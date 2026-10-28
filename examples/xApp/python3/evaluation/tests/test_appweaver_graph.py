"""Offline tests for the AppWeaver LangGraph method and the harness revision (workstream C).

Run:  conda activate flexric-py310 && cd examples/xApp/python3 && python -m pytest -q evaluation/tests
No RIC, xApp or LLM is needed: planner, launches and lease queries are fakes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Importing the harness imports the portal module: keep its sqlite DB and run logs out of the repo.
_TMP = Path(tempfile.mkdtemp(prefix="appweaver-tests-"))
os.environ.setdefault("FLEXRIC_AGENT_PORTAL_DB_PATH", str(_TMP / "portal.db"))
os.environ.setdefault("FLEXRIC_AGENT_PORTAL_LOG_DIR", str(_TMP / "runs"))
os.environ["FLEXRIC_RIC_LOG"] = str(_TMP / "nearRT-RIC.log")

import pytest  # noqa: E402

from backend.appweaver import AppWeaverConfig, AppWeaverDeps, build_graph, run_appweaver  # noqa: E402
from backend.common.models import AgentAction, AgentCard, ControlScope  # noqa: E402
from backend.orchestration.compat import check_chain, repair_chain  # noqa: E402
from backend.orchestration.discovery import discover_with_report, pinned_xapp_ids  # noqa: E402
from backend.orchestration.validate import live_e2_ran_functions, validate_chain  # noqa: E402

INTENTS = json.loads((ROOT / "evaluation" / "intents_50.json").read_text(encoding="utf-8"))
RIC_LOG = """[NEAR-RIC]: Loading SM ID = 2 with def = ORAN-E2SM-KPM
[E2AP]: E2 SETUP-REQUEST rx from PLMN 505. 1 Node ID 1 RAN type ngran_gNB
[NEAR-RIC]: Accepting RAN function ID 2 with def = ORAN-E2SM-KPM
[NEAR-RIC]: Accepting RAN function ID 3 with def = ORAN-E2SM-RC
[NEAR-RIC]: Accepting RAN function ID 143 with def = RLC_STATS_V0
[NEAR-RIC]: Accepting RAN function ID 145 with def = SLICE_STATS_V0
[NEAR-RIC]: Accepting RAN function ID 146 with def = TC_STATS_V0
"""
Path(os.environ["FLEXRIC_RIC_LOG"]).write_text(RIC_LOG, encoding="utf-8")


# --------------------------------------------------------------------------- fakes

def make_card(agent_id: str, *, app_type: str = "xapp", sm: str = "", caps=(), requires=(), consumes=(), produces=(),
              scopes=(("cell", "read", ""),), status: str = "ready", interfaces=(), actions=("run",), conflicts=()) -> AgentCard:
    return AgentCard(
        id=agent_id, name=agent_id.upper(), role="test", service_model=sm or ("Non-RT" if app_type == "rapp" else agent_id.upper()),
        description=f"{agent_id} test card", page_path="", a2a_card_path="", status=status, activity="", skills=[],
        measurements=[], use_cases=[], peers=[], providers=[],
        actions=[AgentAction(id=a, label=a, description=a, kind="test", command=["true"]) for a in actions], notes=[],
        app_type=app_type, ric="non-rt" if app_type == "rapp" else "near-rt", interfaces=list(interfaces),
        consumes=list(consumes), produces=list(produces),
        control_scopes=[ControlScope(target=t, mode=m, resource=r) for t, m, r in scopes],
        requires=list(requires), capabilities=list(caps), conflicts_with=list(conflicts),
    )


def small_registry() -> Dict[str, AgentCard]:
    cards = [
        make_card("kpm", caps=["kpi_monitoring"], produces=["RRU.PrbTotDl"], scopes=[("cell", "read", "kpm_subscription")],
                  interfaces=["E2SM-KPM v2.03"], actions=("observe-rru", "observe-ue")),
        make_card("slice", scopes=[("slice", "write", "slice_control")], actions=("monitor", "apply-static")),
        make_card("tc", scopes=[("transport", "write", "tc_control")], interfaces=["E2SM-TC (FlexRIC custom)"], actions=("apply-codel", "apply-all")),
        make_card("rc", scopes=[("cell", "write", "rc_control")], interfaces=["E2SM-RC v1.03"], actions=("rc-control", "rc-report")),
        make_card("rapp.root_cause", app_type="rapp", caps=["root_cause_analysis"], requires=["kpi_monitoring"], scopes=[("cell", "read", "")]),
        make_card("rapp.self_healing", app_type="rapp", caps=["self_healing"], requires=["root_cause_analysis"], scopes=[("cell", "write", "cell_config")]),
        make_card("rapp.energy_saving", app_type="rapp", caps=["energy_saving"], requires=["kpi_monitoring"], scopes=[("cell", "write", "cell_power")]),
        make_card("rapp.energy_saving.v0", app_type="rapp", caps=["energy_saving"], requires=["kpi_monitoring"], scopes=[("cell", "write", "cell_power")], status="deprecated"),
    ]
    return {card.id: card for card in cards}


class FakeWorld:
    """Planner + launcher + leases. `busy` maps agent_id -> (run_id, free_at)."""

    def __init__(self, registry, compose_chain, recovery: Optional[Dict[str, Any]] = None, busy=None):
        self.registry = registry
        self.compose_chain = compose_chain
        self.recovery = recovery or {"decision": "wait"}
        self.busy: Dict[str, Any] = dict(busy or {})
        self.prompts: List[str] = []
        self.invocations: List[tuple] = []
        self.waits: List[tuple] = []
        self.resets = 0
        self.now = 0.0

    def planner(self, prompt: str) -> Dict[str, Any]:
        self.prompts.append(prompt)
        if "Recover step" in prompt:
            return {"status": "completed", "response": json.dumps(self.recovery), "prompt": prompt}
        return {"status": "completed", "response": json.dumps({"generated_workflow": self.compose_chain, "steps": [], "rationale": "t"}), "prompt": prompt}

    def lease_query(self, agent_ids):
        return {a: ({"run_id": self.busy[a][0], "action_id": "seed"} if a in self.busy and self.busy[a][1] > self.now else None) for a in agent_ids}

    def wait_until_free(self, agent_ids, budget):
        self.waits.append((tuple(agent_ids), budget))
        latest = max([self.busy[a][1] for a in agent_ids if a in self.busy] + [self.now])
        waited = max(0.0, latest - self.now)
        if waited <= budget:
            self.now = latest
            return {"free": True, "waited_s": waited}
        self.now += budget
        return {"free": False, "waited_s": budget}

    def invoke(self, agent_id, action_id):
        self.invocations.append((agent_id, action_id))
        if agent_id in self.busy and self.busy[agent_id][1] > self.now:
            call = {"agent_id": agent_id, "action_id": action_id, "status": "conflict", "lease_refusal": True,
                    "detail": f"409: Agent {agent_id} already has an active action"}
            return {"tool_calls": [call], "run_payloads": [], "error": call["detail"], "lease_wait_s": 0.0, "refused": True}
        run_id = f"own-{agent_id}-{len(self.invocations)}"
        call = {"agent_id": agent_id, "action_id": action_id, "status": "success", "run_id": run_id, "detail": ""}
        return {"tool_calls": [call], "run_payloads": [{"id": run_id}], "error": None, "lease_wait_s": 0.0, "refused": False}

    def discover(self, text, exclude):
        cards = [c for c in self.registry.values() if c.actions and c.id not in set(exclude or [])]
        return cards, {"retrieved": [c.id for c in cards], "pinned": [], "excluded": list(exclude or [])}

    def deps(self) -> AppWeaverDeps:
        return AppWeaverDeps(
            registry=self.registry, discover=self.discover, planner=self.planner, invoke=self.invoke,
            lease_query=self.lease_query, wait_until_free=self.wait_until_free,
            resolve_action=lambda agent_id, text: None, e2_functions=live_e2_ran_functions,
        )


def nodes_of(final) -> List[str]:
    return [event["node"] for event in final["events"]]


# --------------------------------------------------------------------------- graph

def test_graph_runs_end_to_end_on_langgraph():
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"])
    final = run_appweaver("Reduce queueing delay on the backhaul.", world.deps(), AppWeaverConfig())
    assert final["graph_backend"] == "langgraph"
    assert final["status"] == "completed"
    assert final["generated_workflow"] == ["KPM", "TC", "RC"]
    assert [n for n in nodes_of(final) if n != "deploy"][:3] == ["discover", "compose", "validate"]
    assert nodes_of(final)[-1] == "finish"
    assert [inv[0] for inv in world.invocations] == ["kpm", "tc", "rc"]
    report = final["validation_report"]
    assert report["verdict"] == "deployable" and report["e2_conformance"]["available"] is True
    assert final["conflict_detected_before_control"] is False and world.resets == 0


def test_empty_plan_is_a_failed_record_without_fallback():
    world = FakeWorld(small_registry(), [])
    final = run_appweaver("Do something sensible.", world.deps(), AppWeaverConfig())
    assert final["status"] == "failed" and final["failure_reason"] == "empty_plan"
    assert world.invocations == []
    assert "validate" not in nodes_of(final)


def test_repair_inserts_missing_producers_to_fixpoint():
    registry = small_registry()
    chain, events, report = repair_chain(registry, ["rapp.self_healing", "rc"])
    assert report.ok
    assert chain == ["kpm", "rapp.root_cause", "rapp.self_healing", "rc"]
    assert [e["move"] for e in events] == ["insert_producer", "insert_producer"]
    assert check_chain(registry, chain).ok


def test_repair_reorders_late_producer_and_replaces_deprecated():
    registry = small_registry()
    chain, events, report = repair_chain(registry, ["rapp.energy_saving.v0", "kpm", "rc"])
    assert report.ok
    assert chain == ["kpm", "rapp.energy_saving", "rc"]
    moves = [e["move"] for e in events]
    assert "replace_deprecated" in moves and "reorder_producer" in moves


def test_repair_respects_exclusions_and_drops_unknown():
    registry = small_registry()
    chain, events, report = repair_chain(registry, ["ghost", "rapp.energy_saving", "rc"], exclude=["kpm"])
    assert "kpm" not in chain and "ghost" not in chain
    assert events[0]["move"] == "drop_unknown"
    assert any(e["move"] == "drop_unsatisfiable" for e in events)


def test_compose_repair_in_graph_and_no_repair_rejects_at_validate():
    registry = small_registry()
    world = FakeWorld(registry, ["RAPP.ENERGY_SAVING", "RC"])
    full = run_appweaver("Save energy at night.", world.deps(), AppWeaverConfig())
    assert full["generated_workflow"] == ["KPM", "RAPP.ENERGY_SAVING", "RC"]
    assert full["status"] == "completed"
    assert any(e["move"] == "insert_producer" for e in full["repair_events"])

    world2 = FakeWorld(registry, ["RAPP.ENERGY_SAVING", "RC"])
    ablation = run_appweaver("Save energy at night.", world2.deps(), AppWeaverConfig(variant="no_repair", repair=False, recover=False))
    assert ablation["generated_workflow"] == ["RAPP.ENERGY_SAVING", "RC"]
    assert ablation["repair_events"] == []
    assert ablation["status"] == "rejected" and world2.invocations == []


def test_no_repair_differs_only_in_repair_and_recover():
    full, ablation = AppWeaverConfig(), AppWeaverConfig(variant="no_repair", repair=False, recover=False)
    differing = {k for k in vars(full) if getattr(full, k) != getattr(ablation, k)}
    assert differing == {"variant", "repair", "recover"}
    world = FakeWorld(small_registry(), ["KPM"])
    nodes_full = set(build_graph(world.deps(), full).get_graph().nodes)
    nodes_abl = set(build_graph(world.deps(), ablation).get_graph().nodes)
    assert nodes_full - nodes_abl == {"recover"} and nodes_abl <= nodes_full
    # Without Recover a busy app goes straight to Deploy (the shared lease wait handles it there).
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"], busy={"tc": ("seed", 30.0)})
    final = run_appweaver("x", world.deps(), ablation)
    assert "recover" not in nodes_of(final)
    assert final["conflict_detected_before_control"] is True
    assert final["status"] == "queued" and final["partial_deployment"] is False


def test_recovery_waits_instead_of_resetting():
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"], recovery={"decision": "wait"}, busy={"tc": ("seed-run", 20.0)})
    final = run_appweaver("Protect latency while TC is busy.", world.deps(), AppWeaverConfig(lease_wait_s=45.0))
    assert final["conflict_detected_before_control"] is True
    assert world.waits == [(("tc",), 45.0)]
    assert final["waited_for_lease"] is True and final["lease_wait_s"] == pytest.approx(20.0)
    assert final["status"] == "completed" and final["partial_deployment"] is False
    # No control was sent before the wait and TC was launched exactly once (never refused).
    assert [inv[0] for inv in world.invocations] == ["kpm", "tc", "rc"]
    assert all(c["status"] == "success" for c in final["tool_calls"])
    assert world.resets == 0
    seq = nodes_of(final)
    assert seq.index("recover") < seq.index("deploy")


def test_recovery_wait_timeout_finishes_without_control():
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"], recovery={"decision": "wait"}, busy={"tc": ("seed-run", 100.0)})
    final = run_appweaver("x", world.deps(), AppWeaverConfig(lease_wait_s=45.0))
    assert final["status"] == "queued" and final["failure_reason"] == "lease_wait_timeout"
    assert world.invocations == []


def test_recovery_replans_around_busy_resource():
    world = FakeWorld(small_registry(), ["KPM", "TC", "RC"],
                      recovery={"decision": "replan", "generated_workflow": ["KPM", "TC", "RC"]}, busy={"tc": ("seed-run", 20.0)})
    final = run_appweaver("Investigate the latency spike.", world.deps(), AppWeaverConfig())
    assert final["replanned_around_resource"] is True
    assert final["generated_workflow"] == ["KPM", "RC"]
    assert "tc" in final["excluded_agents"]
    assert all(inv[0] != "tc" for inv in world.invocations)
    assert final["status"] == "completed" and world.waits == []
    recover_prompts = [p for p in world.prompts if "Recover step" in p]
    assert recover_prompts and '"agent_id": "tc"' in recover_prompts[0].split("Busy resources:")[1].split("\n")[0]


def test_validate_rejects_unsupported_ran_function_and_deprecated():
    registry = small_registry()
    registry["mac"] = make_card("mac", scopes=[("cell", "write", "mac_control")], actions=("ctrl",))
    e2 = live_e2_ran_functions()
    report = validate_chain(registry, [{"agent_id": "kpm", "action_id": "observe-rru"}, {"agent_id": "mac", "action_id": "ctrl"}], e2_functions=e2)
    assert report["verdict"] == "reject" and any(r.startswith("e2:mac") for r in report["reject_reasons"])
    report = validate_chain(registry, [{"agent_id": "kpm"}, {"agent_id": "rapp.energy_saving.v0"}], e2_functions=e2)
    assert any(r.startswith("lifecycle:") for r in report["reject_reasons"])


def test_validate_dryrun_mode_and_degradation():
    registry = small_registry()
    steps = [{"agent_id": "kpm", "action_id": "observe-rru"}, {"agent_id": "tc", "action_id": "apply-codel"}]
    calls = []
    report = validate_chain(registry, steps, mode="dryrun", dryrun_fn=lambda a, x, d: calls.append((a, x, d)) or {"ok": True})
    assert report["mode"] == "dryrun" and calls == [("tc", "apply-codel", 5)] and report["ok"]
    report = validate_chain(registry, steps, mode="dryrun", dryrun_fn=lambda a, x, d: {"ok": False})
    assert report["verdict"] == "reject"
    report = validate_chain(registry, steps, mode="dryrun", dryrun_fn=None, dryrun_reason="emu_twin missing")
    assert report["mode"] == "checks" and report["degraded_reason"] == "emu_twin missing"


def test_discovery_pins_xapps_and_keeps_deprecated_visible():
    registry = small_registry()
    pins = pinned_xapp_ids(registry)
    assert pins == ["kpm", "rc", "slice", "tc"]
    ranked, report = discover_with_report(registry, "energy saving at night", k=1, pin=pins)
    ids = [c.id for c, _ in ranked]
    assert set(pins) <= set(ids)
    assert "rapp.energy_saving" in ids and "rapp.energy_saving.v0" in ids  # rider, visible, marked deprecated
    assert report["family_slots"] == ["rapp.energy_saving"]


# --------------------------------------------------------------------------- harness

@pytest.fixture(scope="module")
def harness():
    from evaluation import run_harness as h
    return h


def test_no_prompt_contains_notes_or_category(harness):
    seen = 0
    for intent in INTENTS:
        notes = intent["notes"].strip()
        prompts = [
            harness.llm_prompt(intent),
            harness.llm_blind_prompt(intent),
            harness.agentcard_prompt(intent),
            harness.agentcard_recovery_prompt(intent, {"generated_workflow": ["KPM"]}, [{"agent_id": "tc"}]),
            harness.llm_recovery_prompt(intent, {"status": "queued", "tool_calls": []}),
        ]
        for prompt in prompts:
            assert notes not in prompt
            assert "Notes:" not in prompt and "Category:" not in prompt
            harness._RECORD_STATE["notes"] = notes
            harness.assert_prompt_label_free(prompt)
            seen += 1
        assert intent["notes"].lower() not in harness._intent_text(intent)
    harness._RECORD_STATE["notes"] = "Closed-loop latency reduction"
    with pytest.raises(AssertionError):
        harness.assert_prompt_label_free("Intent: x\nNotes: Closed-loop latency reduction\n")
    harness._RECORD_STATE["notes"] = ""
    assert seen == 5 * len(INTENTS)


def test_rule_router_ignores_labels(harness):
    for intent in INTENTS:
        stripped = {"intent": intent["intent"]}
        swapped = {**intent, "category": "slice", "notes": "TC-only action path"}
        assert harness.route_intent(intent) == harness.route_intent(stripped) == harness.route_intent(swapped)


def test_reset_is_forbidden_during_a_record(harness):
    harness._RECORD_STATE["active"] = True
    try:
        with pytest.raises(AssertionError):
            harness.reset_runtime()
    finally:
        harness._RECORD_STATE["active"] = False
        harness._RECORD_STATE["reset_calls"] = 0


def test_rc_default_action_and_markers(harness, monkeypatch):
    card = harness.AGENTS["rc"]
    monkeypatch.setattr(card, "actions", [AgentAction("rc-report", "r", "r", "suite"), AgentAction("rc-control", "c", "c", "suite")])
    assert harness.default_action_for_agent("rc", {"intent": "anything"}) == "rc-control"
    assert harness.default_action_for_agent("rc", {"intent": "Audit and monitor the cell state."}) == "rc-report"
    assert harness.default_action_for_agent("rc", {"intent": "Monitor and reduce latency."}) == "rc-control"
    assert set(harness.TOOL_ACK_MARKERS["rc"]) == {"RC CONTROL-ACK received", "RC indication received"}
    assert {"RC CONTROL-FAILED", "RC REPORT-FAILED"} <= set(harness.TOOL_ACK_NEGATIVE_MARKERS)
    assert harness.TOOL_ACK_MARKERS["tc"] == ["[xApp]: CONTROL ACK rx"] == harness.TOOL_ACK_MARKERS["slice"]


class FakePortal:
    """Minimal in-memory stand-in for the portal's run table and per-agent lease (409)."""

    def __init__(self, hold_s: float):
        self.hold_s = hold_s
        self.runs: List[Dict[str, Any]] = []
        self.resets = 0

    def _active(self, agent_id):
        now = time.time()
        return next((r for r in self.runs if r["agent_id"] == agent_id and r["until"] > now), None)

    def invoke_action(self, agent_id, action_id):
        active = self._active(agent_id)
        if active is not None:
            detail = f"409: Agent {agent_id} already has an active action ({active['action_id']}, run {active['id'][:8]})."
            return ({"agent_id": agent_id, "action_id": action_id, "xapp": agent_id.upper(), "status": "failed", "detail": detail, "run_id": None, "role": "control"}, None, detail)
        run = {"id": f"run{len(self.runs):04d}{agent_id}", "agent_id": agent_id, "action_id": action_id, "until": time.time() + self.hold_s, "status": "running"}
        self.runs.append(run)
        return ({"agent_id": agent_id, "action_id": action_id, "xapp": agent_id.upper(), "status": "success", "detail": "", "run_id": run["id"], "role": "x"}, dict(run), None)

    def api_runs(self):
        now = time.time()
        return [{"id": r["id"], "agent_id": r["agent_id"], "action_id": r["action_id"], "status": "running" if r["until"] > now else "completed"} for r in reversed(self.runs)]


@pytest.fixture()
def seeded_harness(harness, monkeypatch):
    portal = FakePortal(hold_s=0.25)
    portal.seed_hold_s = 1.0
    real_invoke = portal.invoke_action

    def invoke(agent_id, action_id):
        call, payload, err = real_invoke(agent_id, action_id)
        if not harness._RECORD_STATE.get("own_run_ids") and payload and not getattr(portal, "seeded", False):
            portal.seeded = True  # the first launch of a record is the seed: hold it longer
            portal.runs[-1]["until"] = time.time() + portal.seed_hold_s
        return call, payload, err

    def planner(prompt):
        harness.assert_prompt_label_free(prompt)
        if "Recover step" in prompt:
            body = {"decision": "wait"}
        elif "selecting exactly one workflow" in prompt:
            body = {"workflow_id": "observe-diagnose-optimize", "generated_workflow": ["KPM", "SLICE", "TC", "RC"]}
        else:
            body = {"generated_workflow": ["KPM", "SLICE", "TC", "RC"], "steps": []}
        return {"status": "completed", "response": json.dumps(body), "provider_id": "fake", "prompt": prompt}

    def reset(_request):
        portal.resets += 1
        portal.runs.clear()
        portal.seeded = False
        return {"status": "success"}

    monkeypatch.setattr(harness, "invoke_action", invoke)
    monkeypatch.setattr(harness, "api_runs", portal.api_runs)
    monkeypatch.setattr(harness, "api_runtime_leases", lambda: {"leases": []})
    monkeypatch.setattr(harness, "planner_task", planner)
    monkeypatch.setattr(harness, "api_runtime_reset", reset)
    monkeypatch.setattr(harness, "_provider_statuses", lambda: [])
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "metrics_mode", "off")
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "tool_ack_timeout_s", 0.0)
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "lease_wait_s", 3.0)
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "lease_poll_interval_s", 0.05)
    monkeypatch.setitem(harness.EVAL_RUNTIME_CONFIG, "retrieval_k", 0)
    return harness, portal


def _seeded_intent():
    return next(i for i in INTENTS if i["id"] == "latency_under_busy_tc")


def test_seeded_conflict_appweaver_detects_before_control(seeded_harness):
    h, portal = seeded_harness
    portal.seeded = False
    record = h.run_record("langgraph_agentcard", _seeded_intent(), 1, 45, True)
    assert record["conflict_seed"]["type"] == "action" and record["conflict_seed"]["agent_id"] == "tc"
    assert record["graph_backend"] == "langgraph"
    assert record["conflict_detected_before_control"] is True and record["conflict_detected"] is True
    assert record["partial_deployment"] is False
    assert record["completed_after_wait"] is True and record["lease_wait_s"] > 0.5
    assert record["preempted_other_workflow"] is False
    assert record["validation_report"]["lease_precheck"]["busy"].get("tc")
    assert not any(c.get("lease_refusal") for c in record["tool_calls"])
    nodes = [e["node"] for e in record["workflow_events"]]
    assert nodes[:4] == ["discover", "compose", "validate", "recover"] and nodes[-1] == "finish"
    assert record["execution_artifacts"]["recovery_reset_runtime"] is False
    assert "workflow_match_rule" in record and "Notes:" not in json.dumps(record["execution_artifacts"].get("planner_task"))


def test_seeded_conflict_baseline_gets_same_wait_and_partial_flag(seeded_harness):
    h, portal = seeded_harness
    portal.seeded = False
    record = h.run_record("llm_only", _seeded_intent(), 1, 45, True)
    assert record["conflict_seed"]["type"] == "action"
    refused = [c for c in record["tool_calls"] if c.get("lease_refusal")]
    assert len(refused) == 1 and refused[0]["agent_id"] == "tc"
    assert any(c.get("retry_after_lease_wait") and c["status"] == "success" for c in record["tool_calls"])
    assert record["conflict_detected_before_control"] is True
    # The template's SLICE step is `monitor`, read-only per its action scope: nothing was controlled yet.
    assert record["partial_deployment"] is False
    assert record["completed_after_wait"] is True and record["preempted_other_workflow"] is False
    assert record["replanned_around_resource"] is False


def test_partial_deployment_flag_uses_action_scope(harness):
    calls = [
        {"agent_id": "kpm", "action_id": "observe-rru", "status": "success"},
        {"agent_id": "slice", "action_id": "apply-static", "status": "success"},
        {"agent_id": "tc", "action_id": "apply-codel", "status": "conflict", "lease_refusal": True, "detail": "409: busy"},
    ]
    out = harness.conflict_outcome({"status": "queued"}, calls, False)
    assert out["partial_deployment"] is True and out["conflict_detected_before_control"] is True
    assert out["lease_refusal_unresolved"] is True and out["completed_after_wait"] is False
    calls[1]["action_id"] = "monitor"
    assert harness.conflict_outcome({"status": "queued"}, calls, False)["partial_deployment"] is False


def test_ack_uses_full_log_not_tail(harness, tmp_path):
    log = tmp_path / "tc.log"
    flood = "".join(f"RLC len=1 tstamp={i}\n" for i in range(500))
    log.write_text("setup\n[xApp]: CONTROL ACK rx\n[xApp]: Successfully received CONTROL-ACK\nApplied TC profile 'all'\n" + flood + "Error late\n", encoding="utf-8")
    assert harness._log_acknowledges("tc", flood.splitlines()[-20:]) is None  # the tail misses it
    assert harness._log_acknowledges_full("tc", str(log)) is True
    timeout = tmp_path / "timeout.log"  # library prints "Successfully received" even on a timed-out wait
    timeout.write_text("[xApp]: Successfully received CONTROL-ACK\nApplied TC profile 'codel'\n", encoding="utf-8")
    assert harness._log_acknowledges_full("tc", str(timeout)) is None
    assert harness._log_ack_hint("tc", str(timeout)) == "Applied TC profile"
    assert harness._log_acknowledges_full("slice", str(log), "monitor") is False  # no SLICE indication, an Error line
    bad = tmp_path / "bad.log"
    bad.write_text("Traceback (most recent call last)\n" + flood, encoding="utf-8")
    assert harness._log_acknowledges_full("tc", str(bad)) is False
    assert harness._log_acknowledges_full("tc", str(tmp_path / "missing.log")) is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
