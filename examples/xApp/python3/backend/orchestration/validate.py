"""Validate step of AppWeaver: checks a composed chain before any control is issued.

Tier 1 (``mode="checks"``, every intent):
  * compat       -- ``compat.check_chain`` (dependency / interface / control scope /
                    timescale) plus the lifecycle check (deprecated cards are rejected);
  * e2           -- E2 RAN-function conformance: every near-RT step's service model and
                    E2SM interfaces must be advertised by the live E2 node. The advertised
                    functions are read (read-only) from the near-RT RIC log, i.e. the
                    "Accepting RAN function ID <n> with def = <name>" lines of the last
                    E2 SETUP; no extra xApp is connected to the RIC;
  * lease        -- lease pre-check: which applications of the chain are busy right now
                    (another workflow holds them). Busy is not a rejection: the graph routes
                    it to Recover (wait or re-plan), never to a pre-emption.
Tier 1b (``mode="dryrun"``): each control (write-scope) step is additionally launched
  for a short window on the E2 emulator twin via
  ``backend.orchestration.emu_twin.dryrun_step(agent_id, action_id, duration_s)``; a
  failed dry run rejects the chain. If that module is not importable the mode degrades
  to ``checks`` and the reason is recorded.

Nothing here touches the live RAN or the scheduler state.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from backend.common.models import AgentCard
from backend.orchestration.compat import check_chain, lifecycle_findings

DEFAULT_RIC_LOG = "/tmp/flexric_portal_stack/nearRT-RIC.log"
_ACCEPT_RE = re.compile(r"Accepting RAN function ID (\d+) with def = (\S+)")
_SETUP_MARK = "E2 SETUP-REQUEST rx"

LeaseQuery = Callable[[List[str]], Dict[str, Optional[Dict[str, Any]]]]
DryrunFn = Callable[[str, str, int], Any]


def ric_log_path() -> Path:
    return Path(os.getenv("FLEXRIC_RIC_LOG", DEFAULT_RIC_LOG))


def live_e2_ran_functions(log_path: Optional[Path] = None, max_bytes: int = 4_000_000) -> Dict[str, Any]:
    """RAN functions the live E2 node advertised in its last E2 SETUP (from the RIC log)."""
    path = Path(log_path) if log_path else ric_log_path()
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
            text = handle.read().decode("utf-8", errors="replace")
    except OSError as exc:
        return {"available": False, "source": str(path), "detail": f"RIC log unreadable: {exc}", "ran_functions": {}}
    lines = text.splitlines()
    last_setup = max((i for i, line in enumerate(lines) if _SETUP_MARK in line), default=-1)
    window = lines[last_setup + 1:] if last_setup >= 0 else lines
    functions: Dict[str, str] = {}
    for line in window:
        match = _ACCEPT_RE.search(line)
        if match:
            functions[match.group(1)] = match.group(2)
    if not functions and last_setup >= 0:
        for line in lines:
            match = _ACCEPT_RE.search(line)
            if match:
                functions[match.group(1)] = match.group(2)
    return {
        "available": bool(functions),
        "source": str(path),
        "detail": "" if functions else "No 'Accepting RAN function' lines found.",
        "ran_functions": functions,
        "read_at": time.time(),
    }


def _ran_function_name(token: str) -> str:
    key = token.upper().replace("E2SM-", "").strip()
    return f"ORAN-E2SM-{key}" if key in {"KPM", "RC", "CCC", "NI"} else f"{key}_STATS"


def required_ran_functions(card: AgentCard) -> List[str]:
    """E2 RAN-function definitions a near-RT xApp card needs on the E2 node."""
    if getattr(card, "app_type", "xapp") != "xapp" or getattr(card, "ric", "near-rt") != "near-rt":
        return []
    tokens = []
    if card.service_model and card.service_model.upper() not in {"", "NON-RT", "LLM", "ORCHESTRATOR"}:
        tokens.append(card.service_model)
    tokens += [iface.split(" ")[0] for iface in card.interfaces if iface.upper().startswith("E2SM-")]
    seen: List[str] = []
    for token in tokens:
        name = _ran_function_name(token)
        if name not in seen:
            seen.append(name)
    return seen


def e2_conformance(registry: Dict[str, AgentCard], chain: Iterable[str], e2: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    defs = list((e2 or {}).get("ran_functions", {}).values())
    available = bool((e2 or {}).get("available"))
    steps = []
    for agent_id in chain:
        card = registry.get(agent_id)
        if card is None:
            steps.append({"agent_id": agent_id, "required": [], "missing": [], "ok": None, "detail": "unknown agent"})
            continue
        required = required_ran_functions(card)
        if not required:
            steps.append({"agent_id": agent_id, "required": [], "missing": [], "ok": True, "detail": "not an E2 application"})
            continue
        if not available:
            steps.append({"agent_id": agent_id, "required": required, "missing": [], "ok": None, "detail": "E2 node functions unknown"})
            continue
        missing = [name for name in required if not any(d.upper().startswith(name.upper()) for d in defs)]
        steps.append({"agent_id": agent_id, "required": required, "missing": missing, "ok": not missing, "detail": ""})
    return {
        "source": (e2 or {}).get("source"),
        "available": available,
        "advertised": (e2 or {}).get("ran_functions", {}),
        "steps": steps,
        "ok": all(step["ok"] is not False for step in steps),
    }


def writes(card: Optional[AgentCard], action_id: Optional[str] = None) -> bool:
    """Does this step issue control? Per-action scopes (AgentAction.control_scopes) win over the card's."""
    if card is None:
        return False
    action = next((a for a in card.actions if a.id == action_id), None) if action_id else None
    scopes = list(getattr(action, "control_scopes", None) or []) or list(card.control_scopes)
    return any(scope.mode == "write" for scope in scopes)


def resolve_dryrun() -> Tuple[Optional[DryrunFn], str]:
    """Lazily import the emulator-twin dry run (written separately); never raises."""
    try:
        from backend.orchestration import emu_twin  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on the other workstream
        return None, f"backend.orchestration.emu_twin not importable: {exc!r}"
    fn = getattr(emu_twin, "dryrun_step", None)
    if not callable(fn):
        return None, "backend.orchestration.emu_twin has no callable dryrun_step"
    return fn, ""


def _dryrun_ok(result: Any) -> Tuple[bool, Any]:
    if isinstance(result, bool):
        return result, result
    if isinstance(result, dict):
        if "ok" in result:
            return bool(result.get("ok")), result
        verdict = str(result.get("verdict") or result.get("status") or "").lower()
        return verdict in {"pass", "passed", "ok", "accept", "accepted", "acked", "success"}, result
    return False, repr(result)  # unrecognised result: not an acknowledgement


def validate_chain(
    registry: Dict[str, AgentCard],
    steps: List[Dict[str, str]],
    *,
    mode: str = "checks",
    lease_query: Optional[LeaseQuery] = None,
    e2_functions: Optional[Dict[str, Any]] = None,
    dryrun_fn: Optional[DryrunFn] = None,
    dryrun_reason: str = "",
    dryrun_duration_s: int = 5,
) -> Dict[str, Any]:
    """Return a ValidationReport (plain dict) for an ordered list of {agent_id, action_id}."""
    started = time.perf_counter()
    chain = [str(step.get("agent_id") or "").lower() for step in steps]
    compat = check_chain(registry, chain)
    lifecycle = [f.to_dict() for f in lifecycle_findings(registry, chain)]
    e2 = e2_conformance(registry, chain, e2_functions)

    busy: Dict[str, Dict[str, Any]] = {}
    if lease_query is not None and chain:
        step_action = {str(step.get("agent_id") or "").lower(): (str(step.get("action_id") or "") or None) for step in steps}
        for agent_id, info in (lease_query(list(dict.fromkeys(chain))) or {}).items():
            if info:
                # The portal lease is per agent (any active run blocks it); `writes` says whether
                # *our* step on it would be a control (per-action scope, e.g. slice monitor = read).
                busy[agent_id] = dict(info, writes=writes(registry.get(agent_id), step_action.get(agent_id)))

    requested_mode = mode
    effective_mode = mode
    degraded_reason = ""
    dryrun_steps: Optional[List[Dict[str, Any]]] = None
    if mode == "dryrun":
        if dryrun_fn is None:
            effective_mode = "checks"
            degraded_reason = dryrun_reason or "dry-run function unavailable"
        else:
            dryrun_steps = []
            for step in steps:
                agent_id = str(step.get("agent_id") or "").lower()
                if not writes(registry.get(agent_id), str(step.get("action_id") or "") or None):
                    continue
                t0 = time.perf_counter()
                try:
                    duration = max(5, int(dryrun_duration_s)) if agent_id == "kpm" else int(dryrun_duration_s)
                    ok, raw = _dryrun_ok(dryrun_fn(agent_id, str(step.get("action_id") or ""), duration))
                    error = ""
                except Exception as exc:  # the twin failing is a rejection, not a crash
                    ok, raw, error = False, None, repr(exc)
                dryrun_steps.append({
                    "agent_id": agent_id,
                    "action_id": step.get("action_id"),
                    "ok": ok,
                    "result": raw,
                    "error": error,
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                })

    reasons: List[str] = []
    if not chain:
        reasons.append("empty chain")
    if not compat.ok:
        reasons += [f"compat:{f.check}:{f.agent_id}:{f.detail}" for f in compat.findings if f.severity == "error"]
    reasons += [f"lifecycle:{f['agent_id']}:{f['detail']}" for f in lifecycle]
    reasons += [f"e2:{s['agent_id']}: missing {s['missing']}" for s in e2["steps"] if s["ok"] is False]
    reasons += [f"dryrun:{s['agent_id']}/{s['action_id']} failed" for s in (dryrun_steps or []) if not s["ok"]]
    ok = not reasons
    return {
        "requested_mode": requested_mode,
        "mode": effective_mode,
        "degraded_reason": degraded_reason,
        "chain": chain,
        "compat": compat.to_dict(),
        "lifecycle": lifecycle,
        "e2_conformance": e2,
        "lease_precheck": {"checked": list(dict.fromkeys(chain)), "busy": busy},
        "dryrun": dryrun_steps,
        "ok": ok,
        "busy": bool(busy),
        "verdict": "reject" if not ok else ("busy" if busy else "deployable"),
        "reject_reasons": reasons,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }
