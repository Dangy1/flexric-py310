from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ControlScope:
    """What an application may write, and at which granularity."""
    target: str          # cell | ue | slice | node | transport
    mode: str = "read"   # read | write
    resource: str = ""   # lease class, e.g. slice_control, tc_control, rc_control, cell_power


@dataclass
class AgentAction:
    id: str
    label: str
    description: str
    kind: str
    command: List[str] = field(default_factory=list)
    # Per-action scope (optional). Empty = the action may use every scope of its card.
    # Lets a card with a write scope declare a read-only action (e.g. slice `monitor`).
    control_scopes: List[ControlScope] = field(default_factory=list)


@dataclass
class AgentCard:
    id: str
    name: str
    role: str
    service_model: str
    description: str
    page_path: str
    a2a_card_path: str
    status: str
    activity: str
    skills: List[str]
    measurements: List[str]
    use_cases: List[str]
    peers: List[str]
    providers: List[str]
    actions: List[AgentAction]
    notes: List[str]
    timeline: List[str] = field(default_factory=list)
    # --- O-RAN compatibility fields (schema v2) --------------------------------
    # These are what Compose checks before a chain is accepted: dependency
    # (requires ⊆ produced upstream), interface (shared E2SM/A1 data models
    # between consecutive steps), control scope (write/write on the same
    # resource needs a lease order) and timescale (no near-RT step after a
    # non-RT step without an observation in between).
    app_type: str = "xapp"                 # xapp | rapp | orchestrator
    ric: str = "near-rt"                   # near-rt | non-rt | none
    vendor: str = "Aalto 6G Lab"
    version: str = "1.0.0"
    interfaces: List[str] = field(default_factory=list)      # e.g. E2SM-KPM v3.00, E2SM-RC v1.03, A1-P policy-type 20008, O1
    consumes: List[str] = field(default_factory=list)        # data models / KPI names it needs upstream
    produces: List[str] = field(default_factory=list)        # data models / KPI names / decisions it emits
    control_scopes: List[ControlScope] = field(default_factory=list)
    timescale_s: float = 1.0                                 # typical decision period (near-RT 0.01–1 s, non-RT ≥ 1 s)
    requires: List[str] = field(default_factory=list)        # capability ids that must run earlier in the chain
    conflicts_with: List[str] = field(default_factory=list)  # lease classes it must not share a window with
    mcp_endpoint: str = ""                                   # MCP server URL exposing the actions as tools
    capabilities: List[str] = field(default_factory=list)    # discovery vocabulary, e.g. energy_saving, qoe_prediction
    # Declared workflow role: observe | analyze | control | validate ("" = derive it from
    # control_scopes and capabilities, see evaluation/label_rules.app_role). Must agree with the
    # scopes: a card with a write scope is control (or validate), a read-only card never is.
    workflow_role: str = ""
