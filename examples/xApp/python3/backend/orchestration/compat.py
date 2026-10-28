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

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

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


# ---------------------------------------------------------------------------
# Lifecycle check and repair helpers (Compose step of AppWeaver).
#
# `check_chain` above is unchanged; the helpers below only *use* it. Repair is
# registry-driven: it never looks at the intent or at any label.
# ---------------------------------------------------------------------------


def lifecycle_findings(registry: Dict[str, AgentCard], chain: Iterable[str]) -> List[Finding]:
    """Deprecated cards are visible to the planner but may not be deployed."""
    findings: List[Finding] = []
    for index, agent_id in enumerate(str(item).strip().lower() for item in chain if str(item).strip()):
        card = registry.get(agent_id)
        if card is not None and card.status == "deprecated":
            findings.append(Finding("lifecycle", "error", index, agent_id, "Card is deprecated; its runtime refuses to run it."))
    return findings


def _provides_capability(card: AgentCard, capability: str) -> bool:
    return capability in card.capabilities or capability in card.skills or capability == card.id


def _provides_data(card: AgentCard, data_model: str) -> bool:
    return data_model in card.produces or data_model in card.measurements


def _is_reader(card: AgentCard) -> bool:
    return bool(card.control_scopes) and all(scope.mode == "read" for scope in card.control_scopes)


def find_producer(
    registry: Dict[str, AgentCard],
    *,
    capability: Optional[str] = None,
    data_model: Optional[str] = None,
    exclude: Iterable[str] = (),
) -> Optional[AgentCard]:
    """Pick the registry card that provides a missing capability / data model.

    Deterministic preference: executable, active cards only; near-RT xApps before
    rApps; read-only observers before writers; fewest own requirements; then id.
    """
    excluded = {str(item).lower() for item in exclude}
    candidates = []
    for card in registry.values():
        if card.id in excluded or not card.actions or card.status == "deprecated":
            continue
        if capability is not None and not _provides_capability(card, capability):
            continue
        if data_model is not None and not _provides_data(card, data_model):
            continue
        candidates.append(card)
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c.app_type != "xapp", not _is_reader(c), len(c.requires) + len(c.consumes), c.id))
    return candidates[0]


def _same_family_active(registry: Dict[str, AgentCard], card: AgentCard, exclude: Iterable[str]) -> Optional[AgentCard]:
    parts = card.id.split(".")
    if parts[0] != "rapp" or len(parts) < 2:
        return None
    family = ".".join(parts[:2])
    excluded = {str(item).lower() for item in exclude}
    options = [
        other for other in registry.values()
        if other.id not in excluded and other.status != "deprecated" and other.actions
        and (other.id == family or other.id.startswith(family + "."))
    ]
    options.sort(key=lambda c: (c.id != family, c.id))
    return options[0] if options else None


_NEED_RE = re.compile(r"(Requires capability|Consumes) '([^']+)'")


def repair_chain(
    registry: Dict[str, AgentCard],
    chain: Iterable[str],
    *,
    exclude: Iterable[str] = (),
    max_iterations: int = 0,
) -> Tuple[List[str], List[Dict[str, object]], CompatReport]:
    """Repair a candidate chain until `check_chain` (+ lifecycle) is clean or no move is left.

    Moves, applied to the first error each iteration (fixpoint re-check after each):
      * unknown id                      -> drop it
      * deprecated card                 -> replace by the active card of its family, else drop
      * missing capability / data model -> move an existing later producer in front of the
                                           consumer, else insert the registry's producer
                                           (`find_producer`) immediately before it; drop the
                                           consumer only when nothing in the registry provides it
      * control-scope conflict          -> drop the later (conflicting) writer
    ``exclude`` lists ids that may not be inserted (e.g. busy applications).
    Returns (chain, events, final_report); final_report.ok is False when repair gave up.
    """
    current = [str(item).strip().lower() for item in chain if str(item).strip()]
    excluded = {str(item).lower() for item in exclude}
    events: List[Dict[str, object]] = []
    limit = max_iterations or (2 * len(current) + 8)
    inserted_for: set = set()

    def full_report(ids: List[str]) -> CompatReport:
        report = check_chain(registry, ids)
        report.findings.extend(lifecycle_findings(registry, ids))
        report.checks_run = list(report.checks_run) + ["lifecycle"]
        return report

    report = full_report(current)
    for _ in range(limit):
        errors = [f for f in report.findings if f.severity == "error"]
        if not errors:
            break
        finding = sorted(errors, key=lambda f: f.step_index)[0]
        index, agent_id = finding.step_index, finding.agent_id
        card = registry.get(agent_id)
        if card is None:
            current.pop(index)
            events.append({"move": "drop_unknown", "agent_id": agent_id, "index": index, "detail": finding.detail})
        elif finding.check == "lifecycle":
            replacement = _same_family_active(registry, card, excluded | set(current))
            if replacement is not None:
                current[index] = replacement.id
                events.append({"move": "replace_deprecated", "agent_id": agent_id, "replacement": replacement.id, "index": index})
            else:
                current.pop(index)
                events.append({"move": "drop_deprecated", "agent_id": agent_id, "index": index})
        elif finding.check == "dependency":
            match = _NEED_RE.search(finding.detail)
            kind, need = (match.group(1), match.group(2)) if match else ("", "")
            is_cap = kind.startswith("Requires")
            later = [
                j for j in range(index + 1, len(current))
                if registry.get(current[j]) is not None
                and (_provides_capability(registry[current[j]], need) if is_cap else _provides_data(registry[current[j]], need))
            ]
            key = (agent_id, need)
            if later and key not in inserted_for:
                moved = current.pop(later[0])
                current.insert(index, moved)
                inserted_for.add(key)
                events.append({"move": "reorder_producer", "agent_id": moved, "before": agent_id, "need": need, "index": index})
            else:
                producer = None
                if key not in inserted_for:
                    producer = find_producer(
                        registry,
                        capability=need if is_cap else None,
                        data_model=None if is_cap else need,
                        exclude=excluded | set(current),
                    )
                if producer is not None:
                    current.insert(index, producer.id)
                    inserted_for.add(key)
                    events.append({"move": "insert_producer", "agent_id": producer.id, "before": agent_id, "need": need, "index": index})
                else:
                    current.pop(index)
                    events.append({"move": "drop_unsatisfiable", "agent_id": agent_id, "need": need, "index": index})
        else:
            current.pop(index)
            events.append({"move": f"drop_{finding.check}", "agent_id": agent_id, "index": index, "detail": finding.detail})
        report = full_report(current)
        if not current:
            break
    if not report.ok:
        events.append({"move": "gave_up", "errors": [f.to_dict() for f in report.findings if f.severity == "error"]})
    return current, events, report
