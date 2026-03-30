from __future__ import annotations

from typing import Any, Dict, List

from ..tools import PortalToolbox


def build_observe_node(toolbox: PortalToolbox):
    def observe(state: Dict[str, Any]) -> Dict[str, Any]:
        services = toolbox.service_health()
        ready = sum(1 for service in services if service.get("ok"))
        agent_sequence = state.get("agent_sequence", [])
        snapshots = {agent_id: toolbox.get_agent(agent_id) for agent_id in agent_sequence}
        observations: List[str] = list(state.get("observations", []))
        observations.append(f"Platform health: {ready}/{len(services)} core services ready.")
        for agent_id in ("kpm", "slice", "tc", "rc"):
            snapshot = snapshots.get(agent_id)
            if snapshot:
                observations.append(f"{snapshot['name']}: {snapshot.get('activity', 'No recent activity')}")

        events = list(state.get("events", []))
        events.append(
            toolbox.event(
                "observe",
                "observation",
                f"Collected service health and {len(snapshots)} agent snapshots.",
            )
        )

        return {
            "active_stage": "observe",
            "service_health": services,
            "agent_snapshots": snapshots,
            "observations": observations,
            "events": events,
            "status": "running",
        }

    return observe
