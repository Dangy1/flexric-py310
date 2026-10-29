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
    assert harness.METHODS[-2:] == ["appweaver_guided", "appweaver_v2"]
    assert harness.LEARNING_METHODS["appweaver_guided"] == {"workflow_templates": False, "memory": False, "guidance": True, "feedback": True}
    assert harness.LEARNING_METHODS["appweaver_v2"] == {"workflow_templates": True, "memory": True, "guidance": True, "feedback": True}
    hashes = harness.prompt_builders_sha256()
    for key in ("learning_prompts.guidance_section", "learning_prompts.feedback_prompt", "compose.feedback_findings"):
        assert key in hashes, key
    # AppWeaver's own prompt builders are unchanged by the fixes
    assert hashes["prompts.compose_prompt"] == "9b781c4f44b6731f"
    info = harness.learning_manifest(["appweaver_guided", "appweaver_v2"])
    assert info["methods"]["appweaver_guided"]["guidance"] is True and info["methods"]["appweaver_v2"]["feedback"] is True
    assert info["guidance_section_sha256"]
