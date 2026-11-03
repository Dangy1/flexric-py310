#!/usr/bin/env python3
"""Re-score the paper batches for the defects found in the 2026-11-03 code review, from the stored records
and the portal run logs (nothing is re-run).

  acks         TOOL_ACK_MARKERS had the bare word "indication" for KPM (matched by the reader's "Still waiting
               for shared KPM bus indications..." line) and "RC indication received" for RC (also inside the
               failure line "RC REPORT-FAILED: no RC indication received"); positive markers won over negative
               ones, and a run that exited 0 with no marker counted as acknowledged. Fixed rule: a positive
               marker must be a real record (KPM `meas=RRU.`/`meas=DRB.`, a line *starting* with
               "RC indication received:" or "RC CONTROL-ACK received", the other xApps' E2 markers, "rApp ack:"),
               and a call without one is not acknowledged. rApp acks are also split by whether the rApp
               decided on KPM data (`"kpm_available": true` in its reply).
  conflicts    conflict_flagged() counted any `blocked_reason` (also a compat rejection or a failed step) as a
               detected conflict. Strict rule: lease evidence only (a refused or queued call, a busy lease in
               the validation pre-check, a queued execution).
  hallucination AppWeaver's count was taken after repair (unknown ids already dropped). Also counted on the
               planner's raw chain.
  e2conf       share of AppWeaver records whose E2 conformance check had RIC data (available = True).

Writes <batch>/review_rescore.json (per-call ack overrides + per-record strict conflict flag) and prints the
per-method comparison. make_paper_figures.py applies the overrides when the file exists.

  python rescore_review.py [batch dirs...]
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LOG_DIR = Path("/tmp/flexric_agent_portal")
PAPER_BATCHES = ["20261028T190000Z_A_final_gptoss120b_spark1_seededfix", "20261030T134800Z_B_k8_final_repaired_with_variants_gptoss120b_spark1",
                 "20261031T005700Z_B_k0_final_merged_gptoss120b_spark1", "20261031T051600Z_C_final_merged_gptoss120b_spark1"]
E2_CONTROL_ACK = "[xApp]: CONTROL ACK rx"
LINE_MARKERS = {  # (regex over lines)
    "kpm": re.compile(r"meas=(RRU|DRB)\.|\"meas\""),
    "slice": re.compile(re.escape(E2_CONTROL_ACK)),
    "tc": re.compile(re.escape(E2_CONTROL_ACK)),
    "rc": re.compile(r"^(RC CONTROL-ACK received|RC indication received:)", re.M),
    "mac": re.compile(r"MAC ind tstamp="), "rlc": re.compile(r"RLC ind tstamp="),
    "pdcp": re.compile(r"PDCP ind tstamp="), "gtp": re.compile(r"GTP ind tstamp="),
}
ACTION_MARKERS = {("slice", "monitor"): re.compile(r"SLICE ind tstamp=")}
CACHE_OF: Dict[str, Optional[bool]] = {}


def log_text(agent: str, action: str, run_id: str) -> Optional[str]:
    path = LOG_DIR / f"{agent}-{action}-{run_id}.log"
    try:
        return path.read_bytes()[: 16 * 1024 * 1024].decode("utf-8", errors="replace")
    except OSError:
        return None


def fixed_ack(call: Dict[str, Any]) -> Dict[str, Any]:
    """{'ack': bool|None (None = log missing), 'rapp_on_data': bool|None}"""
    agent, action, run_id = str(call.get("agent_id") or ""), str(call.get("action_id") or ""), str(call.get("run_id") or "")
    if call.get("status") in {"failed", "conflict", "queued"} or not run_id:
        return {"ack": False, "rapp_on_data": None}
    if run_id.startswith("cached-"):
        return {"ack": CACHE_OF.get(f"{agent}/{action}"), "rapp_on_data": None, "cached": True}
    text = log_text(agent, action, run_id)
    if text is None:
        return {"ack": None, "rapp_on_data": None}
    if agent.startswith("rapp."):
        ok = "rApp ack:" in text and "rApp error:" not in text.split("rApp ack:")[0]
        on_data = None
        m = re.search(r"\"kpm_available\":\s*(true|false)", text)
        if m:
            on_data = m.group(1) == "true"
        return {"ack": ok, "rapp_on_data": on_data}
    rx = ACTION_MARKERS.get((agent, action)) or LINE_MARKERS.get(agent)
    ok = bool(rx and rx.search(text))
    CACHE_OF[f"{agent}/{action}"] = ok
    return {"ack": ok, "rapp_on_data": None}


def strict_conflict(r: Dict[str, Any]) -> bool:
    calls = r.get("tool_calls") or []
    if any(c.get("status") in {"conflict", "queued"} or c.get("lease_refusal") for c in calls):
        return True
    if str(r.get("execution_status") or "") == "queued":
        return True
    for vr in [r.get("validation_report") or {}] + list((r.get("execution_artifacts") or {}).get("validation_history") or []):
        if (vr.get("lease_precheck") or {}).get("busy") or vr.get("busy"):
            return True
    init = (r.get("execution_artifacts") or {}).get("initial_execution") or {}
    return any(c.get("status") in {"conflict", "queued"} or c.get("lease_refusal") for c in init.get("tool_calls") or [])


def known_ids(records: List[Dict[str, Any]]) -> set:
    reg = json.loads((HERE.parent / "rapps" / "catalog.json").read_text())
    ids = {c["id"].upper() for c in reg} | {"KPM", "SLICE", "TC", "RC", "MAC", "RLC", "PDCP", "GTP"}
    return ids


def main(argv: List[str]) -> int:
    batches = [HERE / "runs" / b for b in (argv or PAPER_BATCHES)]
    for b in batches:
        records = [json.loads(l) for l in (b / "records.jsonl").read_text().splitlines() if l.strip()]
        known = known_ids(records)
        CACHE_OF.clear()
        overrides, per_method = {}, defaultdict(lambda: defaultdict(int))
        for r in records:
            m = r["method"]
            pm = per_method[m]
            rid = r["record_id"]
            calls_fixed = []
            for i, c in enumerate(r.get("tool_calls") or []):
                fx = fixed_ack(c)
                calls_fixed.append((c.get("acknowledged") is True) and fx["ack"] is not False if c.get("acknowledged") is not None else None)
                if c.get("acknowledged") is None or c.get("status") == "conflict":
                    continue
                pm["calls"] += 1
                pm["old_ack"] += c.get("acknowledged") is True
                # Only remove acknowledgements: a call the original deadline did not see acknowledged stays unacknowledged.
                new = (c.get("acknowledged") is True) and fx["ack"] is not False
                pm["log_missing"] += fx["ack"] is None
                pm["new_ack"] += new
                if c.get("role") == "control":
                    pm["ctl_calls"] += 1
                    pm["ctl_old"] += c.get("acknowledged") is True
                    pm["ctl_new"] += (c.get("acknowledged") is True) and fx["ack"] is not False
                if str(c.get("agent_id")).startswith("rapp.") and fx["ack"]:
                    pm["rapp_ack"] += 1
                    pm["rapp_ack_no_data"] += fx["rapp_on_data"] is False
                if c.get("acknowledged") is True and fx["ack"] is False:
                    pm[f"flipped_{c.get('agent_id') if not str(c.get('agent_id')).startswith('rapp.') else 'rapp'}"] += 1
            sc = strict_conflict(r)
            overrides[rid] = {"acks": calls_fixed, "conflict_strict": sc}
            if r.get("conflict_label") is True:
                pm["seeded"] += 1
                pm["seeded_old"] += bool(r.get("conflict_detected") or r.get("blocked_reason"))
                pm["seeded_strict"] += sc
                pm["seeded_completed"] += r.get("execution_status") == "completed" and not r.get("preempted_other_workflow")
                pm["seeded_completed_after_wait_old"] += bool(r.get("completed_after_wait"))
            elif r.get("conflict_label") is False:
                pm["unseeded"] += 1
                pm["fp_old"] += bool(r.get("conflict_detected") or r.get("blocked_reason"))
                pm["fp_strict"] += sc
            raw = (r.get("execution_artifacts") or {}).get("raw_chain")
            if raw is not None:
                pm["raw_halluc"] += sum(1 for x in raw if str(x).upper() not in known)
                pm["raw_halluc_records"] += any(str(x).upper() not in known for x in raw)
            pm["halluc_reported"] += int(r.get("hallucinated_reference_count") or 0)
            if m.startswith("langgraph") or m.startswith("appweaver"):
                e2 = ((r.get("validation_report") or {}).get("e2_conformance") or {})
                if e2:
                    pm["e2conf_records"] += 1
                    pm["e2conf_available"] += e2.get("available") is True
        (b / "review_rescore.json").write_text(json.dumps({"rules": __doc__, "records": overrides}, indent=0))
        print(f"\n== {b.name}")
        for m, pm in per_method.items():
            pct = lambda a, n: f"{100 * a / n:.1f}%" if n else "--"  # noqa: E731
            flips = {k[8:]: v for k, v in pm.items() if k.startswith("flipped_")}
            print(f"{m:22s} ack {pct(pm['old_ack'], pm['calls'])} -> {pct(pm['new_ack'], pm['calls'])} (n={pm['calls']}, log missing {pm['log_missing']}) "
                  f"control {pct(pm['ctl_old'], pm['ctl_calls'])} -> {pct(pm['ctl_new'], pm['ctl_calls'])} (n={pm['ctl_calls']}) flips {flips} "
                  f"rApp acks without KPM data {pm['rapp_ack_no_data']}/{pm['rapp_ack']}")
            if pm["seeded"] or pm["unseeded"]:
                print(f"{'':22s} recall {pm['seeded_old']}/{pm['seeded']} -> {pm['seeded_strict']}/{pm['seeded']}  FP {pm['fp_old']}/{pm['unseeded']} -> "
                      f"{pm['fp_strict']}/{pm['unseeded']}  seeded completed {pm['seeded_completed']} (after-wait flag {pm['seeded_completed_after_wait_old']})")
            print(f"{'':22s} halluc reported {pm['halluc_reported']}, raw-chain {pm['raw_halluc']} in {pm['raw_halluc_records']} records"
                  + (f"; E2 conformance available {pm['e2conf_available']}/{pm['e2conf_records']}" if pm["e2conf_records"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
