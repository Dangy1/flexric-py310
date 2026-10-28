"""The AppWeaver StateGraph.

    START
      |
   discover ──► compose ──(plan failed / empty)──────────────────────────► finish ─► END
                  ▲  │
                  │  ▼
                  │ validate ──(rejected: compat / lifecycle / E2 / dry-run)──► finish
                  │  │   │
                  │  │   └─(busy app, recover on, budget left)──► recover
                  │  ▼                                              │  │  │
                  │ deploy ──(refused after shared lease wait,      │  │  └─(wait timed out /
                  │  │        recover on, budget left)──► recover   │  │     budget spent)──► finish
                  │  └──────────────────────────────────────────────┼──┼──► finish
                  │                                                 │  └─(lease free)──► deploy
                  └──────────────────(replan without busy apps)─────┘

`no_repair` (agentcard_no_repair): identical graph without Compose's repair and without the
recover node (busy apps then meet the shared lease wait in deploy, like every baseline).
"""
from __future__ import annotations

from typing import Any, Dict

try:
    from langgraph.graph import END, START, StateGraph
except Exception as exc:  # fail loudly: AppWeaver must run on LangGraph, no silent fallback
    raise ImportError(
        "backend.appweaver requires langgraph (installed in conda env flexric-py310: langgraph 1.1.3); "
        f"import failed: {exc!r}"
    ) from exc

from .nodes import (
    build_compose_node,
    build_deploy_node,
    build_discover_node,
    build_finish_node,
    build_recover_node,
    build_validate_node,
)
from .state import AppWeaverConfig, AppWeaverDeps, AppWeaverState

GRAPH_BACKEND = "langgraph"
NODE_NAMES = ["discover", "compose", "validate", "deploy", "recover", "finish"]


def _route_after_compose(state: AppWeaverState) -> str:
    return "finish" if state.get("status") in {"failed", "unavailable"} else "validate"


def build_graph(deps: AppWeaverDeps, cfg: AppWeaverConfig):
    graph = StateGraph(AppWeaverState)
    graph.add_node("discover", build_discover_node(deps, cfg))
    graph.add_node("compose", build_compose_node(deps, cfg))
    graph.add_node("validate", build_validate_node(deps, cfg))
    graph.add_node("deploy", build_deploy_node(deps, cfg))
    graph.add_node("finish", build_finish_node(deps, cfg))
    if cfg.recover:
        graph.add_node("recover", build_recover_node(deps, cfg))

    def budget_left(state: AppWeaverState) -> bool:
        return cfg.recover and int(state.get("recoveries") or 0) < int(cfg.max_recoveries)

    def route_after_validate(state: AppWeaverState) -> str:
        if state.get("status") == "rejected":
            return "finish"
        if state.get("busy_resources") and budget_left(state):
            return "recover"
        return "deploy"

    def route_after_deploy(state: AppWeaverState) -> str:
        if state.get("deploy_refusal") and budget_left(state):
            return "recover"
        return "finish"

    targets_validate = {"finish": "finish", "deploy": "deploy"}
    targets_deploy = {"finish": "finish"}
    if cfg.recover:
        targets_validate["recover"] = "recover"
        targets_deploy["recover"] = "recover"

    graph.add_edge(START, "discover")
    graph.add_edge("discover", "compose")
    graph.add_conditional_edges("compose", _route_after_compose, {"validate": "validate", "finish": "finish"})
    graph.add_conditional_edges("validate", route_after_validate, targets_validate)
    graph.add_conditional_edges("deploy", route_after_deploy, targets_deploy)
    if cfg.recover:
        graph.add_conditional_edges(
            "recover",
            lambda state: str(state.get("recovery_route") or "finish"),
            {"compose": "compose", "deploy": "deploy", "finish": "finish"},
        )
    graph.add_edge("finish", END)
    return graph.compile()


def run_appweaver(intent_text: str, deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Dict[str, Any]:
    """Run the graph for one intent sentence and return the final state (plain dict)."""
    app = build_graph(deps, cfg)
    initial: AppWeaverState = {
        "intent_text": intent_text,
        "started_at": deps.clock(),
        "events": [],
        "prompts": [],
        "repair_events": [],
        "validation_history": [],
        "tool_calls": [],
        "run_payloads": [],
        "excluded_agents": [],
        "deployed": {},
        "write_steps_done": 0,
        "deploy_cursor": 0,
        "lease_wait_s": 0.0,
        "recoveries": 0,
        "partial_deployment": False,
        "conflict_detected_before_control": False,
        "replanned_around_resource": False,
        "waited_for_lease": False,
    }
    final = app.invoke(initial, config={"recursion_limit": 40})
    result = dict(final)
    result["graph_backend"] = GRAPH_BACKEND
    result["graph_variant"] = cfg.variant
    result["graph_nodes"] = [name for name in NODE_NAMES if cfg.recover or name != "recover"]
    return result
