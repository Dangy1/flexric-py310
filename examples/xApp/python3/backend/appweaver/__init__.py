"""AppWeaver: Discover -> Compose -> Validate -> Deploy (-> Recover) as a LangGraph StateGraph.

The graph is the evaluated AppWeaver method (`langgraph_agentcard` in the harness) and its
ablation (`agentcard_no_repair`: same graph, Compose repair and the Recover node disabled).
All side effects (planner LLM, xApp launches, lease queries, waits) are injected through
`AppWeaverDeps`, so the graph runs offline in tests with fakes.
"""
from .state import AppWeaverConfig, AppWeaverDeps, AppWeaverState, InvokeResult
from .graph import GRAPH_BACKEND, NODE_NAMES, build_graph, run_appweaver
from .prompts import compose_prompt, recovery_prompt, serialize_cards

__all__ = [
    "AppWeaverConfig",
    "AppWeaverDeps",
    "AppWeaverState",
    "InvokeResult",
    "GRAPH_BACKEND",
    "NODE_NAMES",
    "build_graph",
    "run_appweaver",
    "compose_prompt",
    "recovery_prompt",
    "serialize_cards",
]
