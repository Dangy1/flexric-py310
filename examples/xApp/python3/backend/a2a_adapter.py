from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class A2AHandlers:
    list_agents: Callable[[], List[Dict[str, Any]]]
    get_agent_card: Callable[[str], Dict[str, Any]]
    send_message: Callable[[str, str, str, str], Dict[str, Any]]
    run_workflow: Callable[[str, str, str], Dict[str, Any]]
    get_workflow: Callable[[str], Dict[str, Any]]
    get_workflow_events: Callable[[str], List[Dict[str, Any]]]
    cancel_workflow: Callable[[str], Dict[str, Any]]
    queue_status: Callable[[], Dict[str, Any]]
    scheduler_status: Callable[[], Dict[str, Any]]
    run_task: Callable[[str, str, str], Dict[str, Any]]
    test_all: Callable[[bool, bool], Dict[str, Any]]
    backend_name: Callable[[], str]


class A2AAdapter:
    orchestrator_methods = [
        "agents.list",
        "agent.get_card",
        "message.send",
        "workflow.run",
        "workflow.status",
        "workflow.events",
        "workflow.cancel",
        "workflow.queue_status",
        "agent.task.run",
        "portal.test_all",
        "portal.scheduler_status",
        "portal.reset_runtime",
    ]
    agent_methods = ["message.send", "agent.get_card", "agent.task.run"]

    def __init__(self, handlers: A2AHandlers):
        self.handlers = handlers

    def orchestrator_card(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "protocol": "A2A-aligned JSON-RPC",
            "agent": agent,
            "methods": list(self.orchestrator_methods),
            "orchestration": {
                "backend": self.handlers.backend_name(),
                "entrypoint": "workflow.run",
            },
        }

    def agent_card(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "protocol": "A2A-aligned JSON-RPC",
            "agent": agent,
            "methods": list(self.agent_methods),
            "orchestration": {
                "backend": self.handlers.backend_name(),
            },
        }

    def dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        method = payload.get("method")
        params = payload.get("params", {})
        req_id = payload.get("id")

        try:
            if method == "agents.list":
                result = self.handlers.list_agents()
            elif method == "agent.get_card":
                result = self.handlers.get_agent_card(params["agent_id"])
            elif method == "message.send":
                result = self.handlers.send_message(
                    params["source_id"],
                    params["target_id"],
                    params["content"],
                    params.get("kind", "handoff"),
                )
            elif method == "workflow.run":
                result = self.handlers.run_workflow(
                    params["workflow_id"],
                    params.get("goal", "Run a multi-agent FlexRIC workflow"),
                    params.get("mode", "advisory"),
                )
            elif method == "workflow.status":
                result = self.handlers.get_workflow(params["run_id"])
            elif method == "workflow.events":
                result = {
                    "run_id": params["run_id"],
                    "events": self.handlers.get_workflow_events(params["run_id"]),
                }
            elif method == "workflow.cancel":
                result = self.handlers.cancel_workflow(params["run_id"])
            elif method == "workflow.queue_status":
                result = self.handlers.queue_status()
            elif method == "agent.task.run":
                result = self.handlers.run_task(
                    params["agent_id"],
                    params["prompt"],
                    params.get("provider", "auto"),
                )
            elif method == "portal.test_all":
                result = self.handlers.test_all(
                    params.get("include_actions", True),
                    params.get("include_messages", True),
                )
            elif method == "portal.scheduler_status":
                result = self.handlers.scheduler_status()
            elif method == "portal.reset_runtime":
                result = {"status": "unsupported", "detail": "Use the HTTP reset endpoint from the operator UI."}
            else:
                raise KeyError(f"Unknown method: {method}")
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }
