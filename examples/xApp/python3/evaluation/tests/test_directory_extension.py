"""rApp Directory extension and L2 monitor xApps (workstream E, 2026-10-28).

Checks the families added to rapps/build_catalog.py, their emulated runtime rules, the executable
MAC/RLC/PDCP/GTP monitor cards, and the directory-extension intents of intents_v2.json (labels,
provenance and the distractors their labels are meant to exclude). Results-blind: nothing here reads
a run record.

Run:  python -m pytest -q evaluation/tests/test_directory_extension.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "rapps") not in sys.path:
    sys.path.insert(0, str(ROOT / "rapps"))

import build_catalog  # noqa: E402  (rapps/build_catalog.py)
import runtime as rapp_runtime  # noqa: E402  (rapps/runtime.py)
from backend.agents.registry import L2_MONITOR_IDS, build_agents  # noqa: E402
from backend.orchestration.compat import check_chain  # noqa: E402
from evaluation.build_intents_v2 import DIRECTORY_EXTENSION_INTENTS  # noqa: E402
from evaluation.label_rules import app_role, build_registry, rule_match  # noqa: E402

EVAL = ROOT / "evaluation"
REGISTRY = build_registry(rapp_directory=True)
V2 = {intent["id"]: intent for intent in json.loads((EVAL / "intents_v2.json").read_text(encoding="utf-8"))}
EXT_IDS = [item["id"] for item in DIRECTORY_EXTENSION_INTENTS]
NEW_FAMILIES = ["anr", "pci_optimization", "sleeping_cell", "mobility_load_balancing", "rach_optimization", "beamforming",
                "mimo_sleep", "traffic_forecast", "fault_prediction", "slice_admission", "signalling_storm",
                "ul_interference", "endc_steering", "config_audit", "crossed_feeder", "special_events"]


def _ok(intent_id: str, chain: str) -> bool:
    return rule_match(chain, V2[intent_id], REGISTRY)[0]


def _compat_ok(chain: str) -> bool:
    return check_chain(REGISTRY, [step.strip() for step in chain.split("->")]).ok


# ---------------------------------------------------------------- catalog
def test_catalog_json_is_generated_from_build_catalog():
    on_disk = json.loads((ROOT / "rapps" / "catalog.json").read_text(encoding="utf-8"))
    assert on_disk == build_catalog.build_catalog(), "run python rapps/build_catalog.py"


def test_new_families_present_with_card_conventions():
    catalog = build_catalog.build_catalog()
    families = {entry["family"] for entry in catalog}
    assert set(NEW_FAMILIES) <= families
    for entry in catalog:
        assert entry["vendor"] in build_catalog.VENDORS, entry["id"]  # emulated apps never carry real vendor names
        assert "Use when" in entry["description"] and "Do not use when" in entry["description"], entry["id"]
        writes = [s for s in entry["control_scopes"] if s["mode"] == "write"]
        assert entry["workflow_role"] == ("control" if writes else entry["workflow_role"]), entry["id"]
        if writes:
            assert all(s["resource"] for s in writes), entry["id"]  # a write scope names its lease resource
            assert any(rapp_runtime.is_apply_tool(t["id"]) for t in entry["tools"]), entry["id"]
        else:
            assert not any(rapp_runtime.is_apply_tool(t["id"]) for t in entry["tools"]), entry["id"]
        for data in entry["consumes"]:
            assert data.startswith(("RRU.", "DRB.", "RRC.", "CARR.", "PEE.", "RLC.")) or any(
                data in other["produces"] for other in catalog), (entry["id"], data)


def test_deprecated_releases_and_variants():
    catalog = build_catalog.build_catalog()
    for family in NEW_FAMILIES:
        members = [e for e in catalog if e["family"] == family]
        variants = next(f["variants"] for f in build_catalog.FAMILIES if f["family"] == family)
        assert len(members) == variants + (1 if variants > 1 else 0), family
        for entry in members:
            if entry["status"] == "deprecated":
                assert entry["description"].startswith("DEPRECATED") and entry["superseded_by"] == f"rapp.{family}"


def test_only_observation_cards_provide_kpi_monitoring():
    # repair_chain inserts the cheapest kpi_monitoring producer; a new card must not hijack that slot
    providers = sorted(card_id for card_id, card in REGISTRY.items() if "kpi_monitoring" in card.capabilities)
    assert all(card_id == "kpm" or card_id.startswith("rapp.pm_kpi") for card_id in providers), providers


def test_runtime_rules_cover_every_active_tool():
    catalog = rapp_runtime.load_catalog()
    snapshot = {"available": True, "cells": {
        str(i): {"RRU.PrbTotDl": v, "RRU.PrbTotUl": v, "DRB.UEThpDl": 10 * v, "DRB.UEThpUl": 0.5, "DRB.RlcSduDelayDl": 80 * v}
        for i, v in enumerate([0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 0.9, 1.0])}}
    for rapp_id, rapp in catalog.items():
        if rapp["status"] == "deprecated":
            continue
        for tool in rapp["tools"]:
            result = rapp_runtime.decide(rapp, tool["id"], snapshot)
            assert result["decision"], (rapp_id, tool["id"])
            assert result["emulated"] is True
    empty = rapp_runtime.decide(catalog["rapp.anr"], "detect_missing_neighbours", {"available": False, "cells": {}})
    assert empty["kpm_available"] is False and "add_relations" in empty["decision"]


# ---------------------------------------------------------------- declared conflicts
def test_new_conflict_pairs_are_mutual():
    for chain in ["KPM->RAPP.MOBILITY_LOAD_BALANCING->RAPP.MOBILITY_OPTIMIZATION",
                  "KPM->RAPP.MOBILITY_OPTIMIZATION->RAPP.MOBILITY_LOAD_BALANCING",
                  "KPM->RAPP.SPECIAL_EVENTS->RAPP.ENERGY_SAVING",
                  "KPM->RAPP.ENERGY_SAVING->RAPP.SPECIAL_EVENTS",
                  "KPM->RAPP.BEAMFORMING->RAPP.MIMO_SLEEP",
                  "KPM->RAPP.MIMO_SLEEP->RAPP.BEAMFORMING",
                  "KPM->RAPP.RET_TILT->RAPP.BEAMFORMING"]:
        assert not _compat_ok(chain), chain
    assert _compat_ok("KPM->RAPP.PCI_OPTIMIZATION->RAPP.ANR")
    assert _compat_ok("KPM->RAPP.TRAFFIC_FORECAST->RAPP.MIMO_SLEEP")


# ---------------------------------------------------------------- L2 monitor xApps
def test_l2_monitor_cards_are_executable_read_only():
    for agent_id in L2_MONITOR_IDS:
        card = REGISTRY[agent_id]
        assert app_role(card) == "observe", agent_id
        assert card.actions and all(s.mode == "read" for s in card.control_scopes), agent_id
        assert "kpi_monitoring" not in card.capabilities, agent_id
        for action in card.actions:
            assert action.control_scopes and all(s.mode == "read" for s in action.control_scopes), agent_id
            assert any(part.endswith("xapp_l2_monitor.py") for part in action.command), agent_id
            assert action.command[action.command.index("--sm") + 1] == agent_id
            assert "--duration-s" in action.command
        assert f'"{agent_id.upper()} ind tstamp="' in " ".join(card.notes), agent_id  # documented ack marker


def test_l2_monitors_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("FLEXRIC_L2_MONITORS", "0")
    registry = build_agents(sys.executable, ROOT)
    assert all(not registry[agent_id].actions for agent_id in L2_MONITOR_IDS)


def test_l2_monitor_script_markers_match_cards():
    source = (ROOT / "xapp_l2_monitor.py").read_text(encoding="utf-8")
    for agent_id in L2_MONITOR_IDS:
        assert f'f"{agent_id.upper()} ind tstamp=' in source, agent_id
    assert "control_" not in source.replace("control_scopes", "")  # never sends an E2 CONTROL


# ---------------------------------------------------------------- intents
def test_extension_intents_present_and_annotated():
    assert 20 <= len(EXT_IDS) <= 30 and len(set(EXT_IDS)) == len(EXT_IDS)
    doc = (ROOT / "docs" / "RAPP_USE_CASES.md").read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="(E\d\d)"></a>', doc))
    for intent_id in EXT_IDS:
        intent = V2[intent_id]
        assert intent["split"] == "unseen_capability" and intent["notes"] and intent["label_rule"]
        refs = re.findall(r"docs/RAPP_USE_CASES\.md#(E\d\d)", intent["provenance"])
        assert refs and set(refs) <= anchors, (intent_id, refs)
        for chain in [intent["expected_workflow"], *intent["accepted_workflows"]]:
            assert any(step.startswith("RAPP.") or step.lower() in L2_MONITOR_IDS for step in chain), intent_id
        # operator wording: no application id or card name in the sentence
        text = intent["intent"].lower()
        for card in REGISTRY.values():
            if card.app_type == "rapp":
                assert card.name.lower() not in text, (intent_id, card.name)


def test_original_80_intents_unchanged_except_label_rule():
    # The committed file (before or after the extension is committed) starts with the same 80 intents.
    try:
        head = subprocess.run(["git", "show", "HEAD:./evaluation/intents_v2.json"], cwd=ROOT, capture_output=True, text=True, check=False)
    except FileNotFoundError:  # pragma: no cover - git missing
        pytest.skip("git not available")
    if head.returncode != 0:
        pytest.skip("no committed intents_v2.json")
    before = [{k: v for k, v in item.items() if k != "label_rule"} for item in json.loads(head.stdout)][:80]
    now = [{k: v for k, v in item.items() if k != "label_rule"} for item in V2.values()][:80]
    assert [i["id"] for i in now] == [i["id"] for i in before]
    assert json.dumps(now) == json.dumps(before)


def test_extension_labels_exclude_their_distractors():
    # declared conflicts named in the intent
    assert not _ok("border_shift_keep_mro", "KPM->RAPP.MOBILITY_LOAD_BALANCING->RAPP.MOBILITY_OPTIMIZATION")
    assert not _ok("fair_boost_vs_night_saving", "KPM->RAPP.SPECIAL_EVENTS->RAPP.ENERGY_SAVING")
    # neighbouring families that do a different job
    assert not _ok("evening_cell_border_shift", "KPM->RAPP.TRAFFIC_STEERING->RC")
    assert not _ok("highrise_beam_coverage", "KPM->RAPP.RET_TILT->RC")
    assert not _ok("midday_antenna_muting", "KPM->RAPP.ENERGY_SAVING->RC")
    assert not _ok("station_load_outlook", "KPM->RAPP.CAPACITY_MGMT")
    assert not _ok("pci_clash_fix", "KPM->RAPP.INTERFERENCE->RC")
    assert not _ok("rural_uplink_noise", "KPM->RAPP.INTERFERENCE->RC")
    assert not _ok("tenant_session_cap", "KPM->RAPP.SLICE_SLA->SLICE->RC")
    assert not _ok("far_neighbour_blocklist", "KPM->RAPP.MOBILITY_OPTIMIZATION->RC")
    assert not _ok("ue_link_quality_snapshot", "KPM")
    # order, dependency, lifecycle
    assert not _ok("forecast_antenna_muting", "KPM->RAPP.MIMO_SLEEP->RAPP.TRAFFIC_FORECAST")
    assert not _ok("silent_cell_compensation", "KPM->RAPP.SLEEPING_CELL->RAPP.SELF_HEALING->RC")
    assert not _ok("new_small_cells_neighbours", "KPM->RAPP.ANR.V0")
    assert not _ok("new_small_cells_neighbours", "KPM->RAPP.ANR.NORTHWIND")  # variant not labelled here
    # allowed extras: read-only observation / analytics, optional validation
    assert _ok("golden_config_drift", "KPM->RAPP.CONFIG_AUDIT")
    assert _ok("ue_link_quality_snapshot", "KPM->MAC")
    assert _ok("meter_reconnect_storm", "KPM->RAPP.SIGNALLING_STORM")
    assert _ok("beam_then_link_check", "KPM->RAPP.BEAMFORMING->MAC->RC")
    assert _ok("pci_then_neighbour_refresh", "KPM->RAPP.ANR->RAPP.PCI_OPTIMIZATION")  # two writers, no declared order


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
