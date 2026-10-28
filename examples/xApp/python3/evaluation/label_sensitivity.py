"""Pre-registered label sensitivity analysis (2026-10-28).

The primary metric is `label_rules.rule_match` with the committed `label_rule` of each intent. Four
labels were questioned by the label review (workstream B) from the intent wording alone, before any
final-batch result for these intents existed. They are NOT changed. Instead each gets one alternative
reading, fixed here, and the paper reports rule accuracy under the committed labels (primary) and under
"committed OR alternative" (sensitivity row). A record that passes the committed rule always passes the
sensitivity rule, so the sensitivity row can only be equal or higher, for every method alike.

Alternatives
------------
check-only TC intents (`ecn_policy_validation`, `codel_rollback_verification`, `qos_policy_sanity_check`)
    The intents ask to validate / verify / sanity-check a TC policy, but TC has only apply actions, so the
    committed label requires a TC write. Alternative: a read-only verification is also correct — the chain
    observes (KPM required), may validate (RC, after any control), and contains no control-role write.
`priority_for_emergency_ues`
    The committed label requires QoE prediction only because the `ue_qos_control` card requires it, while the
    intent already names the UEs. Alternative: the same chain without RAPP.QOE_PREDICTION is also correct.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

from evaluation.label_rules import app_role, derive_rule, rule_match

PREREGISTERED = "2026-10-28"

CHECK_ONLY_TC = ("ecn_policy_validation", "codel_rollback_verification", "qos_policy_sanity_check")
DROP_QOE = ("priority_for_emergency_ues",)
INTENTS = CHECK_ONLY_TC + DROP_QOE


def _upper(ids: List[str]) -> List[str]:
    return [str(item).upper() for item in ids]


def alternative_rule(intent: Dict[str, Any], registry: Dict[str, Any]) -> Dict[str, Any] | None:
    """The pre-registered alternative label rule for `intent`, or None if it has none."""
    intent_id = str(intent.get("id") or "")
    if intent_id not in INTENTS:
        return None
    rule = copy.deepcopy(intent.get("label_rule") or derive_rule(intent, registry))
    if intent_id in CHECK_ONLY_TC:
        writers = sorted({card_id.upper() for card_id, card in registry.items() if app_role(card) == "control"})
        rule["required"] = ["KPM"]
        rule["order"] = []
        rule["forbidden_writers"] = sorted(set(_upper(rule.get("forbidden_writers") or [])) | set(writers))
    else:
        rule["required"] = [slot for slot in rule.get("required") or [] if "RAPP.QOE_PREDICTION" not in str(slot).upper()]
        rule["order"] = [pair for pair in rule.get("order") or [] if "RAPP.QOE_PREDICTION" not in _upper(pair)]
    rule["sensitivity_alternative"] = PREREGISTERED
    return rule


def sensitivity_match(chain: Any, intent: Dict[str, Any], registry: Dict[str, Any]) -> Tuple[bool, str]:
    """(passes committed OR alternative rule, which one passed: 'committed' | 'alternative' | '')."""
    ok, _ = rule_match(chain, intent, registry)
    if ok:
        return True, "committed"
    alt = alternative_rule(intent, registry)
    if alt is not None and rule_match(chain, intent, registry, rule=alt)[0]:
        return True, "alternative"
    return False, ""
