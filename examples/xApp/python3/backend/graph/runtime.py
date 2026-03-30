from __future__ import annotations

import os
from typing import Any, Dict, List

from .nodes.act import build_act_node
from .nodes.approve import build_approve_node
from .nodes.diagnose import build_diagnose_node
from .nodes.observe import build_observe_node
from .nodes.summarize import build_summarize_node
from .nodes.verify import build_verify_node
from .tools import PortalToolbox
from backend.orchestration.config import WORKFLOW_ACTIONS

try:
    from langgraph.graph import END, START, StateGraph
except Exception:
    END = None
    START = None
    StateGraph = None

try:
    from langsmith import traceable as _langsmith_traceable
except Exception:
    _langsmith_traceable = None


NODE_NAMES = ["observe", "diagnose", "approve", "act", "verify", "summarize"]


def graph_backend_name() -> str:
    return "langgraph" if StateGraph is not None else "linear-fallback"


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_project_name() -> str:
    return os.getenv("LANGSMITH_PROJECT", "").strip() or os.getenv("LANGCHAIN_PROJECT", "").strip() or "flexric-agent-portal"


def langsmith_status() -> Dict[str, Any]:
    installed = _langsmith_traceable is not None
    enabled = installed and (_env_truthy("LANGSMITH_TRACING_V2") or _env_truthy("LANGSMITH_TRACING"))
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "").strip() or os.getenv("LANGCHAIN_ENDPOINT", "").strip() or "https://api.smith.langchain.com"
    api_key_present = bool(os.getenv("LANGSMITH_API_KEY", "").strip() or os.getenv("LANGCHAIN_API_KEY", "").strip())
    project = _langsmith_project_name()
    if not installed:
        detail = "Install langsmith to emit traces from LangGraph workflows."
    elif not enabled:
        detail = "Tracing is available but disabled. Set LANGSMITH_TRACING_V2=true to enable it."
    elif not api_key_present:
        detail = "Tracing is enabled, but no LangSmith API key is configured yet."
    else:
        detail = f"Tracing is enabled for project '{project}'."
    return {
        "installed": installed,
        "enabled": enabled,
        "api_key_present": api_key_present,
        "project": project,
        "endpoint": endpoint,
        "detail": detail,
    }


def graph_runtime_status() -> Dict[str, Any]:
    tracing = langsmith_status()
    return {
        "backend": graph_backend_name(),
        "langgraph_installed": StateGraph is not None,
        "node_names": list(NODE_NAMES),
        "supports_tracing": _langsmith_traceable is not None,
        "tracing": tracing,
    }


def _langsmith_tracing_enabled() -> bool:
    status = langsmith_status()
    return bool(status["installed"] and status["enabled"] and status["api_key_present"])


def _trace_wrapper(name: str, run_type: str, metadata: Dict[str, Any], fn):
    if not _langsmith_tracing_enabled() or _langsmith_traceable is None:
        return fn
    return _langsmith_traceable(
        run_type=run_type,
        name=name,
        metadata=metadata,
        project_name=_langsmith_project_name(),
    )(fn)


def _selected_actions(workflow_id: str) -> List[Dict[str, Any]]:
    return [
        {"agent_id": agent_id, "action_id": action_id}
        for agent_id, action_id in WORKFLOW_ACTIONS.get(workflow_id, {}).items()
    ]


def _merge_state(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(updates)
    return merged


def _stateful_node(node_fn):
    def wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        return _merge_state(state, node_fn(state))

    return wrapped


def _traceable_node(stage_name: str, node_fn):
    wrapped = _stateful_node(node_fn)

    def execute(state: Dict[str, Any]) -> Dict[str, Any]:
        metadata = {
            "stage": stage_name,
            "workflow_id": state.get("workflow_id"),
            "mode": state.get("mode"),
        }
        traced = _trace_wrapper(f"flexric.{stage_name}", "tool", metadata, wrapped)
        return traced(state)

    return execute


def _approval_route(state: Dict[str, Any]) -> str:
    return "act" if state.get("approved") else "summarize"


def _initial_state(
    workflow_id: str,
    workflow_label: str,
    goal: str,
    mode: str,
    agent_sequence: List[str],
) -> Dict[str, Any]:
    return {
        "graph_backend": graph_backend_name(),
        "workflow_id": workflow_id,
        "workflow_label": workflow_label,
        "goal": goal,
        "mode": mode,
        "status": "pending",
        "active_stage": "observe",
        "agent_sequence": list(agent_sequence),
        "selected_actions": _selected_actions(workflow_id),
        "service_health": [],
        "agent_snapshots": {},
        "observations": [],
        "hypotheses": [],
        "recommendations": [],
        "approval_required": bool(WORKFLOW_ACTIONS.get(workflow_id)),
        "approval_reason": "",
        "approved": False,
        "run_results": [],
        "verification_notes": [],
        "events": [],
        "summary": "",
        "errors": [],
    }


def _build_graph(toolbox: PortalToolbox):
    graph = StateGraph(dict)
    graph.add_node("observe", _traceable_node("observe", build_observe_node(toolbox)))
    graph.add_node("diagnose", _traceable_node("diagnose", build_diagnose_node(toolbox)))
    graph.add_node("approve", _traceable_node("approve", build_approve_node(toolbox)))
    graph.add_node("act", _traceable_node("act", build_act_node(toolbox)))
    graph.add_node("verify", _traceable_node("verify", build_verify_node(toolbox)))
    graph.add_node("summarize", _traceable_node("summarize", build_summarize_node(toolbox)))
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "diagnose")
    graph.add_edge("diagnose", "approve")
    graph.add_conditional_edges("approve", _approval_route, {"act": "act", "summarize": "summarize"})
    graph.add_edge("act", "verify")
    graph.add_edge("verify", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()


def _run_linear_fallback(initial: Dict[str, Any], toolbox: PortalToolbox) -> Dict[str, Any]:
    state = dict(initial)
    nodes = [
        build_observe_node(toolbox),
        build_diagnose_node(toolbox),
        build_approve_node(toolbox),
    ]
    for node in nodes:
        state = _merge_state(state, node(state))

    if state.get("approved"):
        state = _merge_state(state, build_act_node(toolbox)(state))
        state = _merge_state(state, build_verify_node(toolbox)(state))

    state = _merge_state(state, build_summarize_node(toolbox)(state))
    return state


def run_graph_workflow(
    workflow_id: str,
    workflow_label: str,
    goal: str,
    mode: str,
    agent_sequence: List[str],
    toolbox: PortalToolbox,
) -> Dict[str, Any]:
    initial = _initial_state(workflow_id, workflow_label, goal, mode, agent_sequence)

    def execute(state: Dict[str, Any]) -> Dict[str, Any]:
        if StateGraph is None:
            return _run_linear_fallback(state, toolbox)
        compiled = _build_graph(toolbox)
        return compiled.invoke(state)

    traced_execute = _trace_wrapper(
        "flexric_graph_workflow",
        "chain",
        {
            "workflow_id": workflow_id,
            "workflow_label": workflow_label,
            "mode": mode,
            "backend": graph_backend_name(),
        },
        execute,
    )
    result = traced_execute(initial)
    result.setdefault("graph_backend", graph_backend_name())
    return result
