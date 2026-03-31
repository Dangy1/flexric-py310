from __future__ import annotations

from typing import Any, Dict

from ..tools import PortalToolbox


def build_summarize_node(toolbox: PortalToolbox):
    def summarize(state: Dict[str, Any]) -> Dict[str, Any]:
        recommendations = list(state.get("recommendations", []))
        verification = list(state.get("verification_notes", []))
        approval = state.get("approval_reason", "No approval note.")
        runs = list(state.get("run_results", []))
        errors = list(state.get("errors", []))
        mode = state.get("mode", "advisory")

        summary = (
            f"Mode={mode}. Approval: {approval} "
            f"Recommendations={len(recommendations)}. "
            f"Actions launched={len(runs)}. "
            f"Verification notes={len(verification)}."
        )
        if errors:
            summary += f" Errors={len(errors)}."

        events = list(state.get("events", []))
        events.append(
            toolbox.event(
                "summarize",
                "summary",
                summary,
            )
        )
        status = "warning" if errors else "completed"
        return {
            "active_stage": "summarize",
            "summary": summary,
            "events": events,
            "status": status,
        }

    return summarize
