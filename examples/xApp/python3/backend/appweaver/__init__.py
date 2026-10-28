"""AppWeaver: Discover -> Compose -> Validate -> Deploy (-> Recover) as a LangGraph StateGraph.

The graph is the evaluated AppWeaver method (`langgraph_agentcard` in the harness) and its
ablation (`agentcard_no_repair`: same graph, Compose repair and the Recover node disabled), plus the
learning variants `appweaver_tpl` (workflow-template cards) and `appweaver_mem` (templates + experience
memory), configured by `AppWeaverConfig(workflow_templates=..., memory_path=...)`.
All side effects (planner LLM, xApp launches, lease queries, waits) are injected through
`AppWeaverDeps`, so the graph runs offline in tests with fakes.
"""
from .state import AppWeaverConfig, AppWeaverDeps, AppWeaverState, InvokeResult
from .graph import GRAPH_BACKEND, NODE_NAMES, build_graph, run_appweaver
from .prompts import compose_prompt, recovery_prompt, serialize_cards
from .learning import ExperienceMemory, default_workflow_cards, retrieve_workflow_cards
from .learning_prompts import compose_prompt_with_context

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
    "ExperienceMemory",
    "default_workflow_cards",
    "retrieve_workflow_cards",
    "compose_prompt_with_context",
]
