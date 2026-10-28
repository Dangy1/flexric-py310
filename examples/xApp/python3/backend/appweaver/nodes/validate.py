"""Validate: tier-1 checks before any control is issued (backend/orchestration/validate.py).

compat + lifecycle, E2 RAN-function conformance against the live E2 node, the lease
pre-check (which applications of the chain another workflow holds right now) and, with
validate_mode="dryrun", a dry run of every control step on the E2 emulator twin. A busy
application is not a rejection: the graph routes it to Recover (wait or re-plan).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from backend.orchestration.validate import validate_chain

from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import busy_entries, event


def build_validate_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    def validate_node(state: AppWeaverState) -> Dict[str, Any]:
        steps = list(state.get("steps") or [])
        own_runs = list((state.get("deployed") or {}).values())
        pending_ids = [s["agent_id"] for s in steps if s["agent_id"] not in (state.get("deployed") or {})]

        def lease_query(agent_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
            wanted = [a for a in agent_ids if a in pending_ids and a in deps.registry]
            raw = deps.lease_query(wanted) if wanted else {}
            return {item["agent_id"]: item for item in busy_entries(raw, own_runs)}

        e2 = deps.e2_functions() if deps.e2_functions is not None else None
        report = validate_chain(
            deps.registry,
            [{"agent_id": s["agent_id"], "action_id": s.get("action_id")} for s in steps],
            mode=cfg.validate_mode,
            lease_query=lease_query,
            e2_functions=e2,
            dryrun_fn=deps.dryrun_fn,
            dryrun_reason=deps.dryrun_reason,
            dryrun_duration_s=cfg.dryrun_duration_s,
        )
        busy = [{"agent_id": agent_id, **info} for agent_id, info in report["lease_precheck"]["busy"].items()]
        out: Dict[str, Any] = {
            "validation_report": report,
            "validation_history": [{"verdict": report["verdict"], "chain": report["chain"], "reasons": report["reject_reasons"], "busy": [b["agent_id"] for b in busy]}],
            "busy_resources": busy,
            "events": [event(deps, state, "validate", report["verdict"], mode=report["mode"], reasons=report["reject_reasons"][:5],
                             busy=[b["agent_id"] for b in busy], e2_ok=report["e2_conformance"]["ok"])],
        }
        if busy and not int(state.get("write_steps_done") or 0):
            out["conflict_detected_before_control"] = True
        if busy:
            out["recover_trigger"] = "precheck_busy"
        if not report["ok"]:
            out.update({"status": "rejected", "failure_reason": "validation_rejected",
                        "blocked_reason": "; ".join(report["reject_reasons"])[:500]})
        return out

    return validate_node
