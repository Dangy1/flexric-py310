#!/usr/bin/env python3
"""Generate the rApp Directory catalog (`rapps/catalog.json`).

The directory mirrors the shape of a commercial rApp marketplace (solution
areas: Network Evolution, Network Deployment, Network Optimization, Network
Healing, Automation & AI Foundation) and the O-RAN WG1 use cases. Every rApp
is *emulated*: its tools are served by `rapps/runtime.py` against live KPM
from the RIC (or the simulator), and its control decisions are pushed as A1
policies / RC requests through the existing xApps. The catalog therefore
tests discovery and composition at realistic registry sizes without
pretending the rApps are production software.

Distractors are generated on purpose so that discovery is a real search
problem: vendor variants of the same function, deprecated versions, and
cards whose control scope collides with another candidate.

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
        "family": "energy_saving", "area": "Network Optimization", "use_case": "O-RAN UC21 cell switch on/off energy saving",
        "name": "Cell Sleep Energy Saver", "variants": 3, "timescale_s": 60,
        "capabilities": ["energy_saving", "cell_switch_off", "carrier_shutdown"],
        "interfaces": ["A1-P policy-type 20008", "E2SM-RC v1.03", "O1"],
        "consumes": ["RRU.PrbTotDl", "RRU.PrbTotUl", "DRB.UEThpDl"], "produces": ["es.cell_state", "es.energy_kwh_estimate"],
        "control": [("cell", "write", "cell_power")], "requires": ["kpi_monitoring"], "conflicts_with": ["capacity_boost"],
        "tools": [("recommend_sleep_cells", "Rank cells for deep sleep from PRB utilisation."), ("apply_cell_sleep", "Switch the selected cells off via RC and confirm."), ("wake_cells", "Restore switched-off cells.")],
    },
    {
        "family": "traffic_steering", "area": "Network Optimization", "use_case": "O-RAN UC1 traffic steering",
        "name": "Traffic Steering", "variants": 3, "timescale_s": 10,
        "capabilities": ["traffic_steering", "load_balancing", "handover_policy"],
        "interfaces": ["A1-P policy-type 20000", "E2SM-RC v1.03", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl"], "produces": ["ts.ue_steering_policy"],
        "control": [("ue", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": ["cell_power"],
        "tools": [("compute_steering_targets", "Pick target cells for load-balancing handovers."), ("apply_steering_policy", "Push an A1 traffic-steering policy."), ("rollback_steering", "Withdraw the policy.")],
    },
    {
        "family": "qoe_prediction", "area": "Automation and AI Foundation", "use_case": "O-RAN UC2 QoE optimisation",
        "name": "QoE Predictor", "variants": 3, "timescale_s": 5,
        "capabilities": ["qoe_prediction", "mos_estimation", "at_risk_ue_detection"],
        "interfaces": ["E2SM-KPM v3.00", "A1-EI enrichment"],
        "consumes": ["DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["qoe.mos_forecast", "qoe.at_risk_ues"],
        "control": [("ue", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("predict_qoe", "Forecast per-cell MOS and at-risk UE count from KPM."), ("explain_qoe_bottleneck", "Attribute predicted QoE loss to radio, transport or scheduling.")],
    },
    {
        "family": "mobility_optimization", "area": "Network Optimization", "use_case": "Mobility robustness optimisation (MRO)",
        "name": "Mobility Robustness Optimizer", "variants": 2, "timescale_s": 30,
        "capabilities": ["mobility_optimization", "handover_tuning", "ping_pong_mitigation"],
        "interfaces": ["A1-P policy-type 20001", "E2SM-RC v1.03"],
        "consumes": ["RRC.HO_attempts", "RRC.HO_failures"], "produces": ["mro.ho_margin_policy"],
        "control": [("cell", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_ping_pong", "Find cells with oscillating handovers."), ("tune_handover_margins", "Adjust A3 offset / TTT per cell pair."), ("rollback_margins", "Restore previous margins.")],
    },
    {
        "family": "ret_tilt", "area": "Network Optimization", "use_case": "Coverage & capacity optimisation (RET)",
        "name": "Remote Electrical Tilt Optimizer", "variants": 2, "timescale_s": 300,
        "capabilities": ["coverage_optimization", "antenna_tilt", "capacity_boost"],
        "interfaces": ["O1", "E2SM-CCC v6.00"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["ret.tilt_plan"],
        "control": [("cell", "write", "antenna_config")], "requires": ["kpi_monitoring"], "conflicts_with": ["cell_power"],
        "tools": [("propose_tilt_changes", "Propose per-cell tilt deltas."), ("apply_tilt", "Apply tilt via O1/CCC.")],
    },
    {
        "family": "root_cause", "area": "Network Healing", "use_case": "Root cause analysis",
        "name": "Root Cause Analyzer", "variants": 2, "timescale_s": 60,
        "capabilities": ["root_cause_analysis", "anomaly_attribution", "fault_correlation"],
        "interfaces": ["E2SM-KPM v3.00", "O1 alarms"],
        "consumes": ["RRU.PrbTotDl", "DRB.RlcSduDelayDl", "RLC.queue_stats"], "produces": ["rca.report"],
        "control": [("node", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("diagnose_degradation", "Correlate KPI drops with recent control actions and alarms."), ("rank_hypotheses", "Order likely causes with confidence.")],
    },
    {
        "family": "anomaly_detection", "area": "Network Healing", "use_case": "KPI anomaly detection",
        "name": "KPI Anomaly Detector", "variants": 3, "timescale_s": 5,
        "capabilities": ["anomaly_detection", "kpi_baselining", "alerting"],
        "interfaces": ["E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["ad.anomaly_events"],
        "control": [("cell", "read", "")], "requires": [], "conflicts_with": [],
        "tools": [("detect_anomalies", "Flag KPI series that leave their learned baseline."), ("summarize_anomalies", "Group anomalies per cell/slice.")],
    },
    {
        "family": "slice_sla", "area": "Network Optimization", "use_case": "O-RAN UC3 slice SLA assurance",
        "name": "Slice SLA Assurance", "variants": 2, "timescale_s": 10,
        "capabilities": ["slice_assurance", "sla_monitoring", "slice_reconfiguration"],
        "interfaces": ["A1-P policy-type 20010", "E2SM-SLICE (FlexRIC custom)", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "slice.policy"], "produces": ["sla.violation_report", "sla.slice_target"],
        "control": [("slice", "write", "slice_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("evaluate_sla", "Compare per-slice KPIs with SLA targets."), ("recommend_slice_targets", "Compute new PRB reservations."), ("apply_slice_targets", "Push the targets through the slice xApp.")],
    },
    {
        "family": "capacity_mgmt", "area": "Network Deployment", "use_case": "Site capacity management",
        "name": "Site Capacity Manager", "variants": 2, "timescale_s": 3600,
        "capabilities": ["capacity_planning", "capacity_boost", "carrier_add"],
        "interfaces": ["O1", "A1-P policy-type 20020"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["cap.forecast", "cap.expansion_plan"],
        "control": [("node", "write", "cell_power")], "requires": ["kpi_monitoring"], "conflicts_with": ["energy_saving"],
        "tools": [("forecast_capacity", "Forecast PRB headroom per site."), ("plan_carrier_add", "Recommend carrier/cell activation.")],
    },
    {
        "family": "pm_kpi", "area": "Automation and AI Foundation", "use_case": "Performance management and KPI reporting",
        "name": "KPI Manager", "variants": 2, "timescale_s": 60,
        "capabilities": ["kpi_reporting", "pm_collection", "sla_evidence"],
        "interfaces": ["O1 PM", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "RRU.PrbTotUl", "DRB.UEThpDl", "DRB.RlcSduDelayDl"], "produces": ["pm.report", "kpi.aggregates"],
        "control": [("node", "read", "")], "requires": [], "conflicts_with": [],
        "tools": [("build_kpi_report", "Aggregate KPM into a PM report."), ("export_sla_evidence", "Package KPI evidence for an SLA window.")],
    },
    {
        "family": "interference", "area": "Network Healing", "use_case": "Interference management",
        "name": "Interference Mitigator", "variants": 2, "timescale_s": 30,
        "capabilities": ["interference_mitigation", "pci_optimization", "power_control_policy"],
        "interfaces": ["E2SM-RC v1.03", "O1"],
        "consumes": ["RRU.PrbTotDl", "CARR.SINR_dist"], "produces": ["im.power_policy"],
        "control": [("cell", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_interference", "Locate cells with SINR collapse under low load."), ("apply_power_policy", "Push a per-cell power cap.")],
    },
    {
        "family": "transport_qos", "area": "Network Optimization", "use_case": "Transport / backhaul QoS",
        "name": "Transport QoS Advisor", "variants": 2, "timescale_s": 10,
        "capabilities": ["transport_qos", "backhaul_monitoring", "queue_policy_recommendation"],
        "interfaces": ["E2SM-TC (FlexRIC custom)", "O1"],
        "consumes": ["RLC.queue_stats", "DRB.RlcSduDelayDl"], "produces": ["tq.queue_policy"],
        "control": [("transport", "write", "tc_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("recommend_queue_policy", "Choose CoDel/ECN/shaping per bearer class."), ("apply_queue_policy", "Apply through the TC xApp.")],
    },
    {
        "family": "ran_lifecycle", "area": "Network Deployment", "use_case": "RAN lifecycle orchestration",
        "name": "RAN Lifecycle Orchestrator", "variants": 1, "timescale_s": 3600,
        "capabilities": ["lifecycle_management", "config_rollout", "software_upgrade"],
        "interfaces": ["O1", "O2"],
        "consumes": [], "produces": ["lcm.change_plan"],
        "control": [("node", "write", "node_config")], "requires": [], "conflicts_with": ["cell_power", "antenna_config"],
        "tools": [("plan_rollout", "Plan a configuration rollout with maintenance windows."), ("execute_rollout", "Execute a planned change.")],
    },
    {
        "family": "ue_qos_control", "area": "Network Optimization", "use_case": "Per-UE QoS / priority control",
        "name": "QoS Priority Controller", "variants": 2, "timescale_s": 1,
        "capabilities": ["qos_control", "scheduling_priority", "edge_user_protection"],
        "interfaces": ["E2SM-RC v1.03"],
        "consumes": ["qoe.at_risk_ues", "DRB.UEThpDl"], "produces": ["qos.priority_policy"],
        "control": [("ue", "write", "rc_control")], "requires": ["qoe_prediction"], "conflicts_with": [],
        "tools": [("set_priority", "Raise scheduler priority for listed UEs."), ("clear_priority", "Reset priorities.")],
    },
    {
        "family": "spectrum_sharing", "area": "Network Evolution", "use_case": "Dynamic spectrum sharing",
        "name": "Spectrum Share Planner", "variants": 1, "timescale_s": 300,
        "capabilities": ["spectrum_sharing", "carrier_reconfiguration"],
        "interfaces": ["E2SM-CCC v6.00", "O1"],
        "consumes": ["RRU.PrbTotDl", "cap.forecast"], "produces": ["dss.carrier_plan"],
        "control": [("cell", "write", "antenna_config")], "requires": ["capacity_planning"], "conflicts_with": ["cell_power"],
        "tools": [("plan_spectrum_split", "Split carriers between RATs/slices."), ("apply_spectrum_plan", "Reconfigure via CCC.")],
    },
    {
        "family": "self_healing", "area": "Network Healing", "use_case": "Cell outage compensation",
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
                "description": f"{family['name']} rApp ({family['use_case']}). Emulated rApp served by rapps/runtime.py; decisions are computed from live KPM and pushed through A1/RC.",
                "capabilities": list(family["capabilities"]),
                "interfaces": list(family["interfaces"]),
                "consumes": list(family["consumes"]),
                "produces": list(family["produces"]),
                "control_scopes": [{"target": t, "mode": m, "resource": r} for t, m, r in family["control"]],
                "timescale_s": family["timescale_s"],
                "requires": list(family["requires"]),
                "conflicts_with": list(family["conflicts_with"]),
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
            deprecated["distractor"] = True
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
