"""Labels, label rules and Agent Cards agree (FABLE_REVIEW_AND_PLAN P0-3 / P0-5).

Run:  python -m pytest evaluation/tests -q     (or: python evaluation/tests/test_labels.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.compat import check_chain  # noqa: E402
from evaluation.build_label_rules import FILES, annotate, dump  # noqa: E402
from evaluation.label_rules import (  # noqa: E402
    app_role,
    build_registry,
    derive_rule,
    labelled_chains,
    role_consistent,
    rule_match,
)

EVAL = ROOT / "evaluation"
REGISTRY = build_registry(rapp_directory=True)  # FLEXRIC_RAPP_DIRECTORY=1, as Batch B / the portal stack
BASE_REGISTRY = build_registry(rapp_directory=False)  # Batch A registry (9 portal cards)


def _intents(name: str):
    return json.loads((EVAL / name).read_text(encoding="utf-8"))


ALL = [(name, intent) for name in FILES for intent in _intents(name)]
V2 = {intent["id"]: intent for intent in _intents("intents_v2.json")}


# ---------------------------------------------------------------- labels vs rule and compat
def test_every_intent_has_current_label_rule():
    for name, layout in FILES.items():
        intents = _intents(name)
        assert all("label_rule" in intent for intent in intents), name
        assert (EVAL / name).read_text(encoding="utf-8") == dump(annotate(intents, REGISTRY), layout), (
            f"{name}: label_rule out of date; run evaluation/build_label_rules.py")


def test_labelled_chains_pass_their_own_rule():
    failures = []
    for name, intent in ALL:
        for chain in labelled_chains(intent):
            ok, reasons = rule_match(chain, intent, REGISTRY)
            ok_derived, _ = rule_match(chain, intent, REGISTRY, rule=derive_rule(intent, REGISTRY))
            if not (ok and ok_derived):
                failures.append((name, intent["id"], chain, reasons))
    assert not failures, failures


def test_labelled_chains_pass_compat_with_rapp_directory():
    failures = []
    for name, intent in ALL:
        for chain in labelled_chains(intent):
            report = check_chain(REGISTRY, chain).to_dict()
            if report["error_count"]:
                failures.append((name, intent["id"], chain, [f["detail"] for f in report["findings"] if f["severity"] == "error"]))
    assert not failures, failures


def test_base_labels_pass_on_the_batch_a_registry():
    for intent in _intents("intents_50.json"):
        for chain in labelled_chains(intent):
            assert rule_match(chain, intent, BASE_REGISTRY)[0], (intent["id"], chain)
            assert check_chain(BASE_REGISTRY, chain).ok, (intent["id"], chain)


def test_rules_are_well_formed():
    for _, intent in ALL:
        rule = intent["label_rule"]
        assert rule["required"], intent["id"]
        assert rule["optional_readonly_ok"] is True
        keys = set(rule["required"])
        for a, b in rule["order"]:
            assert a in keys and b in keys, (intent["id"], a, b)
        required_apps = {app for slot in rule["required"] for app in slot.split("|")}
        assert not required_apps & set(rule["forbidden_writers"]), intent["id"]
        assert "RC" not in required_apps, intent["id"]  # validation is optional-but-ordered everywhere


def test_annotations_kept_and_labels_unchanged():
    base = {intent["id"]: intent for intent in _intents("intents_50.json")}
    for intent_id, intent in base.items():
        assert "notes" in intent and "category" in intent
        assert V2[intent_id]["expected_workflow"] == intent["expected_workflow"]


# ---------------------------------------------------------------- cards
def test_card_roles_are_consistent_with_scopes():
    bad = [card_id for card_id, card in REGISTRY.items() if not role_consistent(card)]
    assert not bad, bad
    assert app_role(REGISTRY["kpm"]) == "observe"
    assert app_role(REGISTRY["slice"]) == "control"
    assert app_role(REGISTRY["tc"]) == "control"
    # The label policy treats RC as the validation step; a re-carded RC must keep that role
    # (workflow_role="validate" or a `control_validation` capability) or the rule changes.
    assert app_role(REGISTRY["rc"]) == "validate"


def test_card_fixes():
    assert "slice.policy" not in REGISTRY["rapp.slice_sla"].consumes
    assert "kpi_monitoring" in REGISTRY["rapp.pm_kpi"].capabilities
    for card in REGISTRY.values():
        if card.status == "deprecated":
            assert card.description.startswith("DEPRECATED"), card.id
        if card.app_type == "rapp":
            assert "Use when" in card.description and "Do not use when" in card.description, card.id
    monitor = next(a for a in REGISTRY["slice"].actions if a.id == "monitor")
    static = next(a for a in REGISTRY["slice"].actions if a.id == "apply-static")
    assert [s.mode for s in monitor.control_scopes] == ["read"]
    assert [s.mode for s in static.control_scopes] == ["write"]


# ---------------------------------------------------------------- rule semantics (pre-registered examples)
def _ok(intent_id: str, chain: str, registry=REGISTRY) -> bool:
    return rule_match(chain, V2[intent_id], registry)[0]


def test_observe_first_reordering_is_accepted():  # O6
    assert _ok("slice_fairness_assurance", "SLICE->KPM->RC")
    assert _ok("slice_fairness_assurance", "KPM->SLICE->RC")
    # where every label observes first, observing after control is wrong
    assert not _ok("xr_latency_guard", "SLICE->KPM->TC->RC")
    # two control steps of equal rank are unordered
    assert _ok("xr_latency_guard", "KPM->TC->SLICE->RC")


def test_extra_read_only_analytics_allowed_substitution_wrong():  # O8
    assert _ok("downlink_jitter_containment", "KPM->RAPP.ANOMALY_DETECTION->TC->RC")
    assert _ok("downlink_jitter_containment", "KPM->RAPP.QOE_PREDICTION->TC->RC")
    # TRANSPORT_QOS writes tc_control: an extra writer, and here it replaces TC
    ok, reasons = rule_match("KPM->RAPP.TRANSPORT_QOS->RC", V2["backhaul_queue_conflict_recovery"], REGISTRY)
    assert not ok and any("forbidden writer" in r for r in reasons) and any("missing required TC" in r for r in reasons)
    assert not _ok("downlink_jitter_containment", "KPM->RAPP.TRANSPORT_QOS->TC->RC")
    assert not _ok("stadium_congestion_surge", "KPM->RAPP.CAPACITY_MGMT->RC")
    # a vendor variant of a read-only analytic is still read-only
    assert _ok("downlink_jitter_containment", "KPM->RAPP.ANOMALY_DETECTION.NORTHWIND->TC->RC")


def test_validation_optional_but_after_control():
    assert _ok("uplink_queue_stability", "KPM->TC")
    assert _ok("energy_saving_wakeup_guard", "KPM->RAPP.ENERGY_SAVING->RC")
    assert _ok("night_energy_saving", "KPM->RAPP.ENERGY_SAVING")
    assert not _ok("uplink_queue_stability", "KPM->RC->TC")
    assert _ok("gtp_tunnel_health_validation", "KPM")


def test_required_observation_and_tc_only():
    assert not _ok("uplink_queue_stability", "TC->RC")  # KPM is in the label
    assert _ok("transport_bufferbloat_mitigation", "TC")
    assert _ok("transport_bufferbloat_mitigation", "KPM->TC->RC")  # extra read-only observation
    assert not _ok("transport_bufferbloat_mitigation", "KPM->SLICE->TC->RC")  # SLICE is a forbidden writer here


def test_alternatives_dependencies_and_conflicts():
    assert _ok("night_energy_saving", "RAPP.PM_KPI->RAPP.ENERGY_SAVING->RC")
    assert not _ok("night_energy_saving", "RAPP.ENERGY_SAVING->RC")
    assert _ok("vendor_variant_trap", "KPM->RAPP.TRAFFIC_STEERING.NORTHWIND->RC")
    assert not _ok("load_balance_hotspot", "KPM->RAPP.TRAFFIC_STEERING.NORTHWIND->RC")  # variant not labelled here
    assert not _ok("steering_then_energy", "KPM->RAPP.ENERGY_SAVING->RAPP.TRAFFIC_STEERING->RC")  # declared conflict
    assert not _ok("spectrum_resplit", "KPM->RAPP.SPECTRUM_SHARING->RAPP.CAPACITY_MGMT->RC")  # dependency
    assert not _ok("cell_edge_qoe_protection", "KPM->RAPP.UE_QOS_CONTROL->RAPP.QOE_PREDICTION->RC")
    assert _ok("healing_full_chain", "KPM->RAPP.ROOT_CAUSE->RAPP.ANOMALY_DETECTION->RAPP.SELF_HEALING->RC")
    assert not _ok("rollout_blocked_by_energy", "RAPP.RAN_LIFECYCLE->RAPP.ENERGY_SAVING")
    assert not _ok("energy_vs_capacity_conflict", "KPM->RAPP.ENERGY_SAVING->RAPP.CAPACITY_MGMT->RC")


def test_invalid_steps():
    assert not _ok("deprecated_card_trap", "KPM->RAPP.ENERGY_SAVING.V0->RC")
    assert not _ok("uplink_queue_stability", "KPM->TC->MAC->RC")  # descriptive card, not executable
    assert not _ok("uplink_queue_stability", "KPM->TC_XAPP->RC")  # hallucinated
    assert not _ok("uplink_queue_stability", "")
    # Batch A had no rApp Directory: an rApp id there is a hallucination
    assert not _ok("downlink_jitter_containment", "KPM->RAPP.ANOMALY_DETECTION->TC->RC", BASE_REGISTRY)


if __name__ == "__main__":
    failed = 0
    for test_name, test in sorted((k, v) for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)):
        try:
            test()
            print(f"PASS {test_name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test_name}: {str(exc)[:2000]}")
    raise SystemExit(1 if failed else 0)
