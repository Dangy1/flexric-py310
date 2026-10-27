#!/usr/bin/env python3
from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, Query
import uvicorn

load_dotenv()

log = logging.getLogger("flexric-kpm-bus")
logging.basicConfig(level=logging.INFO)

try:
    import redis as redis_lib
except Exception:  # pragma: no cover
    redis_lib = None

THIS_DIR = Path(__file__).resolve().parent
KPM_BUS_HOST = os.getenv("KPM_BUS_HOST", "127.0.0.1").strip()
KPM_BUS_PORT = int(os.getenv("KPM_BUS_PORT", "8091"))
KPM_BUS_REDIS_URL = os.getenv("KPM_BUS_REDIS_URL", "").strip()
KPM_BUS_REDIS_CHANNEL = os.getenv("KPM_BUS_REDIS_CHANNEL", "flexric:kpm:indications").strip() or "flexric:kpm:indications"
KPM_BUS_REDIS_KEY = os.getenv("KPM_BUS_REDIS_KEY", "flexric:kpm:latest").strip() or "flexric:kpm:latest"
KPM_BUS_PERIOD_MS = int(os.getenv("KPM_BUS_PERIOD_MS", os.getenv("FLEXRIC_KPM_PERIOD_MS", "1000")))
KPM_BUS_MAX_RECORDS = int(os.getenv("KPM_BUS_MAX_RECORDS", "500"))
KPM_BUS_AUTO_RESTART = os.getenv("KPM_BUS_AUTO_RESTART", "1").strip().lower() in {"1", "true", "yes", "on"}
KPM_BUS_COLLECTOR_PYTHON = os.getenv("KPM_BUS_COLLECTOR_PYTHON", sys.executable)

_LOCK = threading.RLock()
_RECENT: Deque[Dict[str, Any]] = deque(maxlen=max(50, KPM_BUS_MAX_RECORDS))
_STATE: Dict[str, Any] = {
    "running": False,
    "subscribed": False,
    "collector_pid": None,
    "period_ms": KPM_BUS_PERIOD_MS,
    "last_ts": None,
    "indication_count": 0,
    "error": None,
    "latest_modes": {"rru": [], "ue": [], "all": []},
    "redis_enabled": bool(KPM_BUS_REDIS_URL),
    "redis_connected": False,
    "collector_started_at": None,
    "collector_status": "stopped",
    "collector_cmd": [],
}
_REDIS_CLIENT = None
_COLLECTOR_PROC: subprocess.Popen | None = None
_READER_THREAD: threading.Thread | None = None
_WATCH_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()


def _now() -> str:
    return datetime.now().isoformat()


def _normalize_record(raw: str) -> Dict[str, Any]:
    lowered = raw.lower()
    if "meas=rru.prbtotdl" in lowered or "meas=rru.prbtotul" in lowered:
        mode = "rru"
    elif "meas=drb." in lowered:
        mode = "ue"
    else:
        mode = "all"
    return {"raw": raw, "mode": mode}


def _redis_publish(payload: Dict[str, Any]) -> None:
    global _REDIS_CLIENT
    if not KPM_BUS_REDIS_URL or redis_lib is None:
        with _LOCK:
            _STATE["redis_connected"] = False
        return
    try:
        if _REDIS_CLIENT is None:
            _REDIS_CLIENT = redis_lib.from_url(KPM_BUS_REDIS_URL, decode_responses=True)
        encoded = json.dumps(payload)
        _REDIS_CLIENT.set(KPM_BUS_REDIS_KEY, encoded)
        _REDIS_CLIENT.publish(KPM_BUS_REDIS_CHANNEL, encoded)
        with _LOCK:
            _STATE["redis_connected"] = True
    except Exception as exc:
        with _LOCK:
            _STATE["redis_connected"] = False
            _STATE["error"] = f"Redis publish failed: {exc}"


def _collector_command() -> List[str]:
    return [
        KPM_BUS_COLLECTOR_PYTHON,
        "-u",
        str(THIS_DIR / "xapp_kpm_rc_suite.py"),
        "--profile",
        "kpm",
        "--period-ms",
        str(KPM_BUS_PERIOD_MS),
        "--duration-s",
        "0",
        "--kpm-metrics",
        "all",
    ]


def _append_line(line: str) -> None:
    if not line:
        return
    event_ts = _now()
    normalized = _normalize_record(line)
    with _LOCK:
        seq = _STATE["indication_count"] + 1
        event = {"seq": seq, "ts": event_ts, "mode": normalized["mode"], "raw": normalized["raw"]}
        _RECENT.append(event)
        lowered = line.lower()
        if "kpm subscribed on node" in lowered or "kpm monitor subscribed" in lowered:
            _STATE["subscribed"] = True
            _STATE["last_ts"] = event_ts
        if "meas=" in lowered:
            _STATE["indication_count"] = seq
            _STATE["last_ts"] = event_ts
            _STATE["subscribed"] = True
        if "traceback" in lowered or "attributeerror:" in lowered or "runtimeerror:" in lowered:
            _STATE["error"] = line
        _STATE["latest_modes"] = {
            "rru": [item["raw"] for item in list(_RECENT) if item["mode"] == "rru"][-20:],
            "ue": [item["raw"] for item in list(_RECENT) if item["mode"] == "ue"][-20:],
            "all": [item["raw"] for item in list(_RECENT)][-20:],
        }
        _STATE["error"] = None
    _redis_publish(snapshot_payload())


def _reader_loop(proc: subprocess.Popen) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        if _STOP_EVENT.is_set():
            break
        line = line.rstrip()
        if not line:
            continue
        _append_line(line)
    if proc.stdout is not None:
        proc.stdout.close()


def _start_collector_locked() -> None:
    global _COLLECTOR_PROC, _READER_THREAD
    if _COLLECTOR_PROC is not None and _COLLECTOR_PROC.poll() is None:
        return
    cmd = _collector_command()
    proc = subprocess.Popen(
        cmd,
        cwd=str(THIS_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    _COLLECTOR_PROC = proc
    _STATE.update(
        {
            "running": True,
            "collector_pid": proc.pid,
            "collector_started_at": time.time(),
            "collector_status": "running",
            "collector_cmd": list(cmd),
            "error": None,
        }
    )
    _READER_THREAD = threading.Thread(target=_reader_loop, args=(proc,), daemon=True)
    _READER_THREAD.start()
    log.info("KPM bus collector started pid=%s", proc.pid)


def _stop_collector_locked() -> None:
    global _COLLECTOR_PROC
    proc = _COLLECTOR_PROC
    _COLLECTOR_PROC = None
    if proc is None:
        _STATE["running"] = False
        _STATE["collector_status"] = "stopped"
        _STATE["collector_pid"] = None
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            proc.kill()
        proc.wait(timeout=5)
    _STATE["running"] = False
    _STATE["collector_status"] = f"stopped rc={proc.returncode}"
    _STATE["collector_pid"] = None


def _watch_loop() -> None:
    global _COLLECTOR_PROC
    while not _STOP_EVENT.is_set():
        time.sleep(1)
        with _LOCK:
            proc = _COLLECTOR_PROC
            if proc is None:
                continue
            rc = proc.poll()
            if rc is None:
                continue
            _STATE["running"] = False
            _STATE["collector_status"] = f"exited rc={rc}"
            _STATE["collector_pid"] = None
            _STATE["error"] = f"KPM collector process exited with rc={rc}."
            _COLLECTOR_PROC = None
            should_restart = KPM_BUS_AUTO_RESTART and not _STOP_EVENT.is_set()
        if should_restart:
            time.sleep(1)
            with _LOCK:
                _start_collector_locked()


def recent_records(mode: str = "all", after_seq: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
    mode = (mode or "all").lower()
    with _LOCK:
        records = list(_RECENT)
    out = []
    for event in records:
        if event["seq"] <= after_seq:
            continue
        if mode != "all" and event["mode"] != mode:
            continue
        out.append(event)
    return out[-max(1, min(limit, 200)):]


def snapshot_payload() -> Dict[str, Any]:
    with _LOCK:
        running = bool(_STATE["running"])
        subscribed = bool(_STATE["subscribed"])
        collector_pid = _STATE["collector_pid"]
        collector_status = _STATE["collector_status"]
        collector_started_at = _STATE["collector_started_at"]
        collector_cmd = list(_STATE["collector_cmd"])
        last_ts = _STATE["last_ts"]
        indication_count = int(_STATE["indication_count"])
        error = _STATE["error"]
        latest_modes = dict(_STATE["latest_modes"])
        redis_enabled = bool(_STATE["redis_enabled"])
        redis_connected = bool(_STATE["redis_connected"])
        period_ms = _STATE["period_ms"]
    if running and subscribed:
        ok = True
        status = "ready"
        detail = "Shared KPM bus supervises a single collector subprocess. Agents should read from this bus instead of opening new KPM monitors."
    elif running:
        ok = False
        status = "warning"
        detail = error or "Collector is starting but no KPM indications have been seen yet."
    else:
        ok = False
        status = "warning"
        detail = error or "KPM collector is not running."
    return {
        "ok": ok,
        "status": status,
        "detail": detail,
        "running": running,
        "subscribed": subscribed,
        "collector_pid": collector_pid,
        "collector_status": collector_status,
        "collector_started_at": collector_started_at,
        "collector_cmd": collector_cmd,
        "period_ms": period_ms,
        "last_ts": last_ts,
        "indication_count": indication_count,
        "latest": latest_modes,
        "redis": {
            "enabled": redis_enabled,
            "installed": redis_lib is not None,
            "connected": redis_connected,
            "url": KPM_BUS_REDIS_URL or None,
            "channel": KPM_BUS_REDIS_CHANNEL,
            "key": KPM_BUS_REDIS_KEY,
        },
    }


app = FastAPI(title="FlexRIC KPM Bus", description="Single-owner KPM subscription bus for FlexRIC Python agents")


@app.on_event("startup")
def startup() -> None:
    global _WATCH_THREAD
    with _LOCK:
        _start_collector_locked()
    _WATCH_THREAD = threading.Thread(target=_watch_loop, daemon=True)
    _WATCH_THREAD.start()


@app.on_event("shutdown")
def shutdown() -> None:
    _STOP_EVENT.set()
    with _LOCK:
        _stop_collector_locked()


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return snapshot_payload()


@app.get("/kpm/status")
def kpm_status() -> Dict[str, Any]:
    return snapshot_payload()


@app.get("/kpm/latest")
def kpm_latest(mode: str = Query("all"), after_seq: int = Query(0), limit: int = Query(50)) -> Dict[str, Any]:
    records = recent_records(mode=mode, after_seq=after_seq, limit=limit)
    payload = snapshot_payload()
    payload.update({"mode": mode, "after_seq": after_seq, "records": records, "record_count": len(records)})
    return payload


@app.get("/kpm/recent")
def kpm_recent(mode: str = Query("all"), after_seq: int = Query(0), limit: int = Query(100)) -> Dict[str, Any]:
    return kpm_latest(mode=mode, after_seq=after_seq, limit=limit)


atexit.register(lambda: (_STOP_EVENT.set(), _stop_collector_locked()))


if __name__ == "__main__":
    uvicorn.run(app, host=KPM_BUS_HOST, port=KPM_BUS_PORT, log_level="info")
