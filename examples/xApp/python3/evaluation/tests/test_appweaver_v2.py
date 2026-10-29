"""Offline tests for the AppWeaver fixes from the failure analysis (docs/APPWEAVER_FAILURE_ANALYSIS.md).

appweaver_guided = AppWeaver + planning guidance + one feedback re-plan;
appweaver_v2     = appweaver_guided + workflow-template cards + experience memory.

Run:  conda activate flexric-py310 && cd examples/xApp/python3 && PYTHONPATH=. python -m pytest -q evaluation/tests
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import pytest  # noqa: E402

from test_appweaver_graph import FakeWorld, harness, make_card, small_registry  # noqa: E402,F401

from backend.appweaver import AppWeaverConfig, run_appweaver  # noqa: E402
from backend.appweaver.learning_prompts import FEEDBACK_HEADER, GUIDANCE_SECTION, compose_prompt_with_context  # noqa: E402
from backend.appweaver.needs import coverage_findings, needs_prompt, parse_needs, write_targets  # noqa: E402
from backend.appweaver.nodes.compose import feedback_findings  # noqa: E402
from backend.appweaver.prompts import compose_prompt, serialize_cards  # noqa: E402

GUIDED = AppWeaverConfig(variant="appweaver_guided", guidance=True, feedback=True)
INTENT = "Reduce queueing delay on the backhaul."


class SeqWorld(FakeWorld):
    """FakeWorld whose Compose planner returns the given chains in turn (last one repeats)."""

    def __init__(self, registry, chains: List[List[str]], **kw):
        super().__init__(registry, chains[0], **kw)
        self.chains = list(chains)
        self.compose_calls = 0

    def planner(self, prompt: str) -> Dict[str, Any]:
        if "Recover step" in prompt:
            return super().planner(prompt)
        self.prompts.append(prompt)
        chain = self.chains[min(self.compose_calls, len(self.chains) - 1)]
        self.compose_calls += 1
        return {"status": "completed", "response": json.dumps({"generated_workflow": chain, "steps": [], "rationale": "t"}), "prompt": prompt}


def conflict_registry():
    registry = small_registry()
    card = make_card("rapp.transport_qos", app_type="rapp", requires=["kpi_monitoring"], scopes=[("transport", "write", "tc_control")])
    registry[card.id] = card
    return registry


def test_guidance_text_names_no_intent_or_label():
    """The guidance is general: no intent id, chain or label of any benchmark intent appears in it."""
    root = HERE.parents[0]
    for name in ("intents_50", "intents_v2", "intents_c"):
        for intent in json.loads((root / f"{name}.json").read_text(encoding="utf-8")):
            assert intent["id"] not in GUIDANCE_SECTION
            assert intent["intent"] not in GUIDANCE_SECTION
    for app in ("KPM", "SLICE", "TC", "RC", "RAPP."):
        assert app not in GUIDANCE_SECTION


def test_guided_prompt_is_appweaver_prompt_plus_guidance():
    registry = small_registry()
    world = SeqWorld(registry, [["KPM", "TC", "RC"]])
    final = run_appweaver(INTENT, world.deps(), GUIDED)
    assert final["status"] == "completed" and final["graph_variant"] == "appweaver_guided"
    base = compose_prompt(INTENT, serialize_cards([c for c in registry.values() if c.actions]))
    assert world.prompts[0] == base + GUIDANCE_SECTION
    assert world.compose_calls == 1 and "feedback" not in final  # clean plan: no re-plan


def test_default_appweaver_prompt_unchanged():
    registry = small_registry()
    world = SeqWorld(registry, [["KPM", "TC", "RC"]])
    run_appweaver(INTENT, world.deps(), AppWeaverConfig())
    assert GUIDANCE_SECTION not in world.prompts[0]
    assert world.prompts[0] == compose_prompt(INTENT, serialize_cards([c for c in registry.values() if c.actions]))
    assert compose_prompt_with_context(INTENT, [], None, None) == compose_prompt(INTENT, [])


def test_feedback_replans_a_direct_write_conflict():
    world = SeqWorld(conflict_registry(), [["KPM", "RAPP.TRANSPORT_QOS", "TC"], ["KPM", "TC", "RC"]])
    final = run_appweaver(INTENT, world.deps(), GUIDED)
    assert world.compose_calls == 2
    fb = final["feedback"]
    assert fb["adopted"] is True and fb["first_chain"] == ["KPM", "RAPP.TRANSPORT_QOS", "TC"]
    assert any("Second writer on 'tc_control'" in f for f in fb["findings"])
    assert final["generated_workflow"] == ["KPM", "TC", "RC"] == fb["revised_chain"]
    assert FEEDBACK_HEADER in world.prompts[1] and world.prompts[1].startswith(world.prompts[0])
    assert final["feedback_planner_task"]["status"] == "completed"
    assert [p["node"] for p in final["prompts"]] == ["compose", "compose_feedback"]


def test_feedback_keeps_first_plan_when_revision_is_not_better():
    chain = ["KPM", "RAPP.TRANSPORT_QOS", "TC"]
    world = SeqWorld(conflict_registry(), [chain, chain])
    final = run_appweaver(INTENT, world.deps(), GUIDED)
    assert world.compose_calls == 2 and final["feedback"]["adopted"] is False
    assert final["generated_workflow"] == chain


def test_feedback_is_bounded_to_one_replan_and_off_by_default():
    chain = ["KPM", "RAPP.TRANSPORT_QOS", "TC"]
    world = SeqWorld(conflict_registry(), [chain])
    run_appweaver(INTENT, world.deps(), AppWeaverConfig())
    assert world.compose_calls == 1
    world = SeqWorld(conflict_registry(), [chain, chain, chain])
    run_appweaver(INTENT, world.deps(), GUIDED)
    assert world.compose_calls == 2


def test_feedback_on_empty_plan():
    world = SeqWorld(small_registry(), [[], ["KPM", "TC"]])
    final = run_appweaver(INTENT, world.deps(), GUIDED)
    assert final["feedback"]["adopted"] is True and final["generated_workflow"] == ["KPM", "TC"]
    assert final["status"] == "completed"


def test_feedback_findings_are_card_driven():
    assert feedback_findings({"findings": []}, []) and feedback_findings({"findings": []}, ["kpm"]) == []
    warn = {"check": "interface", "severity": "warning", "agent_id": "tc", "detail": "No shared interface"}
    second = {"check": "control_scope", "severity": "warning", "agent_id": "tc", "detail": "Second writer on 'tc_control' after step 1"}
    assert feedback_findings({"findings": [warn]}, ["kpm"]) == []
    assert feedback_findings({"findings": [warn, second]}, ["kpm"]) == ["TC: Second writer on 'tc_control' after step 1"]


def test_harness_knows_the_new_variants(harness):
    assert harness.METHODS[-3:] == ["appweaver_guided", "appweaver_v2", "appweaver_mem2"]
    assert harness.LEARNING_METHODS["appweaver_guided"] == {"workflow_templates": False, "memory": False, "guidance": True, "feedback": True, "needs": True}
    assert harness.LEARNING_METHODS["appweaver_v2"] == {"workflow_templates": True, "memory": True, "guidance": True, "feedback": True, "needs": True}
    hashes = harness.prompt_builders_sha256()
    for key in ("learning_prompts.guidance_section", "learning_prompts.feedback_prompt", "compose.feedback_findings",
                "needs.needs_prompt", "needs.coverage_findings", "appweaver.needs_module"):
        assert key in hashes, key
    # AppWeaver's own prompt builders are unchanged by the fixes
    assert hashes["prompts.compose_prompt"] == "9b781c4f44b6731f"
    info = harness.learning_manifest(["appweaver_guided", "appweaver_v2"])
    assert info["methods"]["appweaver_guided"]["guidance"] is True and info["methods"]["appweaver_v2"]["feedback"] is True
    assert info["methods"]["appweaver_guided"]["needs"] is True and info["methods"]["appweaver_v2"]["needs"] is True
    assert info["guidance_section_sha256"]


# --------------------------------------------------------------------------- needs-first

NEEDS = AppWeaverConfig(variant="appweaver_guided", guidance=True, feedback=True, needs=True)


class NeedsWorld(SeqWorld):
    """SeqWorld whose Needs step answers `needs` (a dict) and whose Compose answers the chains in turn."""

    def __init__(self, registry, needs, chains, **kw):
        super().__init__(registry, chains, **kw)
        self.needs_answer = needs
        self.needs_prompts: List[str] = []

    def planner(self, prompt: str) -> Dict[str, Any]:
        if "You are the Needs step" in prompt:
            self.needs_prompts.append(prompt)
            return {"status": "completed", "response": json.dumps(self.needs_answer), "prompt": prompt}
        return super().planner(prompt)


def test_write_targets_and_parse_needs_are_card_driven():
    registry = small_registry()
    targets = write_targets(registry.values())
    assert targets["transport"] == ["tc"] and targets["slice"] == ["slice"] and "cell" in targets
    parsed = parse_needs('noise {"observe": true, "control_targets": ["Transport", "warp_drive"], "rationale": "r"}', targets)
    assert parsed == {"observe": True, "control_targets": ["transport"], "unknown_targets": ["warp_drive"], "rationale": "r", "ok": True}
    assert parse_needs("no json here", targets)["ok"] is False


def test_needs_prompt_ignores_availability_and_lists_targets():
    prompt = needs_prompt("Protect latency while TC is busy.", {"transport": ["tc"], "slice": ["slice"]})
    assert "Ignore any statement about which applications are busy" in prompt
    assert '"transport": ["TC"]' in prompt and prompt.endswith("Intent: Protect latency while TC is busy.\n")


def test_coverage_findings_missing_extra_and_observation():
    registry = small_registry()
    needs = {"ok": True, "observe": True, "control_targets": ["transport"]}
    assert coverage_findings(registry, ["kpm", "tc"], needs) == []
    missing = coverage_findings(registry, ["kpm", "rc"], needs)
    assert any("No step writes control target 'transport'" in f for f in missing)
    assert any(f.startswith("RC: writes control target(s)") for f in missing)
    assert coverage_findings(registry, ["tc"], needs) == ["No observation step, although the needs analysis requires observation."]
    assert coverage_findings(registry, ["kpm", "rc"], {"ok": False}) == []


def test_needs_first_replans_a_dropped_busy_app():
    """F1: the planner drops TC (busy); the needs say transport; the feedback re-plan restores TC."""
    world = NeedsWorld(small_registry(), {"observe": True, "control_targets": ["transport"], "rationale": "queues"},
                       [["KPM", "RC"], ["KPM", "TC"]])
    final = run_appweaver("Protect latency while TC is already busy with another workflow.", world.deps(), NEEDS)
    assert len(world.needs_prompts) == 1 and world.compose_calls == 2
    assert final["needs"]["control_targets"] == ["transport"]
    assert "Needs analysis (a previous step decided" in world.prompts[0] and '["transport"]' in world.prompts[0]
    assert final["feedback"]["adopted"] is True and final["generated_workflow"] == ["KPM", "TC"]
    assert [p["node"] for p in final["prompts"]] == ["needs", "compose", "compose_feedback"]
    assert final["needs_planner_task"]["status"] == "completed"


def test_needs_failure_falls_back_to_guided_behaviour():
    world = NeedsWorld(small_registry(), "not json", [["KPM", "TC", "RC"]])
    world.needs_answer = None

    def planner(prompt):
        if "You are the Needs step" in prompt:
            return {"status": "completed", "response": "no json", "prompt": prompt}
        return SeqWorld.planner(world, prompt)
    world.planner = planner
    final = run_appweaver(INTENT, world.deps(), NEEDS)
    assert final["needs"]["ok"] is False and "Needs analysis" not in world.prompts[0]
    assert final["status"] == "completed" and world.compose_calls == 1


# --------------------------------------------------------------------------- two-planner memory

def test_mem2_uses_its_own_memory_file(harness):
    assert harness.LEARNING_METHODS["appweaver_mem2"] == {"workflow_templates": True, "memory": True, "memory_file": "experience_A_both.jsonl"}
    assert harness.memory_path_for_run("appweaver_mem2").name == "experience_A_both.jsonl"
    assert harness.memory_path_for_run("appweaver_mem").name == "experience_A.jsonl"
    assert harness.memory_path_for_run("appweaver_mem2").parent == harness.memory_path_for_run("appweaver_mem").parent


def test_builder_adds_planner_only_proposals(tmp_path):
    from evaluation import build_experience_memory as bem
    rows = [{"intent_id": "x", "chain": ["KPM", "TC"], "rule": False, "reasons": ["missing required SLICE"], "status": "completed"},
            {"intent_id": "y", "chain": [], "rule": False, "reasons": [], "status": "failed"}]
    path = tmp_path / "glm.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    records, label = bem.load_planner_only(f"{path}:GLM-5.3-Flash", "langgraph_agentcard")
    assert label == "GLM-5.3-Flash" and len(records) == 1  # failed planner calls are not proposals
    rec = records[0]
    assert rec["method"] == "langgraph_agentcard" and rec["generated_workflow"] == ["KPM", "TC"]
    assert rec["workflow_match_rule"] is False and rec["workflow_rule_reasons"] == ["missing required SLICE"]


def test_two_planner_memory_is_batch_a_only_and_disjoint_from_batch_c():
    from backend.appweaver.learning import ExperienceMemory, normalize_sentence
    root = HERE.parents[0]
    memory = ExperienceMemory.load(root / "memory" / "experience_A_both.jsonl")
    a = {normalize_sentence(i["intent"]) for i in json.loads((root / "intents_50.json").read_text(encoding="utf-8"))}
    c = json.loads((root / "intents_c.json").read_text(encoding="utf-8"))
    assert len(memory.entries) == 50 and {normalize_sentence(e["intent"]) for e in memory.entries} <= a
    assert not ({normalize_sentence(i["intent"]) for i in c} & a)
    for intent in c:
        assert memory.retrieve(intent["intent"])[1]["excluded_identical"] == []
    runs = {str((e.get("provenance") or {}).get("run")) for e in memory.entries}
    assert len(runs) == 1 and "GLM-5.3-Flash" in next(iter(runs)) and "gptoss120b" in next(iter(runs))
