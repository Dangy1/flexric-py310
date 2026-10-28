#!/usr/bin/env python3
"""Generate the rApp Directory catalog (`rapps/catalog.json`).

The directory mirrors the shape of a commercial rApp marketplace (solution
areas: Network Evolution, Network Deployment, Network Optimization, Network
Healing, Automation & AI Foundation) and the O-RAN WG1 use cases. Every rApp
is *emulated*: its tools are served by `rapps/runtime.py` against live KPM
from the RIC (or the simulator); apply tools write an A1-style policy
document that is not enforced on the RAN. The catalog therefore tests
discovery and composition at realistic registry sizes without pretending the
rApps are production software.

Distractors are generated on purpose so that discovery is a real search
problem: vendor variants of the same function, deprecated versions (their
description starts with "DEPRECATED" and names the superseding card), and
cards whose control scope collides with another candidate.

Card text: every description is "<what it does>. Use when <...>. Do not use
when <...>." written from the O-RAN use-case definitions (not from the
benchmark intents), plus the emulation note. `workflow_role` (observe /
analyze / control) is derived from the control scope and capabilities, the
same rule as `evaluation/label_rules.app_role`.

Card review 2026-10-28 (FABLE_REVIEW_AND_PLAN P0-5/P1-6):
  * slice_sla no longer consumes `slice.policy` (only the SLICE xApp, which
    runs after it, produces that), so KPM -> SLICE_SLA -> SLICE is reachable;
    it consumes RAN-provided PRB and delay counters instead.
  * pm_kpi provides `kpi_monitoring` (it reads O1 PM itself), so it can feed
    rApps that require a KPI input.
  * anomaly_detection requires `kpi_monitoring` like every other analytics
    rApp whose only data interface is E2SM-KPM.
  * spectrum_sharing conflicts with `energy_saving` (cells switched off while
    carriers are re-split), not with every `cell_power` writer: it requires
    capacity planning upstream, and capacity_mgmt writes cell_power, so the
    old declaration made its own dependency a conflict.
  * capacity_mgmt declares a write scope, so it gets the matching apply tool
    (`apply_carrier_activation`, appended; tool order otherwise unchanged).

Run:  python rapps/build_catalog.py  (writes catalog.json next to this file)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VENDORS = ["Aalto 6G Lab", "Northwind Radio", "Kestrel Networks", "Orion RAN Software", "Helix Automation", "VTT Research"]

# One entry per O-RAN use-case family. `variants` controls how many vendor
# cards are generated for that family (the first is canonical, the rest are
# distractors). Fields map 1:1 onto AgentCard schema v2.
FAMILIES: List[Dict[str, Any]] = [
    {
        "family": "energy_saving",
        "summary": 'Ranks lightly loaded cells or carriers for sleep, switches them off and restores them when load returns (writes cell_power).',
        "use_when": 'the goal is to cut RAN energy consumption by switching cells or carriers off in low-traffic periods, or to bring sleeping cells back',
        "avoid_when": 'capacity has to be added, coverage reshaped or individual users prioritised; declared conflict with capacity-boost functions', "area": "Network Optimization", "use_case": "O-RAN UC21 cell switch on/off energy saving",
        "name": "Cell Sleep Energy Saver", "variants": 3, "timescale_s": 60,
        "capabilities": ["energy_saving", "cell_switch_off", "carrier_shutdown"],
        "interfaces": ["A1-P policy-type 20008", "E2SM-RC v1.03", "O1"],
        "consumes": ["RRU.PrbTotDl", "RRU.PrbTotUl", "DRB.UEThpDl"], "produces": ["es.cell_state", "es.energy_kwh_estimate"],
        "control": [("cell", "write", "cell_power")], "requires": ["kpi_monitoring"], "conflicts_with": ["capacity_boost"],
        "tools": [("recommend_sleep_cells", "Rank cells for deep sleep from PRB utilisation."), ("apply_cell_sleep", "Switch the selected cells off via RC and confirm."), ("wake_cells", "Restore switched-off cells.")],
    },
    {
        "family": "traffic_steering",
        "summary": 'Computes load-balancing handover targets and pushes a per-UE steering policy (writes UE-level rc_control).',
        "use_when": 'traffic has to be moved between cells or carriers, e.g. offloading a congested cell onto its neighbours',
        "avoid_when": 'the fix is a transport queue policy or a slice reservation; it must not run after a cell_power writer (declared conflict)', "area": "Network Optimization", "use_case": "O-RAN UC1 traffic steering",
        "name": "Traffic Steering", "variants": 3, "timescale_s": 10,
        "capabilities": ["traffic_steering", "load_balancing", "handover_policy"],
        "interfaces": ["A1-P policy-type 20000", "E2SM-RC v1.03", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl"], "produces": ["ts.ue_steering_policy"],
        "control": [("ue", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": ["cell_power"],
        "tools": [("compute_steering_targets", "Pick target cells for load-balancing handovers."), ("apply_steering_policy", "Push an A1 traffic-steering policy."), ("rollback_steering", "Withdraw the policy.")],
    },
    {
        "family": "qoe_prediction",
        "summary": 'Forecasts per-cell MOS from throughput and delay and lists the UEs at risk of poor QoE. Read-only.',
        "use_when": 'user-perceived quality (QoE/MOS) has to be estimated or forecast, or at-risk users identified before acting',
        "avoid_when": 'a control action is all that is needed; it never changes RAN state', "area": "Automation and AI Foundation", "use_case": "O-RAN UC2 QoE optimisation",
        "name": "QoE Predictor", "variants": 3, "timescale_s": 5,
        "capabilities": ["qoe_prediction", "mos_estimation", "at_risk_ue_detection"],
        "interfaces": ["E2SM-KPM v3.00", "A1-EI enrichment"],
        "consumes": ["DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["qoe.mos_forecast", "qoe.at_risk_ues"],
        "control": [("ue", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("predict_qoe", "Forecast per-cell MOS and at-risk UE count from KPM."), ("explain_qoe_bottleneck", "Attribute predicted QoE loss to radio, transport or scheduling.")],
    },
    {
        "family": "mobility_optimization",
        "summary": 'Detects handover oscillation and tunes A3 offset / time-to-trigger per cell pair (writes cell-level rc_control).',
        "use_when": 'handover failures or too-early, too-late or oscillating handovers have to be reduced by changing handover parameters',
        "avoid_when": 'the problem is load imbalance between cells (traffic steering) or transport delay', "area": "Network Optimization", "use_case": "Mobility robustness optimisation (MRO)",
        "name": "Mobility Robustness Optimizer", "variants": 2, "timescale_s": 30,
        "capabilities": ["mobility_optimization", "handover_tuning", "ping_pong_mitigation"],
        "interfaces": ["A1-P policy-type 20001", "E2SM-RC v1.03"],
        "consumes": ["RRC.HO_attempts", "RRC.HO_failures"], "produces": ["mro.ho_margin_policy"],
        "control": [("cell", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_ping_pong", "Find cells with oscillating handovers."), ("tune_handover_margins", "Adjust A3 offset / TTT per cell pair."), ("rollback_margins", "Restore previous margins.")],
    },
    {
        "family": "ret_tilt",
        "summary": 'Proposes and applies remote electrical tilt changes to reshape coverage and capacity (writes antenna_config).',
        "use_when": 'coverage holes, overshooting or weak cell-edge coverage have to be fixed by changing antenna tilt',
        "avoid_when": 'the problem is load, energy or transport; declared conflict with cell_power writers', "area": "Network Optimization", "use_case": "Coverage & capacity optimisation (RET)",
        "name": "Remote Electrical Tilt Optimizer", "variants": 2, "timescale_s": 300,
        "capabilities": ["coverage_optimization", "antenna_tilt", "capacity_boost"],
        "interfaces": ["O1", "E2SM-CCC v6.00"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["ret.tilt_plan"],
        "control": [("cell", "write", "antenna_config")], "requires": ["kpi_monitoring"], "conflicts_with": ["cell_power"],
        "tools": [("propose_tilt_changes", "Propose per-cell tilt deltas."), ("apply_tilt", "Apply tilt via O1/CCC.")],
    },
    {
        "family": "root_cause",
        "summary": 'Correlates KPI degradations with recent control actions and alarms and ranks likely causes. Read-only.',
        "use_when": 'the goal is to explain why a KPI degraded or a fault occurred, before or instead of acting',
        "avoid_when": 'the cause is already known and only a control action is needed', "area": "Network Healing", "use_case": "Root cause analysis",
        "name": "Root Cause Analyzer", "variants": 2, "timescale_s": 60,
        "capabilities": ["root_cause_analysis", "anomaly_attribution", "fault_correlation"],
        "interfaces": ["E2SM-KPM v3.00", "O1 alarms"],
        "consumes": ["RRU.PrbTotDl", "DRB.RlcSduDelayDl", "RLC.queue_stats"], "produces": ["rca.report"],
        "control": [("node", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("diagnose_degradation", "Correlate KPI drops with recent control actions and alarms."), ("rank_hypotheses", "Order likely causes with confidence.")],
    },
    {
        "family": "anomaly_detection",
        "summary": 'Learns per-cell KPI baselines from KPM and flags series that leave them. Read-only.',
        "use_when": 'deviations from normal KPI behaviour have to be detected, flagged or summarised',
        "avoid_when": 'the cause has to be explained (root cause analysis) or a control applied; it never changes RAN state', "area": "Network Healing", "use_case": "KPI anomaly detection",
        "name": "KPI Anomaly Detector", "variants": 3, "timescale_s": 5,
        "capabilities": ["anomaly_detection", "kpi_baselining", "alerting"],
        "interfaces": ["E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["ad.anomaly_events"],
        "control": [("cell", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_anomalies", "Flag KPI series that leave their learned baseline."), ("summarize_anomalies", "Group anomalies per cell/slice.")],
    },
    {
        "family": "slice_sla",
        "summary": 'Compares per-slice KPIs with SLA targets and recomputes PRB reservations, applied through the SLICE xApp (writes slice_control).',
        "use_when": 'a slice violates or is about to violate its SLA and its resource reservation has to be recomputed',
        "avoid_when": 'only an SLA evidence report is needed, or no slice is involved', "area": "Network Optimization", "use_case": "O-RAN UC3 slice SLA assurance",
        "name": "Slice SLA Assurance", "variants": 2, "timescale_s": 10,
        "capabilities": ["slice_assurance", "sla_monitoring", "slice_reconfiguration"],
        "interfaces": ["A1-P policy-type 20010", "E2SM-SLICE (FlexRIC custom)", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.RlcSduDelayDl"], "produces": ["sla.violation_report", "sla.slice_target"],
        "control": [("slice", "write", "slice_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("evaluate_sla", "Compare per-slice KPIs with SLA targets."), ("recommend_slice_targets", "Compute new PRB reservations."), ("apply_slice_targets", "Push the targets through the slice xApp.")],
    },
    {
        "family": "capacity_mgmt",
        "summary": 'Forecasts PRB headroom per site and plans and activates additional carriers or cells (writes cell_power).',
        "use_when": 'the goal is capacity planning: headroom forecasts, site expansion or carrier-add decisions',
        "avoid_when": 'the goal is to save energy (declared conflict with energy saving) or a near-real-time fix', "area": "Network Deployment", "use_case": "Site capacity management",
        "name": "Site Capacity Manager", "variants": 2, "timescale_s": 3600,
        "capabilities": ["capacity_planning", "capacity_boost", "carrier_add"],
        "interfaces": ["O1", "A1-P policy-type 20020"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["cap.forecast", "cap.expansion_plan"],
        "control": [("node", "write", "cell_power")], "requires": ["kpi_monitoring"], "conflicts_with": ["energy_saving"],
        "tools": [("forecast_capacity", "Forecast PRB headroom per site."), ("plan_carrier_add", "Recommend carrier/cell activation."), ("apply_carrier_activation", "Activate the planned carriers/cells via O1 and confirm.")],
    },
    {
        "family": "pm_kpi",
        "summary": 'Aggregates O1 PM and KPM counters into KPI reports and SLA evidence packages; reads PM itself, so it can serve as the KPI input of other rApps. Read-only.',
        "use_when": 'a periodic KPI/performance report or SLA evidence package is requested, or KPI aggregates are needed as input',
        "avoid_when": 'a control decision or a forecast is needed', "area": "Automation and AI Foundation", "use_case": "Performance management and KPI reporting",
        "name": "KPI Manager", "variants": 2, "timescale_s": 60,
        "capabilities": ["kpi_reporting", "pm_collection", "sla_evidence", "kpi_monitoring"],
        "interfaces": ["O1 PM", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "RRU.PrbTotUl", "DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["pm.report", "kpi.aggregates"],
        "control": [("node", "read", "")], "requires": [], "conflicts_with": [],
        "tools": [("build_kpi_report", "Aggregate KPM into a PM report."), ("export_sla_evidence", "Package KPI evidence for an SLA window.")],
    },
    {
        "family": "interference",
        "summary": 'Locates cells whose SINR collapses under low load and applies per-cell power caps (writes cell-level rc_control).',
        "use_when": 'interference, SINR degradation or PCI clashes have to be mitigated',
        "avoid_when": 'the degradation is caused by load or congestion rather than interference', "area": "Network Healing", "use_case": "Interference management",
        "name": "Interference Mitigator", "variants": 2, "timescale_s": 30,
        "capabilities": ["interference_mitigation", "pci_optimization", "power_control_policy"],
        "interfaces": ["E2SM-RC v1.03", "O1"],
        "consumes": ["RRU.PrbTotDl", "CARR.SINR_dist"], "produces": ["im.power_policy"],
        "control": [("cell", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_interference", "Locate cells with SINR collapse under low load."), ("apply_power_policy", "Push a per-cell power cap.")],
    },
    {
        "family": "transport_qos",
        "summary": 'Recommends a queue policy per bearer class (CoDel, ECN, shaping); enforcement is performed by the TC xApp (writes tc_control).',
        "use_when": 'a transport/backhaul queue policy has to be chosen per traffic class before it is enforced',
        "avoid_when": 'a queue policy is already known and only has to be enforced, or the problem is in the radio domain', "area": "Network Optimization", "use_case": "Transport / backhaul QoS",
        "name": "Transport QoS Advisor", "variants": 2, "timescale_s": 10,
        "capabilities": ["transport_qos", "backhaul_monitoring", "queue_policy_recommendation"],
        "interfaces": ["E2SM-TC (FlexRIC custom)", "O1"],
        "consumes": ["RLC.queue_stats", "DRB.RlcSduDelayDl"], "produces": ["tq.queue_policy"],
        "control": [("transport", "write", "tc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("recommend_queue_policy", "Choose CoDel/ECN/shaping per bearer class."), ("apply_queue_policy", "Apply through the TC xApp.")],
    },
    {
        "family": "ran_lifecycle",
        "summary": 'Plans and executes configuration or software rollouts within maintenance windows (writes node_config).',
        "use_when": 'configuration or software has to be rolled out, staged or upgraded across sites',
        "avoid_when": 'a closed-loop KPI optimisation is needed; declared conflict with cell_power and antenna_config writers', "area": "Network Deployment", "use_case": "RAN lifecycle orchestration",
        "name": "RAN Lifecycle Orchestrator", "variants": 1, "timescale_s": 3600,
        "capabilities": ["lifecycle_management", "config_rollout", "software_upgrade"],
        "interfaces": ["O1", "O2"],
        "consumes": [], "produces": ["lcm.change_plan"],
        "control": [("node", "write", "node_config")], "requires": [], "conflicts_with": ["cell_power", "antenna_config"],
        "tools": [("plan_rollout", "Plan a configuration rollout with maintenance windows."), ("execute_rollout", "Execute a planned change.")],
    },
    {
        "family": "ue_qos_control",
        "summary": 'Raises or resets scheduler priority for selected UEs (writes UE-level rc_control); needs the at-risk UE list from a QoE predictor upstream.',
        "use_when": 'specific users or user groups need higher scheduling priority or protection',
        "avoid_when": 'a whole slice needs more resources (slice control) or no at-risk UE list is available', "area": "Network Optimization", "use_case": "Per-UE QoS / priority control",
        "name": "QoS Priority Controller", "variants": 2, "timescale_s": 1,
        "capabilities": ["qos_control", "scheduling_priority", "edge_user_protection"],
        "interfaces": ["E2SM-RC v1.03"],
        "consumes": ["qoe.at_risk_ues", "DRB.UEThpDl"], "produces": ["qos.priority_policy"],
        "control": [("ue", "write", "rc_control")], "requires": ["qoe_prediction"], "conflicts_with": [],
        "tools": [("set_priority", "Raise scheduler priority for listed UEs."), ("clear_priority", "Reset priorities.")],
    },
    {
        "family": "spectrum_sharing",
        "summary": 'Splits shared carriers between RATs or slices from a capacity forecast and reconfigures them via CCC (writes antenna_config); needs capacity planning upstream.',
        "use_when": 'spectrum or carrier shares have to be re-split between RATs or slices',
        "avoid_when": 'energy saving is switching cells off at the same time (declared conflict)', "area": "Network Evolution", "use_case": "Dynamic spectrum sharing",
        "name": "Spectrum Share Planner", "variants": 1, "timescale_s": 300,
        "capabilities": ["spectrum_sharing", "carrier_reconfiguration"],
        "interfaces": ["E2SM-CCC v6.00", "O1"],
        "consumes": ["RRU.PrbTotDl", "cap.forecast"], "produces": ["dss.carrier_plan"],
        "control": [("cell", "write", "antenna_config")], "requires": ["capacity_planning"], "conflicts_with": ["energy_saving"],
        "tools": [("plan_spectrum_split", "Split carriers between RATs/slices."), ("apply_spectrum_plan", "Reconfigure via CCC.")],
    },
    {
        "family": "self_healing",
        "summary": 'Compensates a failed or degraded cell by adjusting neighbour power and tilt (writes cell-level rc_control); needs root-cause evidence upstream.',
        "use_when": 'a cell outage or severe degradation has to be compensated by its neighbours',
        "avoid_when": 'the cause has not been diagnosed yet; declared conflict with cell_power writers', "area": "Network Healing", "use_case": "Cell outage compensation",
        "name": "Outage Compensator", "variants": 1, "timescale_s": 60,
        "capabilities": ["outage_compensation", "neighbour_power_boost", "self_healing"],
        "interfaces": ["E2SM-RC v1.03", "O1 alarms"],
        "consumes": ["rca.report", "RRU.PrbTotDl"], "produces": ["coc.compensation_plan"],
        "control": [("cell", "write", "rc_control")], "requires": ["root_cause_analysis"], "conflicts_with": ["cell_power"],
        "tools": [("plan_compensation", "Pick neighbours to absorb a failed cell."), ("apply_compensation", "Apply power/tilt changes to neighbours.")],
    },
]


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


EMULATION_NOTE = ("Emulated rApp served by rapps/runtime.py: decisions are simple estimators over live KPM; apply tools write an "
                  "A1-style policy document that is not enforced on the RAN.")


def workflow_role(family: Dict[str, Any]) -> str:
    """Declared workflow role, derived from scope and capabilities (same rule as evaluation/label_rules.app_role)."""
    if any(mode == "write" for _, mode, _ in family["control"]):
        return "control"
    return "observe" if "kpi_monitoring" in family["capabilities"] else "analyze"


def describe(family: Dict[str, Any], vendor: str, canonical: bool) -> str:
    who = f"{family['name']} rApp" if canonical else f"{vendor} implementation of the {family['name']} rApp"
    return (f"{who} ({family['use_case']}). {family['summary']} Use when {family['use_when']}. "
            f"Do not use when {family['avoid_when']}. {EMULATION_NOTE}")


def build_catalog() -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    for family in FAMILIES:
        for variant in range(int(family["variants"])):
            vendor = VENDORS[variant % len(VENDORS)]
            canonical = variant == 0
            rapp_id = f"rapp.{family['family']}" if canonical else f"rapp.{family['family']}.{_slug(vendor.split()[0])}"
            status = "active"
            version = "2.1.0" if canonical else f"1.{variant}.0"
            notes = []
            if not canonical:
                notes.append(f"Vendor variant of {family['name']}; same capability family, different tool names.")
            entry = {
                "id": rapp_id,
                "name": family["name"] if canonical else f"{vendor.split()[0]} {family['name']}",
                "vendor": vendor,
                "version": version,
                "status": status,
                "family": family["family"],
                "solution_area": family["area"],
                "use_case": family["use_case"],
                "description": describe(family, vendor, canonical),
                "capabilities": list(family["capabilities"]),
                "interfaces": list(family["interfaces"]),
                "consumes": list(family["consumes"]),
                "produces": list(family["produces"]),
                "control_scopes": [{"target": t, "mode": m, "resource": r} for t, m, r in family["control"]],
                "timescale_s": family["timescale_s"],
                "requires": list(family["requires"]),
                "conflicts_with": list(family["conflicts_with"]),
                "workflow_role": workflow_role(family),
                "tools": [
                    {"id": tool_id if canonical else f"{_slug(vendor.split()[0])}_{tool_id}", "label": tool_id.replace("_", " ").title(), "description": description}
                    for tool_id, description in family["tools"]
                ],
                "distractor": not canonical,
                "notes": notes,
            }
            catalog.append(entry)
        # One deprecated release per family with >1 variant: a card that must
        # not be selected even though its description matches the intent.
        if int(family["variants"]) > 1:
            deprecated = dict(catalog[-int(family["variants"])])
            deprecated = json.loads(json.dumps(deprecated))
            deprecated["id"] = f"rapp.{family['family']}.v0"
            deprecated["name"] = f"{family['name']} (legacy)"
            deprecated["version"] = "0.9.0"
            deprecated["status"] = "deprecated"
            deprecated["superseded_by"] = f"rapp.{family['family']}"
            deprecated["distractor"] = True
            deprecated["description"] = (f"DEPRECATED release 0.9.0 of the {family['name']} rApp, superseded by "
                                         f"rapp.{family['family']} 2.1.0 and kept in the directory for migration only. Do not "
                                         f"select it for new workflows: its tools are refused at run time. "
                                         + describe(family, VENDORS[0], True))
            deprecated["notes"] = ["Deprecated release kept in the directory for migration; superseded by the 2.x card."]
            catalog.append(deprecated)
    return catalog


def main() -> int:
    catalog = build_catalog()
    out = Path(__file__).resolve().parent / "catalog.json"
    out.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    areas: Dict[str, int] = {}
    for entry in catalog:
        areas[entry["solution_area"]] = areas.get(entry["solution_area"], 0) + 1
    active = sum(1 for e in catalog if e["status"] == "active")
    canonical = sum(1 for e in catalog if not e["distractor"])
    print(f"wrote {out} with {len(catalog)} rApps ({canonical} canonical, {len(catalog) - canonical} distractors, {active} active) across {len(areas)} solution areas: {areas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
