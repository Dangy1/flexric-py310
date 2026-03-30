#!/usr/bin/env python3
"""
mcp_flexric_suites.py (STDIO MCP server)

Unified MCP stdio server for FlexRIC Python suite demos:
- TC suite        (xapp_tc_suite.py)
- Slice suite     (xapp_slice_suite.py)
- KPM/RC suite    (xapp_kpm_rc_suite.py)

Design:
- Run suites as subprocesses (not in-process SWIG calls) to avoid SDK lifecycle conflicts.
- Keep MCP stdout clean (JSON-RPC only). Suite logs go to per-run log files.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp-flexric-suites")

mcp = FastMCP("flexric-suites")

_LOCK = threading.RLock()
_RUN_SEQ = 0


def _now_iso() -> str:
    return datetime.now().isoformat()


def _this_dir() -> Path:
    return Path(__file__).resolve().parent


def _suite_script(suite: str) -> Path:
    mapping = {
        "tc": "xapp_tc_suite.py",
        "slice": "xapp_slice_suite.py",
        "kpm_rc": "xapp_kpm_rc_suite.py",
    }
    return _this_dir() / mapping[suite]


def _log_root() -> Path:
    p = Path(os.getenv("FLEXRIC_MCP_LOG_DIR", "/tmp/flexric_mcp_runs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _python_cmd() -> List[str]:
    # Use current interpreter by default (recommended: launch MCP server from working conda env)
    py = os.getenv("FLEXRIC_MCP_PYTHON", sys.executable)
    return [py, "-u"]


@dataclass
class RunState:
    run_id: str
    suite: str
    profile: str
    cmd: List[str]
    cwd: str
    log_path: str
    started_at: str
    pid: Optional[int] = None
    status: str = "starting"  # starting | running | exited | failed | stopped
    returncode: Optional[int] = None
    ended_at: Optional[str] = None
    error: Optional[str] = None
    proc: Optional[subprocess.Popen] = field(default=None, repr=False)

    def to_public(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite": self.suite,
            "profile": self.profile,
            "pid": self.pid,
            "status": self.status,
            "returncode": self.returncode,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "cwd": self.cwd,
            "log_path": self.log_path,
            "cmd": self.cmd,
            "error": self.error,
        }


_RUNS: Dict[str, RunState] = {}
_ACTIVE_BY_SUITE: Dict[str, str] = {}


def _poll_locked() -> None:
    for run in _RUNS.values():
        if run.proc is None or run.status not in ("starting", "running"):
            continue
        rc = run.proc.poll()
        if rc is None:
            if run.status == "starting":
                run.status = "running"
            continue
        run.returncode = rc
        run.ended_at = _now_iso()
        if run.status == "stopped":
            pass
        elif rc == 0:
            run.status = "exited"
        else:
            run.status = "failed"
        if _ACTIVE_BY_SUITE.get(run.suite) == run.run_id:
            _ACTIVE_BY_SUITE.pop(run.suite, None)


def _tail_file(path: str, lines: int = 50) -> str:
    try:
        with open(path, "r", errors="replace") as f:
            data = f.readlines()
        return "".join(data[-max(1, lines):])
    except FileNotFoundError:
        return ""


def _tail_lines(path: str, lines: int = 50) -> List[str]:
    txt = _tail_file(path, lines=lines)
    return txt.splitlines()


def _new_run_id(suite: str, profile: str) -> str:
    global _RUN_SEQ
    with _LOCK:
        _RUN_SEQ += 1
        return f"{suite}-{profile}-{_RUN_SEQ}"


def _spawn_suite(suite: str, profile: str, extra_args: List[str], stop_existing: bool) -> Dict[str, Any]:
    script = _suite_script(suite)
    if not script.exists():
        return {"status": "error", "error": f"Suite script not found: {script}"}

    with _LOCK:
        _poll_locked()
        active_id = _ACTIVE_BY_SUITE.get(suite)
        if active_id:
            active = _RUNS.get(active_id)
            if active and active.status in ("starting", "running"):
                if not stop_existing:
                    return {
                        "status": "error",
                        "error": f"{suite} suite already running (run_id={active_id})",
                        "active": active.to_public(),
                    }
                _terminate_locked(active, force=False)

        run_id = _new_run_id(suite, profile)
        run_log_dir = _log_root() / suite
        run_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_log_dir / f"{run_id}.log"
        cmd = _python_cmd() + [str(script), "--profile", profile] + extra_args
        state = RunState(
            run_id=run_id,
            suite=suite,
            profile=profile,
            cmd=cmd,
            cwd=str(_this_dir()),
            log_path=str(log_path),
            started_at=_now_iso(),
        )
        _RUNS[run_id] = state

        try:
            logf = open(log_path, "ab", buffering=0)
            proc = subprocess.Popen(
                cmd,
                cwd=str(_this_dir()),
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            state.proc = proc
            state.pid = proc.pid
            state.status = "running"
            _ACTIVE_BY_SUITE[suite] = run_id
            logger.info("Started %s suite profile=%s pid=%s run_id=%s", suite, profile, proc.pid, run_id)
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            state.ended_at = _now_iso()
            return {"status": "error", "error": str(e), "run": state.to_public()}

        return {"status": "success", "run": state.to_public()}


def _terminate_locked(run: RunState, force: bool = False) -> None:
    if run.proc is None or run.status not in ("starting", "running"):
        return
    try:
        if force:
            run.proc.kill()
        else:
            run.proc.terminate()
            try:
                run.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                run.proc.kill()
    except Exception as e:
        run.error = str(e)
    finally:
        rc = run.proc.poll()
        run.returncode = rc
        run.status = "stopped" if (rc is None or rc < 0 or rc == 0) else "failed"
        run.ended_at = _now_iso()
        if _ACTIVE_BY_SUITE.get(run.suite) == run.run_id:
            _ACTIVE_BY_SUITE.pop(run.suite, None)


def _coerce_int(v: Optional[int], name: str) -> List[str]:
    return [] if v is None else [f"--{name}", str(int(v))]


def _coerce_bool(flag: bool, name: str) -> List[str]:
    return [f"--{name}"] if flag else []


def _slice_log_verify(tail: str, profile: str) -> Dict[str, Any]:
    lines = tail.splitlines()
    text = "\n".join(lines)
    lower = text.lower()

    errors = [
        "traceback (most recent call last)",
        "error sending sctp message",
        "sctp_send_failed",
        "no e2 nodes connected",
    ]
    error_hits = [e for e in errors if e in lower]

    setup_ok = "e42 setup-response rx" in lower
    sub_ok = ("slice monitor subscribed" in lower) or ("successfully subscribed" in lower)

    profile_markers = {
        "monitor": ["monitor-only mode", "slice monitor subscribed"],
        "static": ["applied static slice profile"],
        "nvs-rate": ["applied nvs rate slice profile"],
        "nvs-cap": ["applied nvs capacity slice profile"],
        "edf": ["applied edf slice profile"],
        "all": ["running full slice demo sequence", "deleted dl slice id 5"],
    }
    markers = [m.lower() for m in profile_markers.get(profile, [])]
    marker_hits = [m for m in markers if m in lower]

    return {
        "ok": len(error_hits) == 0 and setup_ok and sub_ok and (profile == "monitor" or len(marker_hits) > 0),
        "setup_ok": setup_ok,
        "subscription_ok": sub_ok,
        "profile_marker_hits": marker_hits,
        "error_hits": error_hits,
        "tail_lines": lines[-20:],
    }


def _kpm_log_check(tail: str, min_indications: int = 1) -> Dict[str, Any]:
    lines = tail.splitlines()
    lower = tail.lower()

    errors = [
        "traceback (most recent call last)",
        "no e2 nodes connected",
        "failed to build/subscribe kpm auto-monitor",
        "error sending sctp message",
        "sctp_send_failed",
    ]
    error_hits = [e for e in errors if e in lower]

    subscribed = "kpm subscribed on node[0]" in lower
    indication_lines = [ln for ln in lines if "meas=" in ln]

    return {
        "ok": len(error_hits) == 0 and subscribed and len(indication_lines) >= int(min_indications),
        "subscription_ok": subscribed,
        "indication_count": len(indication_lines),
        "indications": indication_lines[-20:],
        "error_hits": error_hits,
        "tail_lines": lines[-40:],
    }


def _kpm_param_model(
    *,
    profile: str = "kpm",
    period_ms: int = 1000,
    duration_s: int = 30,
    kpm_metrics: str = "rru",
    startup_timeout_s: Optional[int] = None,
    observe_timeout_s: Optional[int] = None,
    tail_lines: Optional[int] = None,
    min_indications: Optional[int] = None,
    stop_after_check: Optional[bool] = None,
) -> Dict[str, Any]:
    shared = {
        "profile": profile,
        "period_ms": int(period_ms),
        "duration_s": int(duration_s),
        "kpm_metrics": str(kpm_metrics),
    }
    mcp_only = {
        "startup_timeout_s": startup_timeout_s,
        "observe_timeout_s": observe_timeout_s,
        "tail_lines": tail_lines,
        "min_indications": min_indications,
        "stop_after_check": stop_after_check,
    }
    mcp_only = {k: v for k, v in mcp_only.items() if v is not None}
    return {
        "shared_with_agent_demo": shared,
        "mcp_only": mcp_only,
        "supported_kpm_metrics": ["rru", "ue", "all"],
    }


def _wait_for_run_state(run_id: str, timeout_s: float) -> Optional[RunState]:
    deadline = time.time() + max(0.1, timeout_s)
    while time.time() < deadline:
        with _LOCK:
            _poll_locked()
            run = _RUNS.get(run_id)
            if run is None:
                return None
            if run.status in ("running", "exited", "failed", "stopped"):
                return run
        time.sleep(0.2)
    with _LOCK:
        _poll_locked()
        return _RUNS.get(run_id)


@mcp.tool()
def list_tools_overview() -> Dict[str, Any]:
    """List available suite profiles and MCP tool usage hints."""
    return {
        "status": "success",
        "suites": {
            "tc": ["segregate", "partition", "shaper", "codel", "ecn", "osi_codel", "all"],
            "slice": ["monitor", "static", "nvs-rate", "nvs-cap", "edf", "all"],
            "kpm_rc": ["kpm", "rc", "both"],
        },
        "notes": [
            "Launch this MCP server from the working conda environment used for xApp scripts.",
            "Suite logs are written to /tmp/flexric_mcp_runs by default.",
            "Only one active run per suite type is allowed (tc/slice/kpm_rc).",
        ],
    }


@mcp.tool()
def tc_start(
    profile: str,
    duration_s: int = 180,
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    protocol: Optional[int] = None,
    pcr_drb_sz: Optional[int] = None,
    codel_interval_ms: Optional[int] = None,
    codel_target_ms: Optional[int] = None,
    shaper_id: Optional[int] = None,
    shaper_window_ms: Optional[int] = None,
    shaper_rate_kbps: Optional[int] = None,
    monitor_rlc: bool = False,
    stop_existing: bool = True,
) -> Dict[str, Any]:
    """Start TC suite profile as a background subprocess and return run metadata."""
    args: List[str] = ["--duration-s", str(int(duration_s))]
    args += _coerce_int(src_port, "src-port")
    args += _coerce_int(dst_port, "dst-port")
    args += _coerce_int(protocol, "protocol")
    args += _coerce_int(pcr_drb_sz, "pcr-drb-sz")
    args += _coerce_int(codel_interval_ms, "codel-interval-ms")
    args += _coerce_int(codel_target_ms, "codel-target-ms")
    args += _coerce_int(shaper_id, "shaper-id")
    args += _coerce_int(shaper_window_ms, "shaper-window-ms")
    args += _coerce_int(shaper_rate_kbps, "shaper-rate-kbps")
    args += _coerce_bool(monitor_rlc, "monitor-rlc")
    return _spawn_suite("tc", profile, args, stop_existing=stop_existing)


@mcp.tool()
def slice_start(
    profile: str = "monitor",
    duration_s: int = 180,
    json_out: str = "rt_slice_stats.json",
    verbose: bool = False,
    assoc_dl_id: Optional[int] = None,
    stop_existing: bool = True,
) -> Dict[str, Any]:
    """Start Slice suite profile and keep logs/JSON output on disk."""
    args: List[str] = ["--duration-s", str(int(duration_s)), "--json-out", str(json_out)]
    args += _coerce_bool(verbose, "verbose")
    args += _coerce_int(assoc_dl_id, "assoc-dl-id")
    return _spawn_suite("slice", profile, args, stop_existing=stop_existing)


@mcp.tool()
def slice_monitor_check(
    duration_s: int = 30,
    verbose: bool = False,
    timeout_s: int = 10,
    tail_lines: int = 120,
    stop_after_check: bool = False,
) -> Dict[str, Any]:
    """
    Start slice suite in monitor mode, wait briefly, and verify setup/subscription via logs.
    Returns structured verification data with run metadata and log evidence.
    """
    started = slice_start(
        profile="monitor",
        duration_s=int(duration_s),
        verbose=bool(verbose),
        stop_existing=True,
    )
    if started.get("status") != "success":
        return started

    run_meta = started["run"]
    run_id = run_meta["run_id"]
    run = _wait_for_run_state(run_id, timeout_s=float(timeout_s))
    if run is None:
        return {"status": "error", "error": f"Run disappeared: {run_id}"}

    tail = _tail_file(run.log_path, lines=int(tail_lines))
    checks = _slice_log_verify(tail, "monitor")

    if stop_after_check and run.status in ("starting", "running"):
        with _LOCK:
            _terminate_locked(run, force=False)

    return {
        "status": "success",
        "run": run.to_public(),
        "checks": checks,
        "verified": checks["ok"],
    }


@mcp.tool()
def slice_apply_profile_and_verify(
    profile: str = "static",
    duration_s: int = 60,
    verbose: bool = True,
    assoc_dl_id: Optional[int] = None,
    startup_timeout_s: int = 15,
    verify_tail_lines: int = 160,
    stop_after_verify: bool = False,
) -> Dict[str, Any]:
    """
    Start a slice profile run and verify success/failure from status + logs.
    Intended as a deterministic MCP-side automation tool for agents.
    """
    if profile not in {"static", "nvs-rate", "nvs-cap", "edf", "all"}:
        return {"status": "error", "error": "profile must be one of: static, nvs-rate, nvs-cap, edf, all"}

    started = slice_start(
        profile=profile,
        duration_s=int(duration_s),
        verbose=bool(verbose),
        assoc_dl_id=assoc_dl_id,
        stop_existing=True,
    )
    if started.get("status") != "success":
        return started

    run_meta = started["run"]
    run_id = run_meta["run_id"]
    run = _wait_for_run_state(run_id, timeout_s=float(startup_timeout_s))
    if run is None:
        return {"status": "error", "error": f"Run disappeared: {run_id}"}

    tail = _tail_file(run.log_path, lines=int(verify_tail_lines))
    checks = _slice_log_verify(tail, profile)

    # If process already failed early, surface that explicitly.
    if run.status in ("failed", "stopped") and not checks["ok"]:
        verified = False
    else:
        verified = checks["ok"]

    if stop_after_verify and run.status in ("starting", "running"):
        with _LOCK:
            _terminate_locked(run, force=False)
        with _LOCK:
            run = _RUNS.get(run_id, run)

    return {
        "status": "success",
        "verified": verified,
        "run": run.to_public(),
        "checks": checks,
        "recommendation": (
            "Proceed to traffic/test steps" if verified else "Inspect log tail and runtime connectivity before retry"
        ),
    }


@mcp.tool()
def kpm_rc_start(
    profile: str = "kpm",
    period_ms: int = 1000,
    duration_s: int = 180,
    kpm_metrics: str = "rru",
    stop_existing: bool = True,
) -> Dict[str, Any]:
    """Start KPM/RC suite profile."""
    args = [
        "--period-ms", str(int(period_ms)),
        "--duration-s", str(int(duration_s)),
        "--kpm-metrics", str(kpm_metrics),
    ]
    res = _spawn_suite("kpm_rc", profile, args, stop_existing=stop_existing)
    if res.get("status") == "success":
        res["params"] = _kpm_param_model(
            profile=profile,
            period_ms=int(period_ms),
            duration_s=int(duration_s),
            kpm_metrics=str(kpm_metrics),
        )
    return res


@mcp.tool()
def kpm_monitor_check(
    period_ms: int = 1000,
    duration_s: int = 30,
    kpm_metrics: str = "rru",
    startup_timeout_s: int = 8,
    observe_timeout_s: int = 12,
    tail_lines: int = 300,
    min_indications: int = 1,
    stop_after_check: bool = False,
) -> Dict[str, Any]:
    """
    Start KPM monitoring (kpm_rc profile='kpm'), wait for subscription + indications,
    and return KPM lines directly in the MCP response for conversational use.
    """
    started = kpm_rc_start(
        profile="kpm",
        period_ms=int(period_ms),
        duration_s=int(duration_s),
        kpm_metrics=str(kpm_metrics),
        stop_existing=True,
    )
    if started.get("status") != "success":
        return started

    run_meta = started["run"]
    run_id = run_meta["run_id"]

    run = _wait_for_run_state(run_id, timeout_s=float(startup_timeout_s))
    if run is None:
        return {"status": "error", "error": f"Run disappeared: {run_id}"}

    deadline = time.time() + max(0.5, float(observe_timeout_s))
    checks = {"ok": False, "subscription_ok": False, "indication_count": 0, "indications": [], "error_hits": [], "tail_lines": []}
    while time.time() < deadline:
        tail = _tail_file(run.log_path, lines=int(tail_lines))
        checks = _kpm_log_check(tail, min_indications=int(min_indications))
        if checks["ok"] or checks["error_hits"]:
            break
        with _LOCK:
            _poll_locked()
            run = _RUNS.get(run_id, run)
            if run and run.status in ("failed", "stopped", "exited"):
                break
        time.sleep(0.5)

    # Final refresh before returning.
    with _LOCK:
        _poll_locked()
        run = _RUNS.get(run_id, run)
    tail = _tail_file(run.log_path, lines=int(tail_lines))
    checks = _kpm_log_check(tail, min_indications=int(min_indications))

    if stop_after_check and run and run.status in ("starting", "running"):
        with _LOCK:
            _terminate_locked(run, force=False)
            run = _RUNS.get(run_id, run)

    return {
        "status": "success",
        "verified": checks["ok"],
        "params": _kpm_param_model(
            profile="kpm",
            period_ms=int(period_ms),
            duration_s=int(duration_s),
            kpm_metrics=str(kpm_metrics),
            startup_timeout_s=int(startup_timeout_s),
            observe_timeout_s=int(observe_timeout_s),
            tail_lines=int(tail_lines),
            min_indications=int(min_indications),
            stop_after_check=bool(stop_after_check),
        ),
        "run": run.to_public() if run else run_meta,
        "checks": checks,
        "recommendation": (
            "KPM monitoring active; indications returned directly"
            if checks["ok"]
            else "If subscription succeeded but no indications arrived, increase observe_timeout_s or check traffic/E2 connectivity"
        ),
    }


@mcp.tool()
def runs_list(active_only: bool = False) -> Dict[str, Any]:
    """List known suite runs with status."""
    with _LOCK:
        _poll_locked()
        items = [r.to_public() for r in _RUNS.values()]
    if active_only:
        items = [r for r in items if r["status"] in ("starting", "running")]
    items.sort(key=lambda x: x["started_at"] or "")
    return {"status": "success", "count": len(items), "runs": items}


@mcp.tool()
def run_status(run_id: Optional[str] = None, suite: Optional[str] = None) -> Dict[str, Any]:
    """Get status for a run_id or current active run for a suite."""
    with _LOCK:
        _poll_locked()
        rid = run_id
        if rid is None and suite is not None:
            rid = _ACTIVE_BY_SUITE.get(suite)
        if rid is None:
            return {"status": "error", "error": "Provide run_id or suite"}
        run = _RUNS.get(rid)
        if run is None:
            return {"status": "error", "error": f"Unknown run_id '{rid}'"}
        return {"status": "success", "run": run.to_public()}


@mcp.tool()
def run_log_tail(run_id: Optional[str] = None, suite: Optional[str] = None, lines: int = 80) -> Dict[str, Any]:
    """Return tail of a run log. Provide run_id or suite (uses active run for suite)."""
    with _LOCK:
        _poll_locked()
        rid = run_id if run_id else (_ACTIVE_BY_SUITE.get(suite) if suite else None)
        if rid is None:
            return {"status": "error", "error": "Provide run_id or suite"}
        run = _RUNS.get(rid)
        if run is None:
            return {"status": "error", "error": f"Unknown run_id '{rid}'"}
        tail = _tail_file(run.log_path, lines=lines)
        return {"status": "success", "run": run.to_public(), "tail": tail}


@mcp.tool()
def run_stop(run_id: Optional[str] = None, suite: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """Stop a running suite process by run_id or active suite name."""
    with _LOCK:
        _poll_locked()
        rid = run_id if run_id else (_ACTIVE_BY_SUITE.get(suite) if suite else None)
        if rid is None:
            return {"status": "error", "error": "Provide run_id or suite"}
        run = _RUNS.get(rid)
        if run is None:
            return {"status": "error", "error": f"Unknown run_id '{rid}'"}
        _terminate_locked(run, force=force)
        return {"status": "success", "run": run.to_public()}


@mcp.tool()
def stop_all(force: bool = False) -> Dict[str, Any]:
    """Stop all active suite subprocesses."""
    stopped: List[Dict[str, Any]] = []
    with _LOCK:
        _poll_locked()
        active_runs = [r for r in _RUNS.values() if r.status in ("starting", "running")]
        for run in active_runs:
            _terminate_locked(run, force=force)
            stopped.append(run.to_public())
    return {"status": "success", "stopped": stopped, "count": len(stopped)}


@mcp.tool()
def health() -> Dict[str, Any]:
    """MCP server health + active suite runs."""
    with _LOCK:
        _poll_locked()
        active = {
            suite: _RUNS[rid].to_public()
            for suite, rid in _ACTIVE_BY_SUITE.items()
            if rid in _RUNS
        }
        python_cmd = _python_cmd()
    return {
        "status": "success",
        "server": "flexric-suites",
        "cwd": str(_this_dir()),
        "python_cmd": python_cmd,
        "log_root": str(_log_root()),
        "active": active,
        "known_runs": len(_RUNS),
    }


@mcp.tool()
def tc_profiles() -> Dict[str, Any]:
    """Return TC profile descriptions."""
    return {
        "status": "success",
        "profiles": {
            "segregate": "Add FIFO queue + generic OSI classifier to queue 1",
            "partition": "BDP/PCR pacing + two FIFO queues + classifier by src-port",
            "shaper": "Three queues + src-port classifiers + shaper on queue",
            "codel": "BDP/PCR pacing + CoDel queue + classifier",
            "ecn": "BDP/PCR pacing + ECN queue + classifier",
            "osi_codel": "BDP/PCR pacing + CoDel + OSI classifier (dst-port/protocol)",
            "all": "Combined demo (BDP/PCR + CoDel + OSI classifier), optionally RLC monitoring",
        },
    }


@mcp.tool()
def slice_profiles() -> Dict[str, Any]:
    """Return Slice profile descriptions."""
    return {
        "status": "success",
        "profiles": {
            "monitor": "Subscribe to SLICE indications only",
            "static": "Apply STATIC slice configuration and monitor",
            "nvs-rate": "Apply NVS RATE slice configuration and monitor",
            "nvs-cap": "Apply NVS CAPACITY slice configuration and monitor",
            "edf": "Apply EDF slice configuration and monitor",
            "all": "Static add -> UE association attempt -> delete slice id 5 -> monitor",
        },
    }


@mcp.tool()
def kpm_rc_profiles() -> Dict[str, Any]:
    """Return KPM/RC profile descriptions."""
    return {
        "status": "success",
        "profiles": {
            "kpm": "KPM auto-monitor (RRU/UE/all output filter)",
            "rc": "RC scaffold (prints RC limitations and node info; no RC auto-sub helper yet)",
            "both": "Run KPM monitor and RC scaffold together",
        },
        "kpm_parameters": {
            "shared_with_agent_demo": {
                "period_ms": {"type": "int", "default": 1000},
                "duration_s": {"type": "int", "default": 30, "notes": "kpm_rc_start default duration_s is 180"},
                "kpm_metrics": {"type": "enum", "values": ["rru", "ue", "all"], "default": "rru"},
            },
            "mcp_kpm_monitor_check_only": {
                "startup_timeout_s": {"type": "int", "default": 8},
                "observe_timeout_s": {"type": "int", "default": 12},
                "tail_lines": {"type": "int", "default": 300},
                "min_indications": {"type": "int", "default": 1},
                "stop_after_check": {"type": "bool", "default": False},
            },
        },
    }


if __name__ == "__main__":
    mcp.run()
