"""Compose-time compatibility checks over Agent Cards (schema v2).

A candidate chain is a list of agent ids in execution order. Each check returns
findings; a chain is accepted only when no finding has severity "error".
Warnings are logged with the workflow so the operator can see what the
planner was allowed to get away with.

Checks
------
dependency     every `requires` entry and every `consumes` data model of step k
               is satisfied by the capabilities/`produces` of some step < k
               (or by the live RAN for raw E2SM measurements).
interface      consecutive steps share at least one interface family or one
               data model (the output of one is readable by the next).
control_scope  two write steps on the same lease resource need an explicit
               ordering (they are serialised by the scheduler, which is fine)
               but a write step followed by a *read-only validation* of a
               different resource is flagged; two writers on `conflicts_with`
               resources in one chain is an error.
timescale      a near-RT step scheduled after a non-RT step must be separated
               by an observation step, otherwise the near-RT loop acts on a
               stale non-RT decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from backend.common.models import AgentCard

# Raw E2SM measurements are produced by the RAN itself, so an observation
# agent may consume them without an upstream producer in the chain.
RAN_PROVIDED_PREFIXES = ("RRU.", "DRB.", "RRC.", "E2SM-", "MAC.", "RLC.", "PDCP.", "GTP.", "CARR.", "QosFlow.", "PEE.")


@dataclass
class Finding:
    check: str
    severity: str  # error | warning | info
    step_index: int
    agent_id: str
    detail: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "check": self.check,
            "severity": self.severity,
            "step_index": self.step_index,
            "agent_id": self.agent_id,
            "detail": self.detail,
        }


@dataclass
class CompatReport:
    chain: List[str]
    findings: List[Finding] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=lambda: ["dependency", "interface", "control_scope", "timescale"])

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> Dict[str, object]:
        return {
            "chain": list(self.chain),
            "ok": self.ok,
            "checks_run": list(self.checks_run),
            "error_count": sum(1 for f in self.findings if f.severity == "error"),
            "warning_count": sum(1 for f in self.findings if f.severity == "warning"),
            "findings": [f.to_dict() for f in self.findings],
        }


def _interface_family(interface: str) -> str:
    # "E2SM-KPM v3.00" -> "E2SM-KPM"; "A1-P policy-type 20008" -> "A1-P"
    return interface.split(" ")[0].strip().upper()


def _ran_provided(name: str) -> bool:
    return name.startswith(RAN_PROVIDED_PREFIXES)


def _write_scopes(card: AgentCard) -> List[str]:
    return [scope.resource or scope.target for scope in card.control_scopes if scope.mode == "write"]


def check_chain(registry: Dict[str, AgentCard], chain: Iterable[str]) -> CompatReport:
    ids = [str(item).strip().lower() for item in chain if str(item).strip()]
    report = CompatReport(chain=ids)
    cards: List[Optional[AgentCard]] = [registry.get(agent_id) for agent_id in ids]

    for index, (agent_id, card) in enumerate(zip(ids, cards)):
        if card is None:
            report.findings.append(Finding("dependency", "error", index, agent_id, "Agent is not in the registry (hallucinated reference)."))
    if not report.ok:
        return report

    available_caps: set = set()
    available_data: set = set()
    held_writes: Dict[str, int] = {}
    for index, card in enumerate(cards):
        assert card is not None
        # dependency
        for requirement in card.requires:
            if requirement not in available_caps:
                report.findings.append(Finding("dependency", "error", index, card.id, f"Requires capability '{requirement}' which no earlier step provides."))
        for data_model in card.consumes:
            if data_model in available_data or _ran_provided(data_model):
                continue
            report.findings.append(Finding("dependency", "error", index, card.id, f"Consumes '{data_model}' which no earlier step produces."))
        # interface
        if index > 0:
            prev = cards[index - 1]
            assert prev is not None
            shared_family = {_interface_family(i) for i in prev.interfaces} & {_interface_family(i) for i in card.interfaces}
            shared_data = set(prev.produces) & set(card.consumes)
            if not shared_family and not shared_data and card.consumes:
                report.findings.append(Finding("interface", "warning", index, card.id, f"No shared interface or data model with previous step '{prev.id}'."))
        # control scope
        # conflicts_with may name lease resources or capabilities of earlier writers
        conflicting_caps = set(card.conflicts_with) & available_caps
        if _write_scopes(card) and conflicting_caps:
            report.findings.append(Finding("control_scope", "error", index, card.id, f"Writes while a conflicting capability is active earlier in the chain: {sorted(conflicting_caps)}."))
        for resource in _write_scopes(card):
            if resource in held_writes:
                report.findings.append(Finding("control_scope", "warning", index, card.id, f"Second writer on '{resource}' after step {held_writes[resource]}; scheduler will serialise them."))
            for other_resource, other_index in held_writes.items():
                if other_resource in card.conflicts_with:
                    report.findings.append(Finding("control_scope", "error", index, card.id, f"Writes while '{other_resource}' (step {other_index}) is declared conflicting."))
            held_writes[resource] = index
        # timescale
        if index > 0:
            prev = cards[index - 1]
            assert prev is not None
            if prev.ric == "non-rt" and card.ric == "near-rt" and card.control_scopes and not any(scope.mode == "read" for scope in card.control_scopes):
                report.findings.append(Finding("timescale", "warning", index, card.id, f"Near-RT control step directly after non-RT step '{prev.id}' without a fresh observation."))
        available_caps |= set(card.capabilities) | set(card.skills) | {card.id}
        available_data |= set(card.produces) | set(card.measurements)
    return report
