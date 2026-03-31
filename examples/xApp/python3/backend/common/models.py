from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentAction:
    id: str
    label: str
    description: str
    kind: str
    command: List[str] = field(default_factory=list)


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
