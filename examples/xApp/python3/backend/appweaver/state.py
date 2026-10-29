from __future__ import annotations

import operator
import time
from dataclasses import dataclass
from typing import Annotated, Any, Callable, Dict, List, Optional, Tuple, TypedDict

from backend.common.models import AgentCard

from .learning import MEMORY_K, MEMORY_MIN_SCORE, TEMPLATE_K


class InvokeResult(TypedDict, total=False):
    """What the injected `invoke` returns for one step (the harness applies the shared lease wait)."""
    tool_calls: List[Dict[str, Any]]      # refused attempt (if any) + final attempt, in order
    run_payloads: List[Dict[str, Any]]
    error: Optional[str]
    lease_wait_s: float                   # time spent waiting for a busy agent before the retry
    refused: bool                         # final attempt still refused by a lease (agent busy)


@dataclass
class AppWeaverConfig:
    variant: str = "appweaver"            # appweaver | no_repair | appweaver_tpl | appweaver_mem | appweaver_guided | appweaver_v2
    repair: bool = True                   # Compose: repair-by-insertion with fixpoint re-check
    recover: bool = True                  # Recover node: wait or re-plan around busy apps
    validate_mode: str = "checks"         # checks | dryrun
    lease_wait_s: float = 45.0            # same budget as every other method
    max_recoveries: int = 1
    dryrun_duration_s: int = 5
    # Learning variants (workstream F); defaults = AppWeaver.
    workflow_templates: bool = False      # Discover retrieves operator workflow-template cards for Compose
    template_k: int = TEMPLATE_K
    memory_path: Optional[str] = None     # experience memory (JSONL) retrieved by Discover for Compose
    memory_k: int = MEMORY_K
    memory_min_score: float = MEMORY_MIN_SCORE
    guidance: bool = False                # Compose prompt adds the planning guidance (learning_prompts.GUIDANCE_SECTION)
    feedback: bool = False                # one bounded re-plan when the repaired chain still has compat findings


@dataclass
class AppWeaverDeps:
    registry: Dict[str, AgentCard]
    # (intent_text, exclude_ids) -> (cards in prompt order, retrieval report)
    discover: Callable[[str, List[str]], Tuple[List[AgentCard], Dict[str, Any]]]
    # prompt -> portal task dict {status, response, error, provider_id, prompt, ...}
    planner: Callable[[str], Dict[str, Any]]
    # (agent_id, action_id) -> InvokeResult
    invoke: Callable[[str, str], InvokeResult]
    # agent_ids -> {agent_id: busy-info dict or None}; busy-info has run_id, action_id, resource
    lease_query: Callable[[List[str]], Dict[str, Optional[Dict[str, Any]]]]
    # (agent_ids, budget_s) -> {"free": bool, "waited_s": float}
    wait_until_free: Callable[[List[str], float], Dict[str, Any]]
    # (agent_id, intent_text) -> default action id for that agent (or None)
    resolve_action: Callable[[str, str], Optional[str]]
    # planner error text -> provider unreachable?
    is_unavailable: Callable[[str], bool] = lambda text: False
    # () -> live E2 RAN functions report (validate.live_e2_ran_functions)
    e2_functions: Optional[Callable[[], Dict[str, Any]]] = None
    dryrun_fn: Optional[Callable[[str, str, int], Any]] = None
    dryrun_reason: str = ""
    clock: Callable[[], float] = time.perf_counter
    # Learning variants: intent_text -> (workflow cards, report) / (memory entries, report).
    # None -> built from backend.orchestration.config / cfg.memory_path (backend.appweaver.learning).
    retrieve_templates: Optional[Callable[[str], Tuple[List[Dict[str, Any]], Dict[str, Any]]]] = None
    recall_memory: Optional[Callable[[str], Tuple[List[Dict[str, Any]], Dict[str, Any]]]] = None


class AppWeaverState(TypedDict, total=False):
    intent_text: str
    started_at: float
    events: Annotated[List[Dict[str, Any]], operator.add]
    # Discover
    retrieval: Dict[str, Any]
    card_ids: List[str]
    excluded_agents: List[str]
    workflow_cards: List[Dict[str, Any]]
    template_retrieval: Dict[str, Any]
    memory_entries: List[Dict[str, Any]]
    memory_retrieval: Dict[str, Any]
    # Compose
    prompts: Annotated[List[Dict[str, Any]], operator.add]
    planner_task: Dict[str, Any]
    planner_plan: Dict[str, Any]
    feedback_planner_task: Dict[str, Any]   # the feedback re-plan call (appweaver_guided / appweaver_v2)
    feedback: Dict[str, Any]                # {findings, first_chain, revised_chain, adopted}
    planner_unavailable: bool
    raw_chain: List[str]
    generated_workflow: List[str]
    steps: List[Dict[str, Any]]
    compat_report: Dict[str, Any]
    repair_events: Annotated[List[Dict[str, Any]], operator.add]
    pending_plan: Optional[Dict[str, Any]]
    # Validate
    validation_report: Dict[str, Any]
    validation_history: Annotated[List[Dict[str, Any]], operator.add]
    busy_resources: List[Dict[str, Any]]
    conflict_detected_before_control: bool
    # Deploy
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
    run_payloads: Annotated[List[Dict[str, Any]], operator.add]
    deployed: Dict[str, str]              # agent_id -> run_id launched by this workflow
    write_steps_done: int
    deploy_cursor: int
    deploy_refusal: Optional[Dict[str, Any]]
    deploy_failure: Optional[Dict[str, Any]]
    partial_deployment: bool
    lease_wait_s: float
    # Recover
    recover_trigger: str                  # precheck_busy | deploy_refused
    recoveries: int
    recovery: Dict[str, Any]
    recovery_route: str                   # deploy | compose | finish
    replanned_around_resource: bool
    waited_for_lease: bool
    # Finish
    status: str
    failure_reason: str
    blocked_reason: str
