from __future__ import annotations

from typing import Any, Dict, List

from ..tools import PortalToolbox


def build_act_node(toolbox: PortalToolbox):
    def act(state: Dict[str, Any]) -> Dict[str, Any]:
        events = list(state.get("events", []))
        selected = list(state.get("selected_actions", []))

        if not state.get("approved"):
            events.append(
                toolbox.event(
                    "act",
                    "skipped",
                    "Skipping control execution because approval was not granted.",
                )
            )
            return {
                "active_stage": "act",
                "run_results": list(state.get("run_results", [])),
                "errors": list(state.get("errors", [])),
                "events": events,
                "status": "completed",
            }

        planned: List[Dict[str, Any]] = []
        for item in selected:
            agent_id = item["agent_id"]
            action_id = item["action_id"]
            label = item.get("label", action_id)
            planned.append({
                "agent_id": agent_id,
                "action_id": action_id,
                "label": label,
                "status": "queued",
                "detail": "Queued for orchestrator-side scheduler admission.",
            })
            events.append(
                toolbox.event(
                    "act",
                    "action-planned",
                    f"Reserved {label} for {agent_id}. Waiting for scheduler admission.",
                    agent_id=agent_id,
                    metadata={"action_id": action_id, "status": "queued"},
                )
            )

        return {
            "active_stage": "act",
            "run_results": planned,
            "events": events,
            "status": "completed",
        }

    return act
