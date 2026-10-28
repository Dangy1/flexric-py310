"""Pre-registered label sensitivity (evaluation/label_sensitivity.py)."""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.label_rules import build_registry, rule_match
from evaluation.label_sensitivity import INTENTS, alternative_rule, sensitivity_match

HERE = Path(__file__).resolve().parents[1]
REGISTRY = build_registry(rapp_directory=True)


def _intents(name):
    data = json.loads((HERE / name).read_text(encoding="utf-8"))
    return {i["id"]: i for i in (data.get("intents", data) if isinstance(data, dict) else data)}


def test_alternatives_only_for_the_four_preregistered_intents():
    v2 = _intents("intents_v2.json")
    assert set(INTENTS) <= set(v2)
    assert [i for i in v2 if alternative_rule(v2[i], REGISTRY) is not None] == [i for i in v2 if i in INTENTS]


def test_sensitivity_never_lowers_a_committed_match():
    v2 = _intents("intents_v2.json")
    for intent in v2.values():
        for chain in [intent["expected_workflow"], *(intent.get("accepted_workflows") or [])]:
            assert rule_match(chain, intent, REGISTRY)[0]
            assert sensitivity_match(chain, intent, REGISTRY) == (True, "committed")


def test_check_only_tc_accepts_read_only_verification():
    intent = _intents("intents_v2.json")["ecn_policy_validation"]
    assert not rule_match(["KPM", "RC"], intent, REGISTRY)[0]
    assert sensitivity_match(["KPM", "RC"], intent, REGISTRY) == (True, "alternative")
    assert sensitivity_match(["KPM", "SLICE", "RC"], intent, REGISTRY)[0] is False  # a write is still wrong


def test_emergency_ues_without_qoe_prediction():
    intent = _intents("intents_v2.json")["priority_for_emergency_ues"]
    chain = ["KPM", "RAPP.UE_QOS_CONTROL"]
    assert not rule_match(chain, intent, REGISTRY)[0]
    assert sensitivity_match(chain, intent, REGISTRY) == (True, "alternative")
