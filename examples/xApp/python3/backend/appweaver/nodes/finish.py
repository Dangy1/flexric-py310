"""Finish: settle the workflow status from what the earlier nodes recorded."""
from __future__ import annotations

from typing import Any, Callable, Dict

from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event


def build_finish_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    def finish_node(state: AppWeaverState) -> Dict[str, Any]:
        status = state.get("status")
        out: Dict[str, Any] = {}
        if not status:
            refusal = state.get("deploy_refusal")
            failure = state.get("deploy_failure")
            if refusal:
                status = "queued"
                out.update({"failure_reason": "lease_refused", "blocked_reason": str(refusal.get("detail") or "")})
            elif failure:
                status = "completed_with_issues"
                out.update({"failure_reason": "step_failed", "blocked_reason": str(failure.get("detail") or "")})
            else:
                status = "completed"
        out["status"] = status
        out["events"] = [event(deps, state, "finish", status, failure_reason=out.get("failure_reason", state.get("failure_reason", "")),
                               lease_wait_s=round(float(state.get("lease_wait_s") or 0.0), 3))]
        return out

    return finish_node
