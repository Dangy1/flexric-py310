from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PortalToolbox:
    get_agent: Callable[[str], Dict[str, Any]]
    list_agents: Callable[[], List[Dict[str, Any]]]
    service_health: Callable[[], List[Dict[str, Any]]]
    record_message: Callable[[str, str, str, str], Dict[str, Any]]
    launch_action: Callable[[str, str], Dict[str, Any]]
    run_task: Optional[Callable[[str, str, str], Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def event(
        self,
        stage: str,
        kind: str,
        content: str,
        *,
        agent_id: str = "orchestrator",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "stage": stage,
            "kind": kind,
            "agent_id": agent_id,
            "content": content,
            "metadata": metadata or {},
        }


def _json_text(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def build_langchain_tools(toolbox: PortalToolbox) -> List[Any]:
    try:
        from langchain_core.tools import StructuredTool
    except Exception:
        return []

    def list_agent_cards() -> str:
        return _json_text({"agents": toolbox.list_agents()})

    def get_service_health() -> str:
        return _json_text({"services": toolbox.service_health()})

    def launch_agent_action(agent_id: str, action_id: str) -> str:
        return _json_text(toolbox.launch_action(agent_id, action_id))

    def send_agent_handoff(source_id: str, target_id: str, content: str, kind: str = "handoff") -> str:
        return _json_text(toolbox.record_message(source_id, target_id, content, kind))

    tools: List[Any] = [
        StructuredTool.from_function(
            func=list_agent_cards,
            name="flexric_list_agent_cards",
            description="List the FlexRIC agent cards known to the current portal runtime.",
        ),
        StructuredTool.from_function(
            func=get_service_health,
            name="flexric_get_service_health",
            description="Fetch the current FlexRIC portal/RPC/MCP health summary.",
        ),
        StructuredTool.from_function(
            func=launch_agent_action,
            name="flexric_launch_agent_action",
            description="Launch a concrete FlexRIC local action for an agent by action id.",
        ),
        StructuredTool.from_function(
            func=send_agent_handoff,
            name="flexric_send_agent_handoff",
            description="Send an in-memory handoff message between FlexRIC agents.",
        ),
    ]

    if toolbox.run_task is not None:
        def reason_with_agent(agent_id: str, prompt: str, provider: str = "auto") -> str:
            return _json_text(toolbox.run_task(agent_id, prompt, provider))

        tools.append(
            StructuredTool.from_function(
                func=reason_with_agent,
                name="flexric_reason_with_agent",
                description="Run a provider-backed reasoning task through a FlexRIC agent workspace.",
            )
        )

    return tools
