#!/usr/bin/env python3
"""Build `intents_v2.json`: the original 50-intent benchmark plus intents that
need rApps from the rApp Directory.

Splits (field `split`):
  known              - matches one of the three portal workflow templates
  open_world         - no template; composable from the four FlexRIC xApps
  unseen_capability  - needs at least one rApp capability that appears in no
                       template and in no deterministic fallback rule

Chains name agents by registry id (upper-cased for comparison); rApp ids are
`RAPP.<FAMILY>` so vendor variants and deprecated releases of the same family
count as wrong selections (the directory contains them as distractors).
`accepted_workflows` lists the alternative valid chains where the ordering of
observation and prediction steps is genuinely interchangeable.

rApp alternatives for the 50 original intents (directory ON only changes what is
*available*, never what the task needs). An original xApp chain gains one extra
accepted chain per rule below, and only when all conditions hold:
  1. the rApp family is read-only (its card's control scopes are all `read`):
     QOE_PREDICTION, ANOMALY_DETECTION, ROOT_CAUSE, PM_KPI. Write-scope rApps
     (SLICE_SLA, TRANSPORT_QOS, MOBILITY_OPTIMIZATION, ...) are never accepted,
     because they would duplicate or replace the xApp control step the label
     specifies (two writers on one control resource);
  2. the intent text explicitly asks for that analytic function (whole-word
     patterns in RAPP_TRIGGERS; the intent id and tags are not consulted);
  3. the chain has a KPM step; the rApp is inserted immediately after it
     (every rApp consumes KPM data), and every original step is kept in order.
Chains that drop or reorder an xApp step, or add a second rApp, stay wrong.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent

NEW_INTENTS: List[Dict[str, Any]] = [
    {"id": "night_energy_saving", "intent": "Reduce RAN energy consumption between 01:00 and 05:00 by switching off lightly loaded cells without breaking coverage.", "category": "energy", "expected_workflow": ["KPM", "RAPP.ENERGY_SAVING", "RC"], "accepted_workflows": [["KPM", "RAPP.ENERGY_SAVING", "RC"], ["RAPP.PM_KPI", "RAPP.ENERGY_SAVING", "RC"]], "tags": ["energy", "uc21"], "notes": "Observe PRB load, pick sleep cells, validate the RC control."},
    {"id": "energy_saving_wakeup_guard", "intent": "Wake sleeping cells as soon as PRB utilisation on the neighbours exceeds 70 percent.", "category": "energy", "expected_workflow": ["KPM", "RAPP.ENERGY_SAVING"], "tags": ["energy"], "notes": "Observation followed by the energy-saving wake tool."},
    {"id": "energy_vs_capacity_conflict", "intent": "Cut site power at night but keep the capacity expansion plan for the stadium site untouched.", "category": "energy", "expected_workflow": ["KPM", "RAPP.ENERGY_SAVING", "RC"], "tags": ["energy", "conflict-scope"], "notes": "Capacity manager must not be composed with energy saving (declared conflict)."},
    {"id": "cell_edge_qoe_protection", "intent": "Improve cell-edge QoE for Zone A: predict at-risk users and raise their scheduling priority.", "category": "qoe", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.UE_QOS_CONTROL", "RC"], "tags": ["qoe", "running-example"], "notes": "The paper's running example, now with real rApps."},
    {"id": "video_qoe_forecast", "intent": "Forecast MOS for video users in the downtown cluster for the next 15 minutes and explain the bottleneck.", "category": "qoe", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION"], "tags": ["qoe", "predict-only"], "notes": "Prediction only, no control."},
    {"id": "qoe_driven_steering", "intent": "Steer at-risk video users away from the congested cell before their QoE drops.", "category": "qoe", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.TRAFFIC_STEERING", "RC"], "tags": ["qoe", "steering"], "notes": "Prediction feeds steering."},
    {"id": "load_balance_hotspot", "intent": "Balance load between the two busiest cells of the campus using traffic steering.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.TRAFFIC_STEERING", "RC"], "tags": ["steering"], "notes": "Observe, steer, validate."},
    {"id": "ping_pong_handover_fix", "intent": "Stop ping-pong handovers on the highway cells by tuning handover margins.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.MOBILITY_OPTIMIZATION", "RC"], "tags": ["mro"], "notes": "MRO rApp with RC validation."},
    {"id": "mobility_root_cause", "intent": "Find out why handover failures doubled yesterday on the ring road cells.", "category": "anomaly", "expected_workflow": ["KPM", "RAPP.ROOT_CAUSE"], "tags": ["rca", "diagnose-only"], "notes": "Diagnosis only."},
    {"id": "coverage_hole_tilt", "intent": "Close the coverage hole near the harbour by adjusting antenna tilt on the surrounding cells.", "category": "coverage", "expected_workflow": ["KPM", "RAPP.RET_TILT", "RC"], "tags": ["ret"], "notes": "RET optimisation."},
    {"id": "tilt_after_outage", "intent": "A cell is down: compensate its coverage with the neighbours' tilt and power until it is repaired.", "category": "healing", "expected_workflow": ["KPM", "RAPP.ROOT_CAUSE", "RAPP.SELF_HEALING", "RC"], "tags": ["coc"], "notes": "Outage compensation requires root-cause evidence first."},
    {"id": "kpi_anomaly_sweep", "intent": "Flag any cell whose downlink delay left its weekly baseline in the last hour.", "category": "anomaly", "expected_workflow": ["KPM", "RAPP.ANOMALY_DETECTION"], "tags": ["anomaly"], "notes": "Detection only."},
    {"id": "anomaly_to_transport_fix", "intent": "When delay anomalies point at the backhaul, apply a CoDel policy on the affected bearers.", "category": "transport", "expected_workflow": ["KPM", "RAPP.ANOMALY_DETECTION", "TC", "RC"], "tags": ["anomaly", "transport"], "notes": "Detector gates the TC action."},
    {"id": "slice_sla_breach", "intent": "The enterprise slice is breaching its latency SLA; re-balance PRB reservations and verify.", "category": "slice", "expected_workflow": ["KPM", "RAPP.SLICE_SLA", "SLICE", "RC"], "tags": ["slice", "sla"], "notes": "SLA assurance drives the slice xApp."},
    {"id": "slice_sla_report", "intent": "Produce the monthly SLA evidence report for all tenant slices.", "category": "enterprise", "expected_workflow": ["RAPP.PM_KPI"], "tags": ["pm", "report-only"], "notes": "Single rApp."},
    {"id": "capacity_headroom_forecast", "intent": "Forecast PRB headroom per site for next quarter and list sites that need a new carrier.", "category": "capacity", "expected_workflow": ["KPM", "RAPP.CAPACITY_MGMT"], "tags": ["capacity"], "notes": "Planning only."},
    {"id": "spectrum_resplit", "intent": "Re-split the shared carrier between the two RATs based on the capacity forecast.", "category": "capacity", "expected_workflow": ["KPM", "RAPP.CAPACITY_MGMT", "RAPP.SPECTRUM_SHARING", "RC"], "tags": ["dss"], "notes": "Spectrum planner requires capacity planning upstream."},
    {"id": "interference_hotspot", "intent": "SINR collapsed on three low-load cells; mitigate the interference.", "category": "healing", "expected_workflow": ["KPM", "RAPP.INTERFERENCE", "RC"], "tags": ["interference"], "notes": "Interference mitigation."},
    {"id": "backhaul_policy_advice", "intent": "Recommend a queue policy per bearer class for the congested backhaul link and apply it.", "category": "transport", "expected_workflow": ["KPM", "RAPP.TRANSPORT_QOS", "TC", "RC"], "tags": ["transport"], "notes": "Advisor rApp then TC xApp."},
    {"id": "pm_report_daily", "intent": "Aggregate today's KPM into the daily performance report.", "category": "enterprise", "expected_workflow": ["KPM", "RAPP.PM_KPI"], "tags": ["pm"], "notes": "Observation plus report."},
    {"id": "config_rollout_window", "intent": "Roll out the new scheduler configuration to all sites in tonight's maintenance window.", "category": "deployment", "expected_workflow": ["RAPP.RAN_LIFECYCLE"], "tags": ["lcm"], "notes": "Lifecycle orchestration only."},
    {"id": "rollout_blocked_by_energy", "intent": "Roll out the configuration tonight, but energy saving is switching cells off at the same time.", "category": "deployment", "expected_workflow": ["RAPP.RAN_LIFECYCLE"], "tags": ["lcm", "conflict-scope"], "notes": "Lifecycle conflicts with cell_power writers; energy saving must not be composed."},
    {"id": "priority_for_emergency_ues", "intent": "Give emergency-service UEs top scheduling priority in the stadium cell right now.", "category": "qoe", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.UE_QOS_CONTROL"], "tags": ["qos"], "notes": "QoS controller requires QoE prediction upstream (card dependency)."},
    {"id": "deprecated_card_trap", "intent": "Use the legacy energy saver to switch off cells tonight.", "category": "energy", "expected_workflow": ["KPM", "RAPP.ENERGY_SAVING", "RC"], "tags": ["energy", "distractor"], "notes": "Intent mentions the legacy card; the deprecated release must still not be selected."},
    {"id": "vendor_variant_trap", "intent": "Run Northwind's traffic steering to relieve the hotspot cell.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.TRAFFIC_STEERING", "RC"], "accepted_workflows": [["KPM", "RAPP.TRAFFIC_STEERING", "RC"], ["KPM", "RAPP.TRAFFIC_STEERING.NORTHWIND", "RC"]], "tags": ["steering", "distractor"], "notes": "Either the canonical or the named vendor variant is acceptable."},
    {"id": "qoe_without_observation", "intent": "Estimate current MOS per cell.", "category": "qoe", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION"], "tags": ["qoe", "underspecified"], "notes": "Underspecified: planner must add the observation step the predictor requires."},
    {"id": "healing_full_chain", "intent": "Detect, diagnose and compensate a degraded cell automatically.", "category": "healing", "expected_workflow": ["KPM", "RAPP.ANOMALY_DETECTION", "RAPP.ROOT_CAUSE", "RAPP.SELF_HEALING", "RC"], "tags": ["healing", "long-chain"], "notes": "Five-step chain across three rApps."},
    {"id": "steering_then_energy", "intent": "Consolidate users onto fewer cells, then put the emptied cells to sleep.", "category": "energy", "expected_workflow": ["KPM", "RAPP.TRAFFIC_STEERING", "RAPP.ENERGY_SAVING", "RC"], "tags": ["energy", "steering", "long-chain"], "notes": "Steering writes rc_control, energy saving writes cell_power; traffic steering declares cell_power as conflicting, so order matters."},
    {"id": "unknown_vertical_request", "intent": "Our drone-delivery pilot needs stable uplink video in the industrial park this afternoon.", "category": "unknown", "expected_workflow": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.UE_QOS_CONTROL", "RC"], "tags": ["underspecified", "vertical"], "notes": "No keyword overlap with any card name."},
    {"id": "report_then_tilt", "intent": "Build the coverage KPI report for the harbour cluster and fix the weakest cell's tilt.", "category": "coverage", "expected_workflow": ["KPM", "RAPP.PM_KPI", "RAPP.RET_TILT", "RC"], "tags": ["ret", "pm"], "notes": "Report precedes control."},
]

RAPP_CAPABILITIES_NOT_IN_TEMPLATES = {"RAPP."}

# Read-only analytic rApps and the intent wording that explicitly asks for them (rule 2 above).
RAPP_TRIGGERS: Dict[str, str] = {
    "RAPP.QOE_PREDICTION": r"\b(qoe|mos|quality of experience)\b",
    "RAPP.ANOMALY_DETECTION": r"\b(anomal(y|ies|ous)|detect|drift)\b",
    "RAPP.ROOT_CAUSE": r"\b(root cause|diagnose|investigate|triage)\b",
    "RAPP.PM_KPI": r"\b(report|audit)\b",
}


def rapp_alternatives(item: Dict[str, Any]) -> List[List[str]]:
    """Extra accepted chains for an original xApp intent (see module docstring)."""
    chain = [str(step) for step in item["expected_workflow"]]
    if "KPM" not in chain:
        return []
    text = str(item.get("intent") or "").lower()
    at = chain.index("KPM") + 1
    return [chain[:at] + [rapp] + chain[at:] for rapp, pattern in RAPP_TRIGGERS.items() if re.search(pattern, text)]


def main() -> int:
    base = json.loads((HERE / "intents_50.json").read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for item in base:
        entry = dict(item)
        entry["split"] = "open_world" if item.get("open_world") else "known"
        entry.setdefault("accepted_workflows", [list(item["expected_workflow"])])
        entry["accepted_workflows"] += [alt for alt in rapp_alternatives(item) if alt not in entry["accepted_workflows"]]
        out.append(entry)
    for item in NEW_INTENTS:
        entry = dict(item)
        entry["open_world"] = True
        entry["split"] = "unseen_capability" if any(step.startswith("RAPP.") for step in entry["expected_workflow"]) else "open_world"
        entry["expected_workflow_id"] = "custom:" + "-".join(step.lower() for step in entry["expected_workflow"])
        entry["expects_conflict"] = False
        entry.setdefault("accepted_workflows", [list(entry["expected_workflow"])])
        out.append(entry)
    path = HERE / "intents_v2.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    splits: Dict[str, int] = {}
    for entry in out:
        splits[entry["split"]] = splits.get(entry["split"], 0) + 1
    print(f"wrote {path} with {len(out)} intents: {splits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
