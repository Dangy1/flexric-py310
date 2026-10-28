"""Offline tests for the AppWeaver learning variants (workstream F).

appweaver_tpl = AppWeaver + operator workflow-template cards;
appweaver_mem = appweaver_tpl + experience memory (evaluation/memory/experience_A.jsonl, Batch A only).

Run:  conda activate flexric-py310 && cd examples/xApp/python3 && PYTHONPATH=. python -m pytest -q evaluation/tests
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import pytest  # noqa: E402

# Fakes, env isolation (portal DB/log dir) and the harness fixtures come from the AppWeaver graph tests.
from test_appweaver_graph import FakeWorld, harness, seeded_harness, small_registry  # noqa: E402,F401

from backend.appweaver import AppWeaverConfig, build_graph, run_appweaver  # noqa: E402
from backend.appweaver.learning import (  # noqa: E402
    ExperienceMemory, default_workflow_cards, normalize_sentence, retrieve_workflow_cards, workflow_cards,
)
from backend.appweaver.learning_prompts import memory_section, template_section  # noqa: E402
from backend.appweaver.prompts import compose_prompt, serialize_cards  # noqa: E402
from backend.orchestration.config import WORKFLOW_ACTIONS, WORKFLOW_TEMPLATES  # noqa: E402
from evaluation import build_experience_memory as bem  # noqa: E402

ROOT = HERE.parents[1]
EVAL = ROOT / "evaluation"
MEMORY = EVAL / "memory" / "experience_A.jsonl"
INTENT_FILES = {name: json.loads((EVAL / f"{name}.json").read_text(encoding="utf-8")) for name in ("intents_50", "intents_v2", "intents_c")}
TPL = AppWeaverConfig(variant="appweaver_tpl", workflow_templates=True)


def mem_cfg(path: Path) -> AppWeaverConfig:
    return AppWeaverConfig(variant="appweaver_mem", workflow_templates=True, memory_path=str(path))


def write_memory(path: Path, entries: List[Dict[str, Any]]) -> Path:
    path.write_text(bem.dumps_entries(entries), encoding="utf-8")
    return path


def toy_entries() -> List[Dict[str, Any]]:
    return [
        {"id": "m_backhaul", "intent": "Reduce queueing delay on the backhaul.", "accepted_workflows": [["KPM", "TC", "RC"]],
         "rejected": [{"workflow": ["TC", "KPM"], "reasons": ["order: KPM must precede TC"], "count": 2}], "provenance": {"run": "toy"}},
        {"id": "m_energy", "intent": "Save energy at night on idle cells.", "accepted_workflows": [["KPM", "RAPP.ENERGY_SAVING", "RC"]],
         "rejected": [], "provenance": {"run": "toy"}},
        {"id": "m_slice", "intent": "Validate slice isolation after a policy update.", "accepted_workflows": [["SLICE", "KPM", "RC"]],
         "rejected": [], "provenance": {"run": "toy"}},
    ]


# --------------------------------------------------------------------------- workflow-template cards

def test_template_cards_come_from_the_operator_config(harness):
    cards = default_workflow_cards(harness.AGENTS)
    assert [c["workflow_id"] for c in cards] == list(WORKFLOW_TEMPLATES)
    for card in cards:
        template = WORKFLOW_TEMPLATES[card["workflow_id"]]
        assert card["name"] == template["label"] and card["description"] == template["description"]
        # the same executable chain (and actions) the rule router deploys and llm_only is shown
        assert card["generated_workflow"] == harness.normalize_action_chain(card["workflow_id"])
        assert [(s["agent_id"], s["action_id"]) for s in card["steps"]] == harness.actions_for_workflow(card["workflow_id"])
        assert set(card) == {"workflow_id", "name", "description", "generated_workflow", "steps"}
    # an action the registry card no longer has is dropped (Compose resolves the default)
    registry = small_registry()
    registry["rc"].actions = registry["rc"].actions[1:]
    rc_step = [s for s in workflow_cards(WORKFLOW_TEMPLATES, WORKFLOW_ACTIONS, registry)[0]["steps"] if s["agent_id"] == "rc"][0]
    assert rc_step == {"agent_id": "rc"}


def test_template_retrieval_ranks_whole_catalog():
    cards = default_workflow_cards(small_registry())
    got, report = retrieve_workflow_cards(cards, "Mitigate transport bufferbloat on the backhaul tunnel.")
    assert [c["workflow_id"] for c in got][0] == "transport-qos"
    assert len(got) == 3 and report["retrieved"] == [c["workflow_id"] for c in got]
    got, _ = retrieve_workflow_cards(cards, "Monitor the slice policy, measure its impact and review control readiness.")
    assert got[0]["workflow_id"] == "slice-assurance"
    got, report = retrieve_workflow_cards(cards, "zzz qqq", k=2)
    assert [c["workflow_id"] for c in got] == list(WORKFLOW_TEMPLATES)[:2]  # ties: catalog order
    got, _ = retrieve_workflow_cards(cards, "zzz qqq", min_score=0.0)
    assert got == []


def test_template_cards_retrieved_and_rendered_in_graph():
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"])
    final = run_appweaver("Mitigate transport bufferbloat on the backhaul.", world.deps(), TPL)
    assert final["status"] == "completed" and final["graph_variant"] == "appweaver_tpl"
    assert final["template_retrieval"]["retrieved"][0] == "transport-qos"
    prompt = world.prompts[0]
    assert "Operator workflow templates: reuse one unchanged" in prompt and "\nWorkflow templates: [" in prompt
    rendered = json.loads(prompt.split("\nWorkflow templates: ", 1)[1].split("\n", 1)[0])
    assert [c["workflow_id"] for c in rendered] == final["template_retrieval"]["retrieved"]
    assert rendered[0]["generated_workflow"] == ["TC"] and rendered[0]["steps"] == [{"agent_id": "tc", "action_id": "apply-codel"}]
    discover = [e for e in final["events"] if e["node"] == "discover"][0]
    assert discover["templates"] == final["template_retrieval"]["retrieved"]
    assert final["prompts"][0]["workflow_cards"] == final["template_retrieval"]["retrieved"]


def test_tpl_differs_from_appweaver_only_by_templates():
    base = AppWeaverConfig()
    assert {k for k in vars(base) if getattr(base, k) != getattr(TPL, k)} == {"variant", "workflow_templates"}
    registry = small_registry()
    w = FakeWorld(registry, ["KPM"])
    assert set(build_graph(w.deps(), base).get_graph().nodes) == set(build_graph(w.deps(), TPL).get_graph().nodes)

    intent = "Reduce queueing delay on the backhaul."
    w_base, w_tpl = FakeWorld(registry, ["KPM", "TC", "RC"]), FakeWorld(registry, ["KPM", "TC", "RC"])
    f_base = run_appweaver(intent, w_base.deps(), base)
    f_tpl = run_appweaver(intent, w_tpl.deps(), TPL)
    # The Compose prompt is AppWeaver's, byte for byte, plus the template section; nothing else changes.
    p_base, p_tpl = w_base.prompts[0], w_tpl.prompts[0]
    assert p_base == compose_prompt(intent, serialize_cards([c for c in registry.values() if c.actions]))
    assert p_tpl.startswith(p_base)
    templates, _ = retrieve_workflow_cards(default_workflow_cards(registry), intent)
    assert p_tpl[len(p_base):] == template_section(templates)
    assert "Past intents" not in p_tpl
    for key in ("generated_workflow", "steps", "compat_report", "status", "tool_calls", "card_ids"):
        assert f_base[key] == f_tpl[key], key
    strip = lambda report: {k: v for k, v in report.items() if k != "latency_ms"}  # noqa: E731
    assert strip(f_base["validation_report"]) == strip(f_tpl["validation_report"])
    assert [(e["node"], e["kind"]) for e in f_base["events"]] == [(e["node"], e["kind"]) for e in f_tpl["events"]]
    assert "template_retrieval" not in f_base and "memory_retrieval" not in f_tpl


def test_tpl_reused_template_keeps_its_actions(harness):
    registry = small_registry()
    world = FakeWorld(registry, ["SLICE", "KPM", "RC"])
    card = next(c for c in default_workflow_cards(registry) if c["workflow_id"] == "slice-assurance")
    world.planner = lambda prompt: (world.prompts.append(prompt) or {"status": "completed", "response": json.dumps(
        {"generated_workflow": card["generated_workflow"], "steps": card["steps"], "rationale": "reuse slice-assurance"})})
    final = run_appweaver("Validate slice isolation after a policy update.", world.deps(), TPL)
    assert final["generated_workflow"] == ["SLICE", "KPM", "RC"] and final["status"] == "completed"
    assert [(s["agent_id"], s["action_id"]) for s in final["steps"]] == [(s["agent_id"], s["action_id"]) for s in card["steps"]]
    assert harness.workflow_id_from_chain(final["generated_workflow"]) == "slice-assurance"


# --------------------------------------------------------------------------- experience memory

def test_memory_retrieval_excludes_identical_sentences(tmp_path):
    memory = ExperienceMemory.load(write_memory(tmp_path / "m.jsonl", toy_entries()), min_score=0.0)
    entries, report = memory.retrieve("Reduce queueing delay on the backhaul.")
    assert "m_backhaul" not in [e["id"] for e in entries]
    assert report["excluded_identical"] == ["m_backhaul"]
    # case, whitespace and the final full stop do not defeat the guard
    _, report = memory.retrieve("  REDUCE queueing   delay on the backhaul ")
    assert report["excluded_identical"] == ["m_backhaul"]
    entries, report = memory.retrieve("Reduce the queueing delay on the transport backhaul links.")
    assert entries[0]["id"] == "m_backhaul" and report["excluded_identical"] == []
    assert report["memory_retrieved"][0] == {"id": "m_backhaul", "score": entries[0]["score"]}
    assert report["sha256"] == hashlib.sha256((tmp_path / "m.jsonl").read_bytes()).hexdigest() and report["entry_count"] == 3
    # floor and k
    floor_mem = ExperienceMemory.load(tmp_path / "m.jsonl", min_score=1e9)
    assert floor_mem.retrieve("Reduce the queueing delay on the backhaul links.")[0] == []
    assert len(ExperienceMemory.load(tmp_path / "m.jsonl", min_score=0.0, k=1).retrieve("slice energy backhaul delay")[0]) == 1


def test_memory_rejects_annotation_fields(tmp_path):
    bad = toy_entries()
    bad[0]["notes"] = "Closed-loop latency reduction"
    with pytest.raises(ValueError):
        ExperienceMemory.load(write_memory(tmp_path / "bad.jsonl", bad))
    bad = toy_entries()
    bad[0]["rejected"][0]["category"] = "latency"
    with pytest.raises(ValueError):
        ExperienceMemory.load(write_memory(tmp_path / "bad2.jsonl", bad))


def test_memory_rendered_without_ids_or_provenance(tmp_path):
    memory = ExperienceMemory.load(write_memory(tmp_path / "m.jsonl", toy_entries()), min_score=0.0)
    entries, _ = memory.retrieve("Reduce the queueing delay on the transport backhaul links.")
    section = memory_section(entries)
    assert section.startswith("Operator experience: similar past intents and the workflow the operator accepted; and proposals the")
    rendered = json.loads(section.split("Past intents: ", 1)[1])
    assert set(rendered[0]) == {"past_intent", "accepted_workflows", "rejected_proposals"}
    assert rendered[0]["rejected_proposals"] == [{"workflow": ["TC", "KPM"], "reason": ["order: KPM must precede TC"]}]
    assert "m_backhaul" not in section and "toy" not in section and "score" not in section


def _synthetic_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    manifest = {"registry": {"agent_ids": ["kpm", "slice", "tc", "rc", "orchestrator"]}, "evaluation_runtime_config": {"rapp_directory_enabled": False}}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    recs = []
    chains = [["KPM", "TC", "RC"], ["KPM", "TC", "RC"], ["TC", "KPM", "SLICE"], [], ["KPM", "SLICE", "TC", "RC"], ["SLICE", "TC"]]
    for i, chain in enumerate(chains):
        recs.append({"method": "langgraph_agentcard", "intent_id": "xr_latency_guard", "repeat_index": i + 1, "record_id": f"r{i}",
                     "generated_workflow": chain})
    # a record that already carries the rule verdict (final batches) is used as is
    recs.append({"method": "langgraph_agentcard", "intent_id": "xr_latency_guard", "repeat_index": 9, "record_id": "r9",
                 "generated_workflow": ["RC"], "workflow_match_rule": False, "workflow_rule_reasons": ["missing required KPM"]})
    recs.append({"method": "llm_only", "intent_id": "xr_latency_guard", "repeat_index": 1, "record_id": "x", "generated_workflow": ["GHOST"]})
    (run / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
    return run


def test_memory_builder_deterministic_and_label_free(tmp_path):
    run = _synthetic_run(tmp_path)
    intents_path = tmp_path / "intents.json"
    intents = [i for i in INTENT_FILES["intents_50"] if i["id"] in {"xr_latency_guard", "congestion_relief"}]
    intents_path.write_text(json.dumps(intents), encoding="utf-8")
    outs = []
    for name in ("a.jsonl", "b.jsonl"):
        assert bem.main(["--run", str(run), "--intents", str(intents_path), "--out", str(tmp_path / name)]) == 0
        outs.append((tmp_path / name).read_bytes())
    assert outs[0] == outs[1]
    entries = [json.loads(line) for line in outs[0].decode().splitlines()]
    assert [e["id"] for e in entries] == ["xr_latency_guard", "congestion_relief"]
    xr = entries[0]
    assert xr["accepted_workflows"] == [["KPM", "SLICE", "TC", "RC"]]
    # most frequent rejected chain first, at most 2, rule reasons attached; empty plan and correct chain skipped
    assert [r["workflow"] for r in xr["rejected"]] == [["KPM", "TC", "RC"], ["RC"]]
    assert xr["rejected"][0] == {"workflow": ["KPM", "TC", "RC"], "reasons": ["missing required SLICE"], "count": 2}
    assert xr["rejected"][1]["reasons"] == ["missing required KPM"]
    assert xr["provenance"]["proposals"] == 6 and xr["provenance"]["rejected_distinct"] == 4
    assert entries[1]["rejected"] == [] and entries[1]["provenance"]["proposals"] == 0
    text = outs[0].decode()
    for intent in intents:
        assert intent["notes"] not in text
    assert '"notes"' not in text and '"category"' not in text and '"label_rule"' not in text


def _memory_source_run() -> Path:
    runs = {json.loads(line)["provenance"]["run"] for line in MEMORY.read_text(encoding="utf-8").splitlines() if line.strip()}
    assert len(runs) == 1, runs
    name = runs.pop()
    for root in (EVAL / "runs", Path.home() / "flexric" / "build" / "examples" / "xApp" / "python3" / "evaluation" / "runs"):
        if (root / name / "records.jsonl").exists():
            return root / name
    pytest.skip(f"source run {name} of the committed memory not present")


def test_committed_memory_rebuilds_from_its_batch_a_run(tmp_path):
    """The committed memory is exactly the builder's output for the Batch A run named in its provenance."""
    out = tmp_path / "experience_A.jsonl"
    assert bem.main(["--run", str(_memory_source_run()), "--intents", str(EVAL / "intents_50.json"), "--out", str(out)]) == 0
    assert out.read_bytes() == MEMORY.read_bytes()


def test_memory_is_batch_a_only_and_disjoint_from_batch_c():
    memory = ExperienceMemory.load(MEMORY)
    a = {normalize_sentence(i["intent"]) for i in INTENT_FILES["intents_50"]}
    assert {normalize_sentence(e["intent"]) for e in memory.entries} <= a
    assert len(memory.entries) == len(INTENT_FILES["intents_50"])
    c_sentences = {normalize_sentence(i["intent"]) for i in INTENT_FILES["intents_c"]}
    assert len(c_sentences) == len(INTENT_FILES["intents_c"]) == 60
    in_memory = {normalize_sentence(e["intent"]) for e in memory.entries}
    assert not (c_sentences & in_memory), "a Batch C intent sentence is in the experience memory"
    assert not ({i["id"] for i in INTENT_FILES["intents_c"]} & {e["id"] for e in memory.entries})
    # no Batch C sentence is retrieved-and-excluded either (would mean it is in memory)
    for intent in INTENT_FILES["intents_c"]:
        assert memory.retrieve(intent["intent"])[1]["excluded_identical"] == []
    # no annotation of any benchmark intent (A, v2, C) is in the memory
    text = MEMORY.read_text(encoding="utf-8")
    for intents in INTENT_FILES.values():
        for intent in intents:
            for key in ("notes", "source"):
                value = str(intent.get(key) or "").strip()
                assert not (len(value) >= 12 and value in text), (intent["id"], key)


def test_memory_in_graph_end_to_end(tmp_path):
    path = write_memory(tmp_path / "m.jsonl", toy_entries())
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"])
    cfg = mem_cfg(path)
    cfg.memory_min_score = 0.0
    final = run_appweaver("Reduce queueing delay on the backhaul.", world.deps(), cfg)
    assert final["status"] == "completed" and final["graph_variant"] == "appweaver_mem"
    report = final["memory_retrieval"]
    assert report["excluded_identical"] == ["m_backhaul"]
    assert "m_backhaul" not in [r["id"] for r in report["memory_retrieved"]]
    prompt = world.prompts[0]
    assert "Operator workflow templates" in prompt and "Operator experience" in prompt
    assert "Reduce queueing delay on the backhaul." not in prompt.split("Past intents: ", 1)[1]
    discover = [e for e in final["events"] if e["node"] == "discover"][0]
    assert discover["memory_excluded_identical"] == ["m_backhaul"]
    assert final["prompts"][0]["memory_entries"] == [r["id"] for r in report["memory_retrieved"]]
    # tpl -> mem differ only by the memory path; the prompt is the tpl prompt plus the memory section
    assert {k for k in vars(TPL) if getattr(TPL, k) != getattr(mem_cfg(path), k)} == {"variant", "memory_path"}
    w_tpl = FakeWorld(small_registry(), ["KPM", "TC", "RC"])
    run_appweaver("Reduce queueing delay on the backhaul.", w_tpl.deps(), TPL)
    assert prompt.startswith(w_tpl.prompts[0]) and prompt[len(w_tpl.prompts[0]):].startswith("Operator experience")


# --------------------------------------------------------------------------- harness

def _label_free(harness, intent: Dict[str, Any], prompt: str) -> None:
    notes = str(intent.get("notes") or "").strip()
    assert notes and notes not in prompt
    assert "Notes:" not in prompt and "Category:" not in prompt
    assert '"notes":' not in prompt and '"category":' not in prompt and '"label_rule":' not in prompt
    harness._RECORD_STATE["notes"] = notes
    try:
        harness.assert_prompt_label_free(prompt)
    finally:
        harness._RECORD_STATE["notes"] = ""


@pytest.mark.parametrize("name", list(INTENT_FILES))
def test_no_prompt_contains_notes_or_category_learning(harness, monkeypatch, name):
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "memory_path", str(MEMORY))
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "retrieval_k", 0)
    memory = harness.experience_memory()
    for intent in INTENT_FILES[name]:
        base = harness.agentcard_prompt(intent)
        tpl = harness.appweaver_tpl_prompt(intent)
        mem = harness.appweaver_mem_prompt(intent)
        assert tpl.startswith(base) and mem.startswith(tpl)
        for prompt in (base, tpl, mem):
            _label_free(harness, intent, prompt)
        # the intent's own memory entry (Batch A) is never shown back to it
        if name != "intents_c":
            past = mem.split("Past intents: ", 1)[1] if "Past intents: " in mem else "[]"
            assert intent["intent"].strip() not in [p["past_intent"] for p in json.loads(past)]
        _, report = memory.retrieve(str(intent["intent"]))
        if name == "intents_c":
            assert report["excluded_identical"] == []
    harness._RECORD_STATE["notes"] = "Closed-loop latency reduction"
    with pytest.raises(AssertionError):
        harness.assert_prompt_label_free('Past intents: [{"past_intent": "x", "notes": "y"}]\n')
    harness._RECORD_STATE["notes"] = ""


def test_methods_labels_manifest_and_prompt_hashes(harness, monkeypatch):
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "memory_path", str(MEMORY))
    methods = harness.METHODS
    assert methods.index("appweaver_tpl") == methods.index("langgraph_agentcard") + 1 and methods[-1] == "appweaver_mem"
    assert harness.METHOD_LABELS["appweaver_tpl"] == "AppWeaver + templates"
    assert harness.METHOD_LABELS["appweaver_mem"] == "AppWeaver + templates + memory"
    hashes = harness.prompt_builders_sha256()
    # AppWeaver's own prompt builders are byte-identical to the Batch A final run (manifest of
    # 20261028T084337_250177Z_A_final_gptoss120b_spark1): the variants only add sections.
    assert hashes["prompts.compose_prompt"] == "9b781c4f44b6731f"
    assert hashes["prompts.recovery_prompt"] == "9680297280ea2b9e"
    assert hashes["prompts.serialize_cards"] == "1a7602bc064a8e2a"
    assert hashes["appweaver.prompts_module"] == "1fa95ef855ea4bbe"
    assert hashes["run_harness.agentcard_prompt"] == "0b60c1c295d6f6cd"
    for key in ("run_harness.appweaver_tpl_prompt", "run_harness.appweaver_mem_prompt", "learning_prompts.compose_prompt_with_context",
                "learning_prompts.template_section", "learning_prompts.memory_section", "learning.ExperienceMemory",
                "learning.retrieve_workflow_cards", "appweaver.learning_prompts_module", "appweaver.learning_module"):
        assert key in hashes, key
    info = harness.learning_manifest(["langgraph_agentcard", "appweaver_tpl", "appweaver_mem"])
    assert info["methods"]["appweaver_tpl"] == {"workflow_templates": True, "memory_path": None}
    assert info["methods"]["appweaver_mem"] == {"workflow_templates": True, "memory_path": str(MEMORY.resolve())}
    assert info["memory_sha256"] == hashlib.sha256(MEMORY.read_bytes()).hexdigest()
    assert info["memory_entry_count"] == 50 and [c["workflow_id"] for c in info["workflow_template_cards"]] == list(WORKFLOW_TEMPLATES)
    assert harness.learning_manifest(["langgraph_agentcard"])["memory_path"] is None


@pytest.mark.parametrize("method", ["appweaver_tpl", "appweaver_mem"])
def test_harness_record_end_to_end(seeded_harness, monkeypatch, method):
    h, portal = seeded_harness
    monkeypatch.setitem(h.EVAL_RUNTIME_CONFIG, "memory_path", str(MEMORY))
    portal.seeded = False
    intent = next(i for i in INTENT_FILES["intents_50"] if i["id"] == "latency_under_busy_tc")
    record = h.run_record(method, intent, 1, 45, True)
    assert record["method"] == method and record["graph_backend"] == "langgraph" and record["graph_variant"] == method
    assert record["generated_workflow"] == ["KPM", "SLICE", "TC", "RC"]
    assert record["conflict_detected_before_control"] is True and record["preempted_other_workflow"] is False
    assert record["workflow_templates_retrieved"] and set(record["workflow_templates_retrieved"]) == set(WORKFLOW_TEMPLATES)
    art = record["execution_artifacts"]
    assert art["workflow_templates_enabled"] is True
    # the graph's Compose prompt is exactly what the hashed harness builder produces
    builder = h.appweaver_mem_prompt if method == "appweaver_mem" else h.appweaver_tpl_prompt
    assert art["planner_task"]["prompt"] == builder(intent)
    if method == "appweaver_mem":
        assert record["memory_excluded_identical"] == ["latency_under_busy_tc"]  # own Batch A entry never shown
        assert record["memory_retrieved"] and all(set(r) == {"id", "score"} for r in record["memory_retrieved"])
        assert "latency_under_busy_tc" not in [r["id"] for r in record["memory_retrieved"]]
        assert art["memory_retrieval"]["sha256"] == hashlib.sha256(MEMORY.read_bytes()).hexdigest()
    else:
        assert record["memory_retrieved"] is None and art["memory_path"] is None
    assert "Notes:" not in json.dumps(art.get("planner_task"))


def test_figures_know_the_variants():
    sys.path.insert(0, str(EVAL / "paper_results"))
    import make_paper_figures as mpf  # noqa: E402

    ids = [m for m, _ in mpf.METHODS]
    assert ids[ids.index("langgraph_agentcard") + 1:] == ["appweaver_tpl", "appweaver_mem"]


def test_harness_cli_guards_for_learning_methods(harness, tmp_path, monkeypatch):
    monkeypatch.setattr(harness.flexric_agent_portal, "MAX_PROMPT_CHARS", harness.flexric_agent_portal.MAX_PROMPT_CHARS)
    monkeypatch.setattr(harness, "EVAL_RUNTIME_CONFIG", dict(harness.EVAL_RUNTIME_CONFIG))
    base = ["--intents", str(EVAL / "intents_c.json"), "--output-root", str(tmp_path / "runs"), "--repeat", "1"]
    # appweaver_mem prompts exceed the portal's 8000-character UI guard: refuse to start without lifting it
    with pytest.raises(SystemExit, match="max-prompt-chars"):
        harness.main(base + ["--methods", "langgraph_agentcard", "appweaver_tpl", "appweaver_mem"])
    with pytest.raises(SystemExit, match="experience memory"):
        harness.main(base + ["--methods", "appweaver_mem", "--max-prompt-chars", "20000", "--memory-path", str(tmp_path / "missing.jsonl")])
    assert not any((tmp_path / "runs").glob("*/records.jsonl"))
