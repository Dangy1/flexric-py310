from __future__ import annotations

from typing import Any, Dict

from ..tools import PortalToolbox


def build_approve_node(toolbox: PortalToolbox):
    def approve(state: Dict[str, Any]) -> Dict[str, Any]:
        mode = str(state.get("mode", "advisory")).strip().lower() or "advisory"
        selected = list(state.get("selected_actions", []))
        ready = sum(1 for service in state.get("service_health", []) if service.get("ok"))
        total = len(state.get("service_health", []))
        events = list(state.get("events", []))

        approval_required = bool(selected) and mode == "enforced"
        approved: Any = None
        if not selected:
            reason = "No control action is mapped for this workflow."
        elif mode != "enforced":
            reason = "Advisory mode skips RC approval and control execution."
        elif ready == 0 and total > 0:
            approved = False
            reason = "No core platform services are healthy, so RC blocks control execution."
        else:
            approved = True
            reason = "RC guardrail approved the selected action set."

        events.append(
            toolbox.event(
                "approve",
                "approval",
                reason,
                agent_id="rc",
                metadata={
                    "approved": approved,
                    "approval_required": approval_required,
                    "mode": mode,
                    "action_count": len(selected),
                },
            )
        )
        return {
            "active_stage": "approve",
            "approval_required": approval_required,
            "approval_reason": reason,
            "approved": approved,
            "events": events,
            "status": "running",
        }

    return approve
