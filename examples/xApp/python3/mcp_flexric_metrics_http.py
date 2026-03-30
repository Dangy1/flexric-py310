#!/usr/bin/env python3
"""
mcp_flexric_metrics_http.py

Goal: initialize FlexRIC first, then expose metrics and health endpoints from a
single main-thread uvicorn server.

Env:
  MCP_HOST=127.0.0.1
  MCP_PORT=8000
  MCP_PATH=/mcp
  FLEXRIC_NODE_INDEX=0
  FLEXRIC_ENABLE=mac,rlc,pdcp,gtp,slice
  FLEXRIC_INTERVAL=10
"""

import os
import time
import logging
import threading
import json
import atexit
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcp-flexric-http")

try:
    import xapp_sdk as ric
except Exception as e:
    raise RuntimeError(
        "Failed to import xapp_sdk. Run from the directory containing "
        "xapp_sdk.py and _xapp_sdk.so (or add it to PYTHONPATH)."
    ) from e

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1").strip()
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
MCP_PATH = os.getenv("MCP_PATH", "/mcp").strip()
SNAPSHOT_PATH = Path(os.getenv("FLEXRIC_MCP_SNAPSHOT", "/tmp/flexric_mcp_snapshot.json"))
SNAPSHOT_INTERVAL_S = float(os.getenv("FLEXRIC_MCP_SNAPSHOT_INTERVAL", "1.0"))
LIVE_COLLECTOR_ENABLED = os.getenv("FLEXRIC_MCP_ENABLE_COLLECTOR", "0").strip().lower() in {"1", "true", "yes", "on"}

NODE_INDEX = int(os.getenv("FLEXRIC_NODE_INDEX", "0"))
ENABLE = {x.strip().lower() for x in os.getenv("FLEXRIC_ENABLE", "mac,rlc,pdcp,gtp,slice").split(",") if x.strip()}
INTERVAL_MS = int(os.getenv("FLEXRIC_INTERVAL", "10"))

_LOCK = threading.Lock()
_RUNNING = False
_NODE = None
_HANDLES: Dict[str, Any] = {}
_COLLECTOR_PROC: subprocess.Popen | None = None

LATEST: Dict[str, Dict[str, Any]] = {
    "mac":   {"status": "init", "ts": None, "error": None, "data": None},
    "rlc":   {"status": "init", "ts": None, "error": None, "data": None},
    "pdcp":  {"status": "init", "ts": None, "error": None, "data": None},
    "gtp":   {"status": "init", "ts": None, "error": None, "data": None},
    "slice": {"status": "init", "ts": None, "error": None, "data": None},
}

MCP_BASE_PATH = MCP_PATH.rstrip("/") or "/mcp"

def to_jsonable(x: Any, depth: int = 2, max_list: int = 50) -> Any:
    if depth <= 0:
        return str(x)
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, (bytes, bytearray)):
        try:
            return x.decode(errors="ignore")
        except Exception:
            return str(x)
    if isinstance(x, dict):
        return {str(k): to_jsonable(v, depth - 1, max_list) for k, v in list(x.items())[:200]}
    if isinstance(x, (list, tuple)):
        return [to_jsonable(i, depth - 1, max_list) for i in list(x)[:max_list]]

    out = {}
    try:
        for a in [a for a in dir(x) if not a.startswith("_")][:200]:
            try:
                v = getattr(x, a)
            except Exception:
                continue
            if callable(v):
                continue
            out[a] = to_jsonable(v, depth - 1, max_list)
    except Exception:
        pass
    return out if out else str(x)

def _interval_enum():
    cand = f"Interval_ms_{INTERVAL_MS}"
    if hasattr(ric, cand):
        return getattr(ric, cand)
    for fallback in ["Interval_ms_10", "Interval_ms_5", "Interval_ms_1", "Interval_ms_100"]:
        if hasattr(ric, fallback):
            return getattr(ric, fallback)
    return None

def _store(sm: str, ind_obj: Any):
    with _LOCK:
        LATEST[sm]["status"] = "ok"
        LATEST[sm]["ts"] = datetime.now().isoformat()
        LATEST[sm]["error"] = None
        # Avoid deep traversal of SWIG-backed indication objects here. The
        # recursive attribute walk is a likely crash path once indications
        # begin arriving, so keep only a shallow, string-safe summary.
        LATEST[sm]["data"] = {
            "summary": to_jsonable(ind_obj, depth=0, max_list=0),
            "python_type": type(ind_obj).__name__,
        }

class _BaseCb:
    SM = "unknown"
    def _ok(self, ind): _store(self.SM, ind)
    def _err(self, e):
        with _LOCK:
            LATEST[self.SM]["status"] = "error"
            LATEST[self.SM]["ts"] = datetime.now().isoformat()
            LATEST[self.SM]["error"] = str(e)

class MACCallback(ric.mac_cb, _BaseCb):
    SM = "mac"
    def __init__(self): ric.mac_cb.__init__(self)
    def handle(self, ind):
        try: self._ok(ind)
        except Exception as e: self._err(e)

class RLCCallback(ric.rlc_cb, _BaseCb):
    SM = "rlc"
    def __init__(self): ric.rlc_cb.__init__(self)
    def handle(self, ind):
        try: self._ok(ind)
        except Exception as e: self._err(e)

class PDCPCallback(ric.pdcp_cb, _BaseCb):
    SM = "pdcp"
    def __init__(self): ric.pdcp_cb.__init__(self)
    def handle(self, ind):
        try: self._ok(ind)
        except Exception as e: self._err(e)

class GTPCallback(ric.gtp_cb, _BaseCb):
    SM = "gtp"
    def __init__(self): ric.gtp_cb.__init__(self)
    def handle(self, ind):
        try: self._ok(ind)
        except Exception as e: self._err(e)

class SLICECallback(ric.slice_cb, _BaseCb):
    SM = "slice"
    def __init__(self): ric.slice_cb.__init__(self)
    def handle(self, ind):
        try: self._ok(ind)
        except Exception as e: self._err(e)

def _ensure_started():
    global _RUNNING, _NODE
    with _LOCK:
        if _RUNNING:
            return

    log.info("FlexRIC init() ...")
    ric.init()

    conn = ric.conn_e2_nodes()
    if not conn or len(conn) == 0:
        raise RuntimeError("No E2 nodes connected (conn_e2_nodes() returned empty).")

    idx = NODE_INDEX if NODE_INDEX < len(conn) else 0
    _NODE = conn[idx].id

    interval = _interval_enum()
    if interval is None:
        raise RuntimeError("Could not find any Interval_ms_* enum in xapp_sdk.")

    log.info("Using node_index=%d interval=%s enable=%s", idx, str(interval), sorted(ENABLE))

    if "mac" in ENABLE:
        _HANDLES["mac"] = ric.report_mac_sm(_NODE, interval, MACCallback())
    if "rlc" in ENABLE:
        _HANDLES["rlc"] = ric.report_rlc_sm(_NODE, interval, RLCCallback())
    if "pdcp" in ENABLE:
        _HANDLES["pdcp"] = ric.report_pdcp_sm(_NODE, interval, PDCPCallback())
    if "gtp" in ENABLE:
        _HANDLES["gtp"] = ric.report_gtp_sm(_NODE, interval, GTPCallback())
    if "slice" in ENABLE:
        _HANDLES["slice"] = ric.report_slice_sm(_NODE, interval, SLICECallback())

    with _LOCK:
        _RUNNING = True

def _get_latest(sm: str) -> Dict[str, Any]:
    with _LOCK:
        snap = dict(LATEST.get(sm, {}))
        running = _RUNNING
    return {"status": snap.get("status"), "ts": snap.get("ts"), "running": running,
            "error": snap.get("error"), "data": snap.get("data")}

def health() -> Dict[str, Any]:
    with _LOCK:
        return {
            "status": "success",
            "running": _RUNNING,
            "enabled": sorted(ENABLE),
            "subscribed": sorted(_HANDLES.keys()),
            "latest": {k: {"status": v["status"], "ts": v["ts"], "error": v["error"]} for k, v in LATEST.items()},
        }

def get_mac_metrics() -> Dict[str, Any]:   return _get_latest("mac")
def get_rlc_metrics() -> Dict[str, Any]:   return _get_latest("rlc")
def get_pdcp_metrics() -> Dict[str, Any]:  return _get_latest("pdcp")
def get_gtp_metrics() -> Dict[str, Any]:   return _get_latest("gtp")
def get_slice_metrics() -> Dict[str, Any]: return _get_latest("slice")


def _snapshot_payload() -> Dict[str, Any]:
    with _LOCK:
        latest = {
            k: {
                "status": v["status"],
                "ts": v["ts"],
                "error": v["error"],
                "data": v["data"],
            }
            for k, v in LATEST.items()
        }
        return {
            "status": "success",
            "running": _RUNNING,
            "enabled": sorted(ENABLE),
            "subscribed": sorted(_HANDLES.keys()),
            "latest": latest,
            "written_at": datetime.now().isoformat(),
        }


def _write_snapshot() -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = _snapshot_payload()
    tmp_path = SNAPSHOT_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload), encoding="utf-8")
    tmp_path.replace(SNAPSHOT_PATH)


def _read_snapshot() -> Dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        if not LIVE_COLLECTOR_ENABLED:
            return {
                "status": "ok",
                "running": False,
                "enabled": sorted(ENABLE),
                "subscribed": [],
                "latest": {},
                "detail": "Live FlexRIC collector is disabled by default for stability. Set FLEXRIC_MCP_ENABLE_COLLECTOR=1 to opt in.",
            }
        return {
            "status": "warning",
            "running": False,
            "enabled": sorted(ENABLE),
            "subscribed": [],
            "latest": {},
            "detail": f"Snapshot not available yet at {SNAPSHOT_PATH}",
        }
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "running": False,
            "enabled": sorted(ENABLE),
            "subscribed": [],
            "latest": {},
            "detail": f"Failed to read snapshot: {exc}",
        }


def _collector_alive() -> bool:
    return _COLLECTOR_PROC is not None and _COLLECTOR_PROC.poll() is None


def _cleanup_collector() -> None:
    global _COLLECTOR_PROC
    if _COLLECTOR_PROC is None:
        return
    if _COLLECTOR_PROC.poll() is None:
        try:
            _COLLECTOR_PROC.terminate()
            _COLLECTOR_PROC.wait(timeout=5)
        except Exception:
            try:
                _COLLECTOR_PROC.kill()
            except Exception:
                pass
    _COLLECTOR_PROC = None


def _start_collector() -> None:
    global _COLLECTOR_PROC
    if not LIVE_COLLECTOR_ENABLED:
        return
    if _collector_alive():
        return

    env = os.environ.copy()
    env["FLEXRIC_MCP_SNAPSHOT"] = str(SNAPSHOT_PATH)
    _COLLECTOR_PROC = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--collector"],
        env=env,
    )
    atexit.register(_cleanup_collector)


def _run_collector() -> None:
    _ensure_started()
    log.info("FlexRIC subscriptions started. Collector loop running.")
    while True:
        _write_snapshot()
        time.sleep(SNAPSHOT_INTERVAL_S)

def _http_payload(path: str) -> tuple[int, Dict[str, Any]]:
    if path == "/healthz":
        snapshot = _read_snapshot()
        snapshot["collector_running"] = _collector_alive()
        if not LIVE_COLLECTOR_ENABLED:
            snapshot["status"] = "ok"
        else:
            snapshot["status"] = "ok" if snapshot.get("running") and snapshot["collector_running"] else "warning"
        return 200, snapshot
    if path == MCP_BASE_PATH:
        return 200, {
            "status": "success",
            "service": "flexric-metrics-http",
            "note": "Lightweight HTTP bridge for FlexRIC metrics.",
            "paths": {
                "health": f"{MCP_BASE_PATH}/health",
                "mac": f"{MCP_BASE_PATH}/mac",
                "rlc": f"{MCP_BASE_PATH}/rlc",
                "pdcp": f"{MCP_BASE_PATH}/pdcp",
                "gtp": f"{MCP_BASE_PATH}/gtp",
                "slice": f"{MCP_BASE_PATH}/slice",
            },
        }
    if path == f"{MCP_BASE_PATH}/health":
        snapshot = _read_snapshot()
        snapshot["collector_running"] = _collector_alive()
        if not LIVE_COLLECTOR_ENABLED:
            snapshot["status"] = "ok"
        return 200, snapshot
    if path == f"{MCP_BASE_PATH}/mac":
        return 200, _read_snapshot().get("latest", {}).get("mac", {})
    if path == f"{MCP_BASE_PATH}/rlc":
        return 200, _read_snapshot().get("latest", {}).get("rlc", {})
    if path == f"{MCP_BASE_PATH}/pdcp":
        return 200, _read_snapshot().get("latest", {}).get("pdcp", {})
    if path == f"{MCP_BASE_PATH}/gtp":
        return 200, _read_snapshot().get("latest", {}).get("gtp", {})
    if path == f"{MCP_BASE_PATH}/slice":
        return 200, _read_snapshot().get("latest", {}).get("slice", {})
    return 404, {"status": "error", "detail": f"Unknown path: {path}"}


def _run_http():
    log.info("Starting MCP HTTP server at http://%s:%d%s", MCP_HOST, MCP_PORT, MCP_PATH)

    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            status_code, payload = _http_payload(self.path)
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args):
            log.info("HTTP %s - %s", self.address_string(), fmt % args)

    server = ThreadingHTTPServer((MCP_HOST, MCP_PORT), MetricsHandler)
    server.serve_forever()

if __name__ == "__main__":
    if "--collector" in sys.argv:
        _run_collector()
    else:
        signal.signal(signal.SIGTERM, lambda *_: (_cleanup_collector(), sys.exit(0)))
        signal.signal(signal.SIGINT, lambda *_: (_cleanup_collector(), sys.exit(0)))
        _start_collector()
        if LIVE_COLLECTOR_ENABLED:
            log.info("Collector subprocess started. Launching HTTP server.")
        else:
            log.info("Launching HTTP server with live collector disabled. Set FLEXRIC_MCP_ENABLE_COLLECTOR=1 to opt in.")
        _run_http()
