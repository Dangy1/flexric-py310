from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict

GraphMode = Literal["advisory", "enforced"]
GraphStatus = Literal["pending", "running", "completed", "warning", "failed"]


class GraphEvent(TypedDict, total=False):
    timestamp: float
    stage: str
    kind: str
    agent_id: str
    content: str
    metadata: Dict[str, Any]


class FlexRICGraphState(TypedDict, total=False):
    graph_backend: str
    workflow_id: str
    workflow_label: str
    goal: str
    mode: GraphMode
    status: GraphStatus
    active_stage: str
    agent_sequence: List[str]
    selected_actions: List[Dict[str, Any]]
    service_health: List[Dict[str, Any]]
    agent_snapshots: Dict[str, Dict[str, Any]]
    observations: List[str]
    hypotheses: List[str]
    recommendations: List[str]
    approval_required: bool
    approval_reason: str
    approved: bool
    run_results: List[Dict[str, Any]]
    verification_notes: List[str]
    events: List[GraphEvent]
    summary: str
    errors: List[str]
