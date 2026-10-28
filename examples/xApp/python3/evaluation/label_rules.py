"""Pre-registered label rule for workflow correctness (primary accuracy metric).

Decided by the owner on 2026-10-28 (REVISION_PLAN.md §3c O6/O8) and fixed here before the final
batches. The rule is applied identically to every method; it is derived only from an intent's
labelled chain(s) (`expected_workflow` + `accepted_workflows`) and the Agent Cards' declared roles,
scopes, dependencies and conflicts -- never from any method's output.

Rule (see evaluation/METRICS.md for the prose version)
------------------------------------------------------
A generated chain is *correct* iff

1. every step is an active (not deprecated), executable card of the run's Agent Registry;
2. it contains every **required** app of the intent (a required slot may list interchangeable
   alternatives, e.g. a canonical rApp and the vendor variant an accepted chain names);
3. it respects the intent's **partial order**: for two required slots a, b that every labelled chain
   orders a before b, a must precede b in the generated chain when
   - role(a) < role(b) with observe < analyze < control  (observe/analyze before control), or
   - b depends on a (b `requires` a capability of a, or `consumes` a non-RAN data model a produces), or
   - a declares b's capability / write resource in `conflicts_with` (compat would reject b then a);
   pairs the labels order *against* the role ranks (the slice-assurance template SLICE -> KPM -> RC)
   and pairs of equal rank without a dependency (SLICE, TC) are unconstrained;
4. every **validate** step comes after every control step in the chain (control < validate);
5. it contains no **forbidden writer**: a control-role app (write scope) that no labelled chain of the
   intent contains;
6. any other extra step is read-only (observe / analyze / validate role) -- allowed (O8).

Uniform policy for observation and validation (one policy for all 80 intents):
* **Validation (RC) is never required** but is allowed and ordered (rule 4). The labels are
  inconsistent on whether a control chain ends in RC (`energy_saving_wakeup_guard` vs
  `night_energy_saving`, the TC-only templates); "required everywhere" would contradict labels, so
  validate is optional-but-ordered everywhere.
* **Observation (KPM, or PM as a KPI source) is required exactly when every labelled chain of the
  intent contains it**, like any other app: observation produces the data that the downstream
  analytics/control steps declare as `requires: kpi_monitoring`, and for investigation intents it is the
  only non-validation step. Extra observation steps are read-only and therefore always allowed.

Roles come from the cards (`app_role`): a declared `workflow_role` if the card has one, otherwise
validate if the card advertises a validation capability, control if any control scope is `write`,
observe if it provides `kpi_monitoring`, analyze otherwise.

Interface for the harness::

    from evaluation.label_rules import rule_match
    ok, reasons = rule_match(generated_workflow, intent, AGENTS)   # AGENTS = the run's registry
    record["workflow_match_rule"] = ok
    record["workflow_rule_reasons"] = reasons
"""
from __future__ import annotations

import os
import re
import sys
from itertools import permutations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.compat import RAN_PROVIDED_PREFIXES  # noqa: E402

RULE_VERSION = "2026-10-28"
ROLE_RANK = {"observe": 0, "analyze": 1, "control": 2, "validate": 3}
VALIDATION_CAPABILITIES = {"control_validation"}
OBSERVATION_CAPABILITIES = {"kpi_monitoring"}
SLOT_SEP = "|"


class LabelError(ValueError):
    """A labelled chain names an app the registry does not contain."""


# ---------------------------------------------------------------- card helpers
def normalize_chain(value: Any) -> List[str]:
    """Same normalisation as run_harness.normalize_generated_workflow (upper-case ids)."""
    if isinstance(value, (list, tuple)):
        return [str(item).strip().upper() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"\s*(?:->|=>|→|,|\|)\s*", value.strip())
        return [part.strip().upper() for part in parts if part.strip()]
    return []


def _card(registry: Dict[str, Any], app: str) -> Any:
    return registry.get(str(app).strip().lower())


def _write_resources(card: Any) -> Set[str]:
    return {scope.resource or scope.target for scope in getattr(card, "control_scopes", []) or [] if scope.mode == "write"}


def _provides(card: Any) -> Set[str]:
    return set(card.capabilities) | set(card.skills) | {card.id}


def app_role(card: Any) -> str:
    """observe | analyze | control | validate, from the card's declared role, scopes and capabilities."""
    declared = str(getattr(card, "workflow_role", "") or "").strip().lower()
    if declared in ROLE_RANK:
        return declared
    caps = set(getattr(card, "capabilities", []) or [])
    if caps & VALIDATION_CAPABILITIES:
        return "validate"
    if _write_resources(card):
        return "control"
    if caps & OBSERVATION_CAPABILITIES:
        return "observe"
    return "analyze"


def role_consistent(card: Any) -> bool:
    """A declared role must agree with the scopes: control <=> write scope (validate may write)."""
    role = app_role(card)
    writes = bool(_write_resources(card))
    if role == "control":
        return writes
    if role in {"observe", "analyze"}:
        return not writes
    return True


def _depends_on(later: Any, earlier: Any) -> bool:
    if set(later.requires) & _provides(earlier):
        return True
    needed = {d for d in later.consumes if not str(d).startswith(RAN_PROVIDED_PREFIXES)}
    return bool(needed & set(earlier.produces))


def _must_precede_by_conflict(first: Any, second: Any) -> bool:
    """compat rejects `first` placed after `second` when `first` writes and declares `second` conflicting."""
    if not _write_resources(first):
        return False
    declared = set(first.conflicts_with)
    return bool(declared & _provides(second)) or bool(declared & _write_resources(second))


# ---------------------------------------------------------------- rule derivation
def labelled_chains(intent: Dict[str, Any]) -> List[List[str]]:
    chains = [normalize_chain(chain) for chain in (intent.get("accepted_workflows") or [])]
    chains = [chain for chain in chains if chain] or [normalize_chain(intent.get("expected_workflow"))]
    unique: List[List[str]] = []
    for chain in chains:
        if chain and chain not in unique:
            unique.append(chain)
    return unique


def _slot_key(slot: Sequence[str]) -> str:
    return SLOT_SEP.join(slot)


def derive_rule(intent: Dict[str, Any], registry: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the label rule of one intent from its labelled chain(s) and the cards in `registry`.

    Returns a JSON-serialisable dict: required (slots, "A|B" = any of), order ([a, b] pairs over slot
    keys), order_basis, validate_after_control, forbidden_writers, optional_readonly_ok, optional_apps,
    roles, version.
    """
    chains = labelled_chains(intent)
    if not chains:
        raise LabelError(f"{intent.get('id')}: no labelled chain")
    roles: Dict[str, str] = {}
    for chain in chains:
        for app in chain:
            card = _card(registry, app)
            if card is None:
                raise LabelError(f"{intent.get('id')}: labelled app {app} is not in the registry")
            roles[app] = app_role(card)

    def is_write(app: str) -> bool:
        return roles[app] == "control"

    # Validation steps are never required (uniform policy); everything else in every chain is.
    core = [list(dict.fromkeys(a for a in chain if roles[a] != "validate")) for chain in chains]
    common = set(core[0]).intersection(*map(set, core[1:])) if core else set()
    slots: List[List[str]] = [[app] for app in core[0] if app in common]
    residual = [[a for a in chain if a not in common] for chain in core]
    optional: Set[str] = set()
    # Apps that differ between accepted chains: if every chain has one of the same class (write or
    # read) they are interchangeable alternatives for one required slot; otherwise they are optional.
    for write_class in (True, False):
        per_chain = [[a for a in r if is_write(a) == write_class] for r in residual]
        members = sorted({a for r in per_chain for a in r})
        if not members:
            continue
        if all(per_chain):
            slots.append(members)
        else:
            optional.update(members)

    def first_pos(slot: Sequence[str], chain: Sequence[str]) -> Optional[int]:
        positions = [chain.index(a) for a in slot if a in chain]
        return min(positions) if positions else None

    # Display order of slots: position in the first labelled chain.
    slots.sort(key=lambda s: (first_pos(s, chains[0]) if first_pos(s, chains[0]) is not None else 10**6, _slot_key(s)))

    def rank(slot: Sequence[str]) -> int:
        return min(ROLE_RANK[roles[a]] for a in slot)

    order: List[List[str]] = []
    basis: Dict[str, str] = {}
    for a_slot, b_slot in permutations(slots, 2):
        positions = [(first_pos(a_slot, ch), first_pos(b_slot, ch)) for ch in chains]
        if not all(pa is not None and pb is not None and pa < pb for pa, pb in positions):
            continue  # the labels do not agree on a before b
        cards_a = [_card(registry, a) for a in a_slot]
        cards_b = [_card(registry, b) for b in b_slot]
        if rank(a_slot) < rank(b_slot):
            why = "role"
        elif any(_depends_on(cb, ca) for ca in cards_a for cb in cards_b):
            why = "dependency"
        elif any(_must_precede_by_conflict(ca, cb) for ca in cards_a for cb in cards_b):
            why = "conflict"
        else:
            continue
        order.append([_slot_key(a_slot), _slot_key(b_slot)])
        basis[f"{_slot_key(a_slot)}<{_slot_key(b_slot)}"] = why
    order.sort(key=lambda pair: ([_slot_key(s) for s in slots].index(pair[0]), [_slot_key(s) for s in slots].index(pair[1])))

    required_apps = {a for slot in slots for a in slot}
    forbidden = sorted(
        str(card_id).upper()
        for card_id, card in registry.items()
        if app_role(card) == "control" and str(card_id).upper() not in required_apps | optional
    )
    if not slots:
        raise LabelError(f"{intent.get('id')}: rule has no required app (labelled chain is validation-only)")
    return {
        "version": RULE_VERSION,
        "required": [_slot_key(slot) for slot in slots],
        "order": order,
        "order_basis": basis,
        "validate_after_control": True,
        "validate_optional": True,
        "forbidden_writers": forbidden,
        "optional_readonly_ok": True,
        "optional_apps": sorted(optional),
        "roles": {app: roles[app] for app in sorted(roles)},
    }


# ---------------------------------------------------------------- matching
def rule_match(chain: Any, intent: Dict[str, Any], registry: Dict[str, Any],
               rule: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
    """Is `chain` correct for `intent` under the pre-registered rule?

    chain     generated workflow (list of app ids, any case, or an "A -> B" string)
    intent    the intent dict (uses `label_rule` if present, else derives it from the labels)
    registry  the run's Agent Registry {lower-case id: AgentCard} (the harness's AGENTS)
    Returns (correct, reasons); reasons is empty iff correct.
    """
    apps = normalize_chain(chain)
    if not apps:
        return False, ["empty chain"]
    if rule is None:
        rule = intent.get("label_rule") or derive_rule(intent, registry)
    reasons: List[str] = []
    slots = [str(slot).split(SLOT_SEP) for slot in rule.get("required") or []]
    labelled = {a for slot in slots for a in slot} | set(rule.get("optional_apps") or [])
    forbidden = set(rule.get("forbidden_writers") or [])

    role_of: Dict[str, str] = {}
    for app in dict.fromkeys(apps):
        card = _card(registry, app)
        if card is None:
            reasons.append(f"{app}: not in the registry")
            continue
        role_of[app] = app_role(card)
        if str(getattr(card, "status", "")) == "deprecated":
            reasons.append(f"{app}: deprecated card")
        if not getattr(card, "actions", None):
            reasons.append(f"{app}: not executable (card has no actions)")
        if app not in labelled and (role_of[app] == "control" or app in forbidden):
            reasons.append(f"{app}: forbidden writer (write scope, not required by the intent)")

    for slot in slots:
        if not any(a in apps for a in slot):
            reasons.append(f"missing required {_slot_key(slot)}")

    def first(slot_key: str) -> Optional[int]:
        positions = [i for i, a in enumerate(apps) if a in slot_key.split(SLOT_SEP)]
        return min(positions) if positions else None

    def last(slot_key: str) -> Optional[int]:
        positions = [i for i, a in enumerate(apps) if a in slot_key.split(SLOT_SEP)]
        return max(positions) if positions else None

    for a_key, b_key in rule.get("order") or []:
        pa, pb = first(a_key), last(b_key)
        if pa is not None and pb is not None and not pa < pb:
            reasons.append(f"order: {a_key} must precede {b_key}")

    if rule.get("validate_after_control", True):
        control = [i for i, a in enumerate(apps) if role_of.get(a) == "control"]
        validate = [i for i, a in enumerate(apps) if role_of.get(a) == "validate"]
        if control and validate and min(validate) < max(control):
            reasons.append(f"order: validation step {apps[min(validate)]} before control step {apps[max(control)]}")
    return (not reasons), reasons


# ---------------------------------------------------------------- registry
def build_registry(rapp_directory: bool = True, agent_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """The Agent Registry as the portal builds it (`backend.agents.build_agents`).

    rapp_directory=True adds the rApp Directory (FLEXRIC_RAPP_DIRECTORY=1). `agent_ids` restricts the
    registry to the cards a run actually had (manifest -> registry.agent_ids), so a Batch A record that
    names an rApp is scored as a hallucination, as it was at run time.
    """
    from backend.agents.registry import build_agents

    previous = os.environ.get("FLEXRIC_RAPP_DIRECTORY")
    os.environ["FLEXRIC_RAPP_DIRECTORY"] = "1" if rapp_directory else "0"
    try:
        registry = build_agents(sys.executable, ROOT)
    finally:
        if previous is None:
            os.environ.pop("FLEXRIC_RAPP_DIRECTORY", None)
        else:
            os.environ["FLEXRIC_RAPP_DIRECTORY"] = previous
    if agent_ids is not None:
        keep = {str(a).lower() for a in agent_ids}
        registry = {k: v for k, v in registry.items() if k in keep}
    return registry
