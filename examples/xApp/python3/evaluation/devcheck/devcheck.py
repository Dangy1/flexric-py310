"""Planner-only development check (no RIC, no deploy): run the AppWeaver graph with fake invoke/leases
on the Batch A intents and score with the pre-registered label rule. Usage: devcheck.py METHOD OUT.jsonl"""
import json, os, sys, tempfile, time
tmp = tempfile.mkdtemp(prefix="devcheck-")
os.environ["FLEXRIC_AGENT_PORTAL_DB_PATH"] = f"{tmp}/portal.db"
os.environ["FLEXRIC_AGENT_PORTAL_LOG_DIR"] = f"{tmp}/runs"
ROOT = os.path.expanduser("~/flexric-learning/examples/xApp/python3")
sys.path[:0] = [ROOT, ROOT + "/evaluation"]
os.chdir(ROOT + "/evaluation")
import run_harness as h
import flexric_agent_portal
from backend.appweaver import AppWeaverConfig, AppWeaverDeps, run_appweaver
from evaluation.label_rules import rule_match
method, out = sys.argv[1], sys.argv[2]
intents_file = sys.argv[3] if len(sys.argv) > 3 else "intents_50.json"
flexric_agent_portal.MAX_PROMPT_CHARS = 160000
h.EVAL_RUNTIME_CONFIG["memory_path"] = str(h.DEFAULT_MEMORY_PATH)
learning = h.LEARNING_METHODS.get(method, {})
cfg = AppWeaverConfig(variant=method, validate_mode="checks", lease_wait_s=0.0,
                      workflow_templates=bool(learning.get("workflow_templates")),
                      memory_path=str(h.DEFAULT_MEMORY_PATH) if learning.get("memory") else None,
                      guidance=bool(learning.get("guidance")), feedback=bool(learning.get("feedback")), needs=bool(learning.get("needs")))
def invoke(agent_id, action_id):
    return {"tool_calls": [{"agent_id": agent_id, "action_id": action_id, "status": "success", "run_id": "x"}],
            "run_payloads": [], "error": None, "lease_wait_s": 0.0, "refused": False}
deps = AppWeaverDeps(registry=h.AGENTS, discover=lambda t, e: h.discover_for_text(t, e), planner=h.planner_task,
                     invoke=invoke, lease_query=lambda ids: {a: None for a in ids},
                     wait_until_free=lambda ids, b: {"free": True, "waited_s": 0.0},
                     resolve_action=lambda a, t: h.default_action_for_agent(a, {"intent": t}),
                     is_unavailable=h._is_provider_unavailable, e2_functions=None)
intents = json.load(open(intents_file))
done = set()
if os.path.exists(out):
    done = {json.loads(l)["intent_id"] for l in open(out)}
with open(out, "a") as f:
    for it in intents:
        if it["id"] in done:
            continue
        t0 = time.time()
        final = run_appweaver(it["intent"], deps, cfg)
        chain = list(final.get("generated_workflow") or [])
        ok, reasons = rule_match(chain, it, h.AGENTS)
        f.write(json.dumps({"intent_id": it["id"], "method": method, "chain": chain, "rule": ok, "reasons": reasons,
                            "feedback": final.get("feedback"), "needs": final.get("needs"), "status": final.get("status"), "s": round(time.time() - t0, 1)}) + "\n")
        f.flush()
