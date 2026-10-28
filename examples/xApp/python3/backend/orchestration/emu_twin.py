"""Tier-1 twin: interface-conformance dry-run of a composed step on the FlexRIC E2 emulator.

The twin is a second, independent nearRT-RIC + emu_agent_gnb started by
``scripts/start_twin_emu_stack.sh`` (logs, pids and the generated FlexRIC config
under ``/tmp/flexric_twin_emu``). It listens on 127.0.0.2:36421 (E2) and
127.0.0.2:36422 (E42); the live stack is on 127.0.0.1 and is never touched.

``dryrun_step(agent_id, action_id)`` launches the same suite command as the agent
card's action, pointed at the twin through ``FLEXRIC_XAPP_CONF`` and with a short
duration, and reports whether the step was acknowledged over E2:

* control steps (slice ``apply-static``, tc ``apply-*``, rc ``rc-control``): the
  E2 RIC CONTROL ACKNOWLEDGE reached the xApp (the E2 library's own
  ``[xApp]: CONTROL ACK rx`` line, or ``RC CONTROL-ACK received`` for RC). The
  library's "Successfully received CONTROL-ACK" line is *not* accepted: in the
  Release build it is also printed when the wait times out.
* subscription steps (kpm ``observe-*``, slice ``monitor``, rc ``rc-report``): at
  least one RIC INDICATION was delivered to the xApp.

What this validates: E2 encoding/decoding, that the twin's E2 node advertises the
RAN function the step needs, that the subscription is accepted / the control is
acknowledged, that the xApp runs, and the step's timing. What it does not
validate: any KPI effect. The emulator is stateless (controls are printed and
acknowledged, then discarded) and its KPM/RC indications are random
(test/rnd/fill_rnd_data_*).

The KPM agent's actions read the live shared KPM bus over HTTP (not E2), so on
the twin they are replaced by the E2 KPM subscription the bus collector performs
(``xapp_kpm_rc_suite.py --profile kpm``).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE_DIR = Path(__file__).resolve().parents[2]         # .../examples/xApp/python3


def _xapp_dir() -> Path:
    """Directory holding the built SWIG SDK (_xapp_sdk.so) and the suites: this tree when it is
    the build tree, else FLEXRIC_XAPP_DIR or ~/flexric/build/examples/xApp/python3."""
    if (_HERE_DIR / "_xapp_sdk.so").exists():
        return _HERE_DIR
    env_dir = os.environ.get("FLEXRIC_XAPP_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / "flexric" / "build" / "examples" / "xApp" / "python3"


BASE_DIR = _xapp_dir()
SCRIPTS_DIR = _HERE_DIR / "scripts"
TWIN_DIR = Path(os.environ.get("TWIN_LOG_DIR", "/tmp/flexric_twin_emu"))
TWIN_CONF = TWIN_DIR / "flexric_twin.conf"

E2_PORT = 36421
E42_PORT = 36422

# RAN function id each executable agent needs on the E2 node.
AGENT_RAN_FUNCTION = {"kpm": 2, "rc": 3, "slice": 145, "tc": 146}

# Real E2 acknowledgement lines (see module docstring).
LIB_CONTROL_ACK = "[xApp]: CONTROL ACK rx"
ACK_MARKERS: Dict[Tuple[str, str], List[str]] = {
    ("kpm", "observe-rru"): ["meas=RRU."],
    ("kpm", "observe-ue"): ["meas=DRB.", "meas=RRU."],
    ("slice", "monitor"): ["SLICE ind tstamp="],
    ("slice", "apply-static"): [LIB_CONTROL_ACK],
    ("tc", "apply-codel"): [LIB_CONTROL_ACK],
    ("tc", "apply-all"): [LIB_CONTROL_ACK],
    ("rc", "rc-control"): ["RC CONTROL-ACK received"],
    ("rc", "rc-report"): ["RC indication received"],
}
# Lines that end the dry-run as failed as soon as they appear.
FAIL_MARKERS = ["RC CONTROL-FAILED", "RC REPORT-FAILED", "Traceback (most recent call last)",
                "No E2 nodes connected", "Failed to build/subscribe KPM"]

# Twin replacements for actions whose live command does not use E2 directly.
TWIN_COMMAND_OVERRIDES: Dict[Tuple[str, str], List[str]] = {
    ("kpm", "observe-rru"): ["xapp_kpm_rc_suite.py", "--profile", "kpm", "--kpm-metrics", "rru", "--period-ms", "1000"],
    ("kpm", "observe-ue"): ["xapp_kpm_rc_suite.py", "--profile", "kpm", "--kpm-metrics", "all", "--period-ms", "1000"],
}


# --------------------------------------------------------------------------- twin status

def _pid_alive(name: str) -> bool:
    pid_file = TWIN_DIR / f"{name}.pid"
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def twin_ric_ip() -> str:
    try:
        for line in TWIN_CONF.read_text().splitlines():
            if line.strip().startswith("NEAR_RIC_IP"):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "127.0.0.2"


def _sctp_listening(ip: str, port: int) -> bool:
    try:
        out = subprocess.run(["ss", "-Hln", "--sctp"], capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return False
    return any(f"{ip}:{port}" == fields.split()[3] for fields in out.splitlines() if len(fields.split()) >= 4)


def twin_available() -> bool:
    """True when the twin RIC and emulated E2 node are up and the E2 setup completed."""
    if not TWIN_CONF.is_file() or not _pid_alive("nearRT-RIC") or not _pid_alive("emu_agent_gnb"):
        return False
    ip = twin_ric_ip()
    if ip == "127.0.0.1":  # never treat the live RIC as the twin
        return False
    if not (_sctp_listening(ip, E2_PORT) and _sctp_listening(ip, E42_PORT)):
        return False
    try:
        return "E2 SETUP RESPONSE rx" in (TWIN_DIR / "emu_agent_gnb.log").read_text(errors="replace")
    except OSError:
        return False


def start_twin(restart: bool = False, timeout_s: float = 60.0) -> bool:
    """Start (or restart) the twin with the repo script; returns twin_available()."""
    if restart:
        subprocess.run([str(SCRIPTS_DIR / "stop_twin_emu_stack.sh")], capture_output=True, timeout=timeout_s)
    elif twin_available():
        return True
    subprocess.run([str(SCRIPTS_DIR / "start_twin_emu_stack.sh")], capture_output=True, timeout=timeout_s)
    return twin_available()


def twin_e2_ran_function_defs() -> List[Dict[str, Any]]:
    """RAN functions the twin's E2 node advertised at E2 Setup, as accepted by the twin RIC
    (parsed from its log: "Accepting RAN function ID <id> with def = <name>")."""
    try:
        text = (TWIN_DIR / "nearRT-RIC.log").read_text(errors="replace")
    except OSError:
        return []
    # Keep the last E2 SETUP block (an E2 node may reconnect).
    block = text.rsplit("E2 SETUP-REQUEST rx", 1)[-1] if "E2 SETUP-REQUEST rx" in text else text
    seen: Dict[int, str] = {}
    for match in re.finditer(r"Accepting RAN function ID (\d+) with def = (\S+)", block):
        seen[int(match.group(1))] = match.group(2)
    return [{"id": rf_id, "name": name} for rf_id, name in sorted(seen.items())]


def twin_e2_ran_functions() -> List[int]:
    """RAN function ids advertised by the twin's E2 node."""
    return [item["id"] for item in twin_e2_ran_function_defs()]


# --------------------------------------------------------------------------- dry-run

def _python_bin() -> str:
    env_py = Path.home() / "anaconda3" / "envs" / "flexric-py310" / "bin" / "python"
    return str(env_py) if env_py.exists() else sys.executable


def _card_command(agent_id: str, action_id: str) -> Optional[List[str]]:
    from backend.agents.registry import build_agents  # local import: keeps this module light

    card = build_agents(_python_bin(), BASE_DIR).get(agent_id)
    if card is None:
        return None
    for action in card.actions:
        if action.id == action_id:
            return list(action.command)
    return None


def _with_duration(cmd: List[str], duration_s: float, integer: bool) -> List[str]:
    value = str(max(1, int(round(duration_s)))) if integer else f"{max(0.5, float(duration_s)):g}"
    out = list(cmd)
    if "--duration-s" in out:
        idx = out.index("--duration-s")
        if idx + 1 < len(out):
            out[idx + 1] = value
        else:
            out.append(value)
    else:
        out += ["--duration-s", value]
    return out


def twin_command(agent_id: str, action_id: str, duration_s: float = 4.0) -> Optional[List[str]]:
    """The command dryrun_step runs: the card action's command (or its twin override) with a short duration."""
    override = TWIN_COMMAND_OVERRIDES.get((agent_id, action_id))
    if override is not None:
        cmd = [_python_bin(), "-u", str(BASE_DIR / override[0]), *override[1:]]
    else:
        cmd = _card_command(agent_id, action_id)
        if cmd is None:
            return None
    # Only xapp_rc_ctrl.py accepts fractional durations; the other suites take int.
    integer = not any(part.endswith("xapp_rc_ctrl.py") for part in cmd)
    return _with_duration(cmd, duration_s, integer)


def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
    # `ok` / `verdict` mirror `acked` for callers that look for those keys (validate.py).
    result["ok"] = bool(result["acked"])
    result["verdict"] = "acked" if result["acked"] else "reject"
    return result


def dryrun_step(agent_id: str, action_id: str, duration_s: float = 4.0, timeout_s: Optional[float] = None) -> Dict[str, Any]:
    """Run one composed step against the twin and report whether E2 acknowledged it.

    Returns {acked, ok (= acked), verdict, detail, latency_ms, e2_ran_functions, agent_id, action_id,
    command, tail, exit_code}.
    latency_ms is the time from process launch to the first acknowledgement line (it
    includes Python start-up and the E42 setup with the twin RIC, ~0.5-1 s).
    """
    result: Dict[str, Any] = {
        "agent_id": agent_id,
        "action_id": action_id,
        "acked": False,
        "detail": "",
        "latency_ms": None,
        "e2_ran_functions": [],
        "command": [],
        "tail": [],
    }
    if agent_id.startswith("rapp."):
        result["detail"] = "rApps are not E2 applications; no tier-1 E2 dry-run (A1/O1 path not emulated)."
        return _finish(result)
    markers = ACK_MARKERS.get((agent_id, action_id))
    if markers is None:
        result["detail"] = f"No E2 dry-run defined for {agent_id}/{action_id} (descriptive card or unknown action)."
        return _finish(result)
    if not twin_available():
        result["detail"] = "Twin not available: run scripts/start_twin_emu_stack.sh (or emu_twin.start_twin())."
        return _finish(result)

    ran_functions = twin_e2_ran_functions()
    result["e2_ran_functions"] = ran_functions
    needed = AGENT_RAN_FUNCTION.get(agent_id)
    if needed is not None and needed not in ran_functions:
        result["detail"] = f"reject: twin E2 node does not advertise RAN function {needed} required by {agent_id}"
        return _finish(result)

    cmd = twin_command(agent_id, action_id, duration_s)
    if cmd is None:
        result["detail"] = f"Unknown action {agent_id}/{action_id}"
        return _finish(result)
    if shutil.which("stdbuf"):
        cmd = ["stdbuf", "-oL", "-eL", *cmd]  # line-buffer the E2 library's printf output
    result["command"] = cmd

    env = os.environ.copy()
    env["FLEXRIC_XAPP_CONF"] = str(TWIN_CONF)
    env["PYTHONUNBUFFERED"] = "1"
    lines: List[str] = []
    state: Dict[str, Any] = {"ack_at": None, "ack_line": None, "fail_line": None}
    started = time.time()
    proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, errors="replace", start_new_session=True)

    def _reader() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            if state["ack_at"] is None and any(marker in line for marker in markers):
                state["ack_at"] = time.time()
                state["ack_line"] = line
            if state["fail_line"] is None and any(marker in line for marker in FAIL_MARKERS):
                state["fail_line"] = line

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    budget = timeout_s if timeout_s is not None else float(duration_s) + 25.0
    try:
        proc.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, 2)
            proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(proc.pid, 9)
            except Exception:
                pass
            proc.wait(timeout=5)
        lines.append(f"[emu_twin] killed after {budget:.0f}s")
    reader.join(timeout=5)

    result["tail"] = [line for line in lines if "Opening plugin" not in line and "Loading SM" not in line][-25:]
    if state["ack_at"] is not None:
        result["acked"] = True
        result["latency_ms"] = round((state["ack_at"] - started) * 1000.0, 1)
        result["detail"] = f"acked: {state['ack_line'].strip()}"
    elif state["fail_line"] is not None:
        result["detail"] = f"failed: {state['fail_line'].strip()}"
    else:
        result["detail"] = f"no E2 acknowledgement within {budget:.0f}s (exit code {proc.returncode})"
    result["exit_code"] = proc.returncode
    return _finish(result)


def dryrun_chain(steps: List[Tuple[str, str]], duration_s: float = 4.0) -> List[Dict[str, Any]]:
    """Dry-run each (agent_id, action_id) step in order; one report per step."""
    return [dryrun_step(agent_id, action_id, duration_s) for agent_id, action_id in steps]


if __name__ == "__main__":  # python -m backend.orchestration.emu_twin [agent:action ...]
    import json

    pairs = [tuple(arg.split(":", 1)) for arg in sys.argv[1:]] or [
        ("kpm", "observe-rru"), ("slice", "apply-static"), ("tc", "apply-codel"), ("rc", "rc-control"), ("rc", "rc-report"),
    ]
    print(json.dumps({"twin_available": twin_available(), "twin_e2_ran_functions": twin_e2_ran_function_defs()}, indent=1))
    for agent, action in pairs:
        report = dryrun_step(agent, action)
        print(json.dumps({k: report[k] for k in ("agent_id", "action_id", "acked", "latency_ms", "detail")}))
