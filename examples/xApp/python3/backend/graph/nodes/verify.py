from __future__ import annotations

from typing import Any, Dict, List

from ..tools import PortalToolbox


def build_verify_node(toolbox: PortalToolbox):
    def verify(state: Dict[str, Any]) -> Dict[str, Any]:
        notes: List[str] = list(state.get("verification_notes", []))
        for result in state.get("run_results", []):
            agent_id = result.get("agent_id", "unknown")
            status = result.get("status", "unknown")
            notes.append(f"{agent_id} launch status: {status}")

        if not notes:
            notes.append("No concrete action was launched; verification remains advisory.")

        events = list(state.get("events", []))
        events.append(
            toolbox.event(
                "verify",
                "verification",
                f"Prepared {len(notes)} verification notes.",
            )
        )
        return {
            "active_stage": "verify",
            "verification_notes": notes,
            "events": events,
            "status": "running",
        }

    return verify
