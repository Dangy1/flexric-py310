#!/usr/bin/env python3
"""Build `intents_v2.json`: the original 50-intent benchmark plus intents that
need rApps from the rApp Directory.

Splits (field `split`):
  known              - matches one of the three portal workflow templates
  open_world         - no template; composable from the four FlexRIC xApps
  unseen_capability  - needs at least one rApp capability that appears in no
                       template and in no deterministic fallback rule; for the
                       directory-extension intents (DIRECTORY_EXTENSION_INTENTS,
                       2026-10-28) also an L2 monitor action (MAC/RLC/PDCP/GTP)
                       that no template executes

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
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

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

# Directory extension (workstream E, 2026-10-28): intents that need the families added to the rApp
# Directory on 2026-10-28 or the L2 monitor xApps (MAC/RLC/PDCP/GTP, executable since the same date).
# Written results-blind from the use-case definitions in docs/RAPP_USE_CASES.md (field `provenance`
# names the use-case row) and the cards; operator wording, no application names. All are
# `unseen_capability`: each needs an rApp family or an L2 monitor action that no workflow template
# executes and no earlier label uses. `notes` and `provenance` are annotations only.
DIRECTORY_EXTENSION_INTENTS: List[Dict[str, Any]] = [
    {"id": "new_small_cells_neighbours", "intent": "We just integrated three new small cells in the shopping mall; make sure they have the right neighbour relations so users can hand over to and from them.", "category": "deployment", "expected_workflow": ["KPM", "RAPP.ANR"], "tags": ["anr", "son"], "provenance": "docs/RAPP_USE_CASES.md#E01", "notes": "Missing neighbour relations after cell integration: ANR adds them. MRO (handover margins) is a distractor."},
    {"id": "far_neighbour_blocklist", "intent": "Handovers from the airport cells keep going to a cell 40 km away across the bay; remove that neighbour and stop handovers to it.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.ANR"], "tags": ["anr", "blocklist"], "provenance": "docs/RAPP_USE_CASES.md#E01", "notes": "Neighbour removal / handover blocklisting is an ANR function, not handover-margin tuning."},
    {"id": "pci_clash_fix", "intent": "Drive tests show two neighbours of cell 1043 transmitting the same physical cell ID; fix the clash.", "category": "healing", "expected_workflow": ["KPM", "RAPP.PCI_OPTIMIZATION"], "tags": ["pci", "son"], "provenance": "docs/RAPP_USE_CASES.md#E02", "notes": "PCI confusion: PCI reassignment. The interference mitigator (power caps) is a distractor."},
    {"id": "pci_then_neighbour_refresh", "intent": "Resolve the cell-identity clashes in the north cluster and then rebuild the neighbour lists to match the new identities.", "category": "deployment", "expected_workflow": ["KPM", "RAPP.PCI_OPTIMIZATION", "RAPP.ANR"], "tags": ["pci", "anr", "long-chain"], "provenance": "docs/RAPP_USE_CASES.md#E02; docs/RAPP_USE_CASES.md#E01", "notes": "Two O1 configuration writers on different resources (pci_config, neighbour_relations)."},
    {"id": "silent_cell_sweep", "intent": "Some suburban cells raise no alarm but customers report no service there; find the cells that silently stopped carrying traffic.", "category": "healing", "expected_workflow": ["KPM", "RAPP.SLEEPING_CELL"], "tags": ["cod", "detect-only"], "provenance": "docs/RAPP_USE_CASES.md#E03", "notes": "Sleeping-cell detection only; no compensation requested."},
    {"id": "silent_cell_compensation", "intent": "Find any silently failed cell in the riverside cluster, establish why it failed and let its neighbours cover the area until it is repaired.", "category": "healing", "expected_workflow": ["KPM", "RAPP.SLEEPING_CELL", "RAPP.ROOT_CAUSE", "RAPP.SELF_HEALING", "RC"], "tags": ["cod", "coc", "long-chain"], "provenance": "docs/RAPP_USE_CASES.md#E03", "notes": "Detect (COD) -> diagnose (RCA, required by the compensator) -> compensate (COC); RC validation optional."},
    {"id": "evening_cell_border_shift", "intent": "Cell 12 runs at 90 percent load every evening while its neighbours sit at 30 percent; shift the cell borders so the load evens out.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.MOBILITY_LOAD_BALANCING"], "tags": ["mlb", "cio"], "provenance": "docs/RAPP_USE_CASES.md#E04", "notes": "Persistent imbalance, fixed by cell-level offsets (CIO). Per-UE traffic steering is not what is asked."},
    {"id": "border_shift_keep_mro", "intent": "Even out the load between the stadium cells by moving the cell boundaries, without touching the handover-margin tuning that is already running there.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.MOBILITY_LOAD_BALANCING"], "tags": ["mlb", "conflict-scope"], "provenance": "docs/RAPP_USE_CASES.md#E04", "notes": "MLB and MRO tune the same handover triggers (declared conflict); MRO must not be composed."},
    {"id": "port_access_failures", "intent": "Random-access failures on the port cells tripled after the new container terminal opened; tune the access channel settings.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.RACH_OPTIMIZATION"], "tags": ["rach", "son"], "provenance": "docs/RAPP_USE_CASES.md#E05", "notes": "RACH parameter optimisation."},
    {"id": "highrise_beam_coverage", "intent": "Users on the upper floors of the new office towers get poor service from the massive-MIMO site next door; adapt its beams to cover them.", "category": "coverage", "expected_workflow": ["KPM", "RAPP.BEAMFORMING"], "tags": ["mmimo", "gob"], "provenance": "docs/RAPP_USE_CASES.md#E06", "notes": "GoB beam-pattern optimisation; RET tilt is the distractor (and declared conflicting)."},
    {"id": "beam_then_link_check", "intent": "Retune the massive-MIMO beams at the stadium site and then check per-user channel quality and MCS to confirm the radio links improved.", "category": "coverage", "expected_workflow": ["KPM", "RAPP.BEAMFORMING", "MAC"], "tags": ["mmimo", "mac", "post-check"], "provenance": "docs/RAPP_USE_CASES.md#E06; docs/RAPP_USE_CASES.md#E17", "notes": "Per-UE CQI/MCS comes from the MAC monitor, not from KPM."},
    {"id": "midday_antenna_muting", "intent": "Save energy on the 64-antenna sites during the quiet midday hours without switching any cell off.", "category": "energy", "expected_workflow": ["KPM", "RAPP.MIMO_SLEEP"], "tags": ["energy", "mimo"], "provenance": "docs/RAPP_USE_CASES.md#E07", "notes": "RF channel / MIMO muting; cell sleep is excluded by the intent."},
    {"id": "forecast_antenna_muting", "intent": "Use the expected load for the next hour to decide which massive-MIMO cells can run with fewer active antennas, then apply it.", "category": "energy", "expected_workflow": ["KPM", "RAPP.TRAFFIC_FORECAST", "RAPP.MIMO_SLEEP"], "tags": ["energy", "mimo", "forecast"], "provenance": "docs/RAPP_USE_CASES.md#E07; docs/RAPP_USE_CASES.md#E08", "notes": "Forecast feeds the muting decision."},
    {"id": "station_load_outlook", "intent": "How busy will the cells around the central station be over the next three hours?", "category": "capacity", "expected_workflow": ["KPM", "RAPP.TRAFFIC_FORECAST"], "tags": ["forecast", "predict-only"], "provenance": "docs/RAPP_USE_CASES.md#E08", "notes": "Short-term forecast only; capacity planning (carrier add) is a distractor."},
    {"id": "forecast_then_cell_sleep", "intent": "Predict tonight's traffic and switch off the capacity cells that will stay idle.", "category": "energy", "expected_workflow": ["KPM", "RAPP.TRAFFIC_FORECAST", "RAPP.ENERGY_SAVING"], "tags": ["energy", "forecast"], "provenance": "docs/RAPP_USE_CASES.md#E08; docs/RAPP_USE_CASES.md#E07", "notes": "Prediction then cell switch-off (UC21)."},
    {"id": "radio_failure_outlook", "intent": "Which radio units are likely to fail in the coming week, so we can send the field team before they break?", "category": "healing", "expected_workflow": ["KPM", "RAPP.FAULT_PREDICTION"], "tags": ["fault-prediction", "predict-only"], "provenance": "docs/RAPP_USE_CASES.md#E09", "notes": "Predictive maintenance, no control; root cause analysis explains past faults."},
    {"id": "tenant_session_cap", "intent": "The gaming tenant is flooding the shared cells with new sessions; cap how many new sessions its slice may open so the public-safety slice keeps its guarantees.", "category": "slice", "expected_workflow": ["KPM", "RAPP.SLICE_ADMISSION"], "tags": ["slice", "admission"], "provenance": "docs/RAPP_USE_CASES.md#E10", "notes": "Admission control per slice/tenant; PRB re-reservation (SLICE_SLA / SLICE) is not asked."},
    {"id": "meter_reconnect_storm", "intent": "Thousands of smart meters reconnect at the same second after a power cut and the control plane is choking; detect it and throttle them.", "category": "healing", "expected_workflow": ["KPM", "RAPP.SIGNALLING_STORM", "RC"], "tags": ["signalling-storm"], "provenance": "docs/RAPP_USE_CASES.md#E11", "notes": "O-RAN UC15 detection + mitigation; RC validation optional."},
    {"id": "rural_uplink_noise", "intent": "Uplink throughput in the rural cells near the military range collapsed and the uplink noise floor is up; find the interference and adjust uplink power control.", "category": "healing", "expected_workflow": ["KPM", "RAPP.UL_INTERFERENCE"], "tags": ["interference", "uplink"], "provenance": "docs/RAPP_USE_CASES.md#E12", "notes": "Uplink interference / P0-alpha retuning; the downlink interference mitigator is a distractor."},
    {"id": "nsa_nr_leg_overload", "intent": "Our 5G non-standalone phones are overloading the NR carrier at the university while the LTE anchors are idle; rebalance the dual-connectivity split.", "category": "mobility", "expected_workflow": ["KPM", "RAPP.ENDC_STEERING"], "tags": ["endc", "nsa"], "provenance": "docs/RAPP_USE_CASES.md#E13", "notes": "EN-DC distribution profile; same-RAT steering/MLB are distractors."},
    {"id": "golden_config_drift", "intent": "Before tonight's change window, check whether any site has parameters that drifted from the golden configuration.", "category": "deployment", "expected_workflow": ["RAPP.CONFIG_AUDIT"], "tags": ["audit", "report-only"], "provenance": "docs/RAPP_USE_CASES.md#E14", "notes": "Read-only CM audit; no KPM input needed (extra observation allowed)."},
    {"id": "audit_then_rollout", "intent": "Check the north region for parameters that deviate from the baseline, then roll the corrected configuration out in tonight's maintenance window.", "category": "deployment", "expected_workflow": ["RAPP.CONFIG_AUDIT", "RAPP.RAN_LIFECYCLE"], "tags": ["audit", "lcm"], "provenance": "docs/RAPP_USE_CASES.md#E14", "notes": "Audit before rollout."},
    {"id": "antenna_swap_wrong_sector", "intent": "Since last week's antenna swap at site 220, handovers go to the wrong sector; check whether the feeders were crossed.", "category": "deployment", "expected_workflow": ["KPM", "RAPP.CROSSED_FEEDER"], "tags": ["crossed-feeder", "detect-only"], "provenance": "docs/RAPP_USE_CASES.md#E15", "notes": "Installation-error detection; ANR/MRO are distractors."},
    {"id": "arena_concert_profile", "intent": "There is a concert at the arena on Saturday from 18:00 to 23:00; prepare the surrounding cells for the crowd and put them back to normal afterwards.", "category": "capacity", "expected_workflow": ["KPM", "RAPP.SPECIAL_EVENTS"], "tags": ["special-event"], "provenance": "docs/RAPP_USE_CASES.md#E16", "notes": "Temporary event profile with revert."},
    {"id": "fair_boost_vs_night_saving", "intent": "Boost the cells around the fairground for the weekend fair, even though the night energy-saving policy normally switches some of them off.", "category": "capacity", "expected_workflow": ["KPM", "RAPP.SPECIAL_EVENTS"], "tags": ["special-event", "conflict-scope"], "provenance": "docs/RAPP_USE_CASES.md#E16", "notes": "Event profile and cell sleep are declared conflicting; energy saving must not be composed."},
    {"id": "ue_link_quality_snapshot", "intent": "Show me the per-user channel quality, MCS and block error rate on the gNB right now.", "category": "observability", "expected_workflow": ["MAC"], "tags": ["mac", "monitor"], "provenance": "docs/RAPP_USE_CASES.md#E17", "notes": "Per-UE scheduler/link statistics come from the MAC service model; KPM has no CQI/MCS/BLER (extra KPM allowed)."},
    {"id": "bearer_buffer_buildup", "intent": "Are the radio bearers building up RLC buffers or retransmitting a lot at the moment?", "category": "observability", "expected_workflow": ["RLC"], "tags": ["rlc", "monitor"], "provenance": "docs/RAPP_USE_CASES.md#E18", "notes": "RLC buffer occupancy / retransmissions per bearer."},
    {"id": "pdcp_discard_check", "intent": "Report per-bearer PDCP traffic volume and how many packets are being discarded or arrive out of order.", "category": "observability", "expected_workflow": ["PDCP"], "tags": ["pdcp", "monitor"], "provenance": "docs/RAPP_USE_CASES.md#E19", "notes": "PDCP bearer statistics."},
    {"id": "n3_tunnel_inventory", "intent": "List which UEs currently have an active N3 user-plane tunnel and which QoS flow each one carries.", "category": "observability", "expected_workflow": ["GTP"], "tags": ["gtp", "monitor"], "provenance": "docs/RAPP_USE_CASES.md#E20", "notes": "GTP-U tunnel table (TEIDs, QFI) from the GTP service model."},
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
        entry = {k: v for k, v in item.items() if k != "label_rule"}  # re-derived below for the v2 labels
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
    for item in DIRECTORY_EXTENSION_INTENTS:
        entry = {k: v for k, v in item.items() if k != "provenance"}
        entry["open_world"] = True
        entry["split"] = "unseen_capability"
        entry["expected_workflow_id"] = "custom:" + "-".join(step.lower() for step in entry["expected_workflow"])
        entry["expects_conflict"] = False
        entry.setdefault("accepted_workflows", [list(entry["expected_workflow"])])
        entry["provenance"] = item["provenance"]
        out.append(entry)
    # Pre-registered label rule (evaluation/label_rules.py), derived from the labels + Agent Cards.
    from evaluation.build_label_rules import annotate, dump
    from evaluation.label_rules import build_registry

    out = annotate(out, build_registry(rapp_directory=True))
    path = HERE / "intents_v2.json"
    path.write_text(dump(out, "indent2"), encoding="utf-8")
    splits: Dict[str, int] = {}
    for entry in out:
        splits[entry["split"]] = splits.get(entry["split"], 0) + 1
    print(f"wrote {path} with {len(out)} intents: {splits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
