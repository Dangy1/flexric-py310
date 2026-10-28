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

Directory extension 2026-10-28 (workstream E, docs/RAPP_USE_CASES.md):
  * 16 further families (ANR, PCI, sleeping cell, CIO load balancing, RACH,
    beamforming, MIMO sleep, traffic forecast, fault prediction, slice
    admission, signalling storm, UL interference, EN-DC steering, config
    audit, crossed feeder, special events), appended after the originals so
    the original cards keep their order; 5 of them get a vendor variant and
    a deprecated release.
  * Disambiguation clauses added to the "Do not use when" text of
    traffic_steering, energy_saving, ret_tilt, capacity_mgmt and
    interference; interference drops PCI from its use-when and its
    `pci_optimization` capability becomes `sinr_recovery` (PCI has its own
    family now); mobility_optimization declares `cio_load_balancing`
    conflicting (MRO and LBO update the same handover trigger, TS 28.313).

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
        "avoid_when": 'capacity has to be added, coverage reshaped or individual users prioritised, or the cell must stay on and only MIMO layers / RF channels are to be muted (MIMO sleep); declared conflict with capacity-boost functions', "area": "Network Optimization", "use_case": "O-RAN UC21 cell switch on/off energy saving",
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
        "avoid_when": 'the fix is a transport queue policy or a slice reservation, or the load balance should be shifted for all users by changing cell-level handover offsets (mobility load balancing); it must not run after a cell_power writer (declared conflict)', "area": "Network Optimization", "use_case": "O-RAN UC1 traffic steering",
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
        "avoid_when": 'the problem is load imbalance between cells (traffic steering or mobility load balancing) or transport delay; declared conflict with cell-offset load balancing, which tunes the same handover triggers', "area": "Network Optimization", "use_case": "Mobility robustness optimisation (MRO)",
        "name": "Mobility Robustness Optimizer", "variants": 2, "timescale_s": 30,
        "capabilities": ["mobility_optimization", "handover_tuning", "ping_pong_mitigation"],
        "interfaces": ["A1-P policy-type 20001", "E2SM-RC v1.03"],
        "consumes": ["RRC.HO_attempts", "RRC.HO_failures"], "produces": ["mro.ho_margin_policy"],
        "control": [("cell", "write", "rc_control")], "requires": ["kpi_monitoring"], "conflicts_with": ["cio_load_balancing"],
        "tools": [("detect_ping_pong", "Find cells with oscillating handovers."), ("tune_handover_margins", "Adjust A3 offset / TTT per cell pair."), ("rollback_margins", "Restore previous margins.")],
    },
    {
        "family": "ret_tilt",
        "summary": 'Proposes and applies remote electrical tilt changes to reshape coverage and capacity (writes antenna_config).',
        "use_when": 'coverage holes, overshooting or weak cell-edge coverage have to be fixed by changing antenna tilt',
        "avoid_when": 'the problem is load, energy or transport, or the beam pattern of a massive-MIMO cell is to be optimised (beamforming optimisation); declared conflict with cell_power writers', "area": "Network Optimization", "use_case": "Coverage & capacity optimisation (RET)",
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
        "avoid_when": 'the goal is to save energy (declared conflict with energy saving), a near-real-time fix, or only a short-term traffic/load forecast is needed (traffic forecasting)', "area": "Network Deployment", "use_case": "Site capacity management",
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
        "use_when": 'downlink interference or SINR degradation has to be mitigated by capping cell transmit power',
        "avoid_when": 'the degradation is caused by load or congestion rather than interference, the problem is a PCI collision or confusion (PCI optimisation), or the interference is in the uplink (uplink power control)', "area": "Network Healing", "use_case": "Interference management",
        "name": "Interference Mitigator", "variants": 2, "timescale_s": 30,
        "capabilities": ["interference_mitigation", "sinr_recovery", "power_control_policy"],
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


# ---------------------------------------------------------------------------
# Directory extension 2026-10-28 (workstream E): sixteen further families, each
# modelled on a publicly documented rApp/xApp use case or 3GPP SON function
# (provenance per family in docs/RAPP_USE_CASES.md; real vendor names appear
# only there, card vendors stay fictional). Appended after the original
# families so the original cards keep their order in catalog.json.
# ---------------------------------------------------------------------------
FAMILIES += [
    {
        "family": "anr",
        "summary": 'Finds missing or unused neighbour relations from UE measurement reports and handover statistics and adds, removes or blocklists them (writes neighbour_relations).',
        "use_when": 'neighbour cell relations have to be created, cleaned up or blocklisted, e.g. missing neighbours after a new cell or carrier is integrated or handovers to an undeclared neighbour fail',
        "avoid_when": 'the handover parameters (offsets, time-to-trigger) are the problem (mobility robustness), or two cells share a PCI (PCI optimisation)', "area": "Network Deployment", "use_case": "Automatic Neighbour Relation management (3GPP ANR, O-RAN UC19 SON)",
        "name": "Neighbour Relation Manager", "variants": 2, "timescale_s": 900,
        "capabilities": ["neighbour_relation_management", "anr", "neighbour_blocklisting"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRC.HO_attempts", "RRC.HO_failures"], "produces": ["anr.neighbour_changes"],
        "control": [("cell", "write", "neighbour_relations")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_missing_neighbours", "List candidate neighbour relations to add or remove per cell."), ("apply_neighbour_relations", "Create or delete the neighbour relations via O1 and confirm."), ("apply_neighbour_blocklist", "Blocklist a neighbour relation for handover.")],
    },
    {
        "family": "pci_optimization",
        "summary": 'Detects PCI collisions and confusions between neighbouring cells and reassigns physical cell identities (writes pci_config).',
        "use_when": 'two cells that are neighbours, or neighbours of a common cell, share a physical cell identity (PCI collision or confusion), or a new site needs a clash-free PCI',
        "avoid_when": 'the interference is caused by transmit power or load rather than identity clashes (interference mitigation), or neighbour lists are missing (neighbour relation management)', "area": "Network Optimization", "use_case": "PCI conflict detection and resolution (3GPP TS 28.313 PCI configuration, O-RAN UC19 SON)",
        "name": "PCI Conflict Resolver", "variants": 2, "timescale_s": 3600,
        "capabilities": ["pci_conflict_resolution", "pci_planning"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRC.HO_failures", "CARR.SINR_dist"], "produces": ["pci.reassignment_plan"],
        "control": [("cell", "write", "pci_config")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_pci_conflicts", "Find PCI collisions and confusions among neighbouring cells."), ("apply_pci_reassignment", "Assign new PCIs via O1 and confirm.")],
    },
    {
        "family": "sleeping_cell",
        "summary": 'Detects sleeping cells: cells that raise no alarm but carry no traffic while their neighbours do. Read-only.',
        "use_when": 'silent cell outages have to be found, i.e. cells that look healthy in fault management but stopped serving users',
        "avoid_when": 'the faulty cell is already known and has to be compensated (outage compensation), or general KPI deviations are to be flagged (KPI anomaly detection); it never changes RAN state', "area": "Network Healing", "use_case": "Sleeping cell / cell outage detection (3GPP TS 32.541 COD)",
        "name": "Sleeping Cell Detector", "variants": 1, "timescale_s": 900,
        "capabilities": ["sleeping_cell_detection", "cell_outage_detection"],
        "interfaces": ["E2SM-KPM v3.00", "O1 alarms"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl", "RRC.ConnMean"], "produces": ["cod.sleeping_cells"],
        "control": [("cell", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_sleeping_cells", "Flag cells with no traffic while neighbours carry load.")],
    },
    {
        "family": "mobility_load_balancing",
        "summary": 'Balances load between neighbouring cells by adjusting cell individual offsets (CIO) / handover triggers for all users of a cell pair, without per-UE handover commands (writes handover_offsets).',
        "use_when": 'a persistent load imbalance between neighbouring cells has to be evened out by moving cell boundaries (cell-level handover offsets) over minutes to hours',
        "avoid_when": 'specific users have to be moved now (per-UE traffic steering), or handover failures / ping-pong are the problem (mobility robustness); declared conflict with handover-margin tuning, which changes the same triggers', "area": "Network Optimization", "use_case": "Mobility load balancing via CIO (3GPP TS 28.313 LBO, O-RAN UC19 MLB)",
        "name": "Cell Offset Load Balancer", "variants": 2, "timescale_s": 900,
        "capabilities": ["cio_load_balancing", "mobility_load_balancing"],
        "interfaces": ["A1-P policy-type 20030", "O1", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "RRU.PrbTotUl", "RRC.ConnMean"], "produces": ["mlb.cio_policy"],
        "control": [("cell", "write", "handover_offsets")], "requires": ["kpi_monitoring"], "conflicts_with": ["handover_tuning"],
        "tools": [("compute_cio_offsets", "Compute per cell-pair CIO deltas from the load imbalance."), ("apply_cio_offsets", "Push the CIO policy and confirm."), ("rollback_cio_offsets", "Restore the previous offsets.")],
    },
    {
        "family": "rach_optimization",
        "summary": 'Tunes random-access parameters (PRACH configuration, root sequence index, zero-correlation zone) to cut RACH collisions and access failures (writes rach_config).',
        "use_when": 'random-access or connection-setup failures, preamble collisions or root-sequence clashes have to be reduced',
        "avoid_when": 'failures happen after access, at handover (mobility robustness), or a surge of connection attempts is a signalling storm to be throttled (signalling storm protection)', "area": "Network Optimization", "use_case": "RACH optimisation (3GPP TS 38.300 15.5.3, TS 28.313)",
        "name": "RACH Optimizer", "variants": 1, "timescale_s": 3600,
        "capabilities": ["rach_optimization", "prach_tuning"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRC.ConnEstabAtt", "RRC.ConnEstabSucc", "RRU.PrbTotUl"], "produces": ["rach.parameter_plan"],
        "control": [("cell", "write", "rach_config")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("analyze_rach_failures", "Rank cells by access failure ratio and suspected cause."), ("apply_rach_parameters", "Apply PRACH / RSI / ZCZ changes via O1 and confirm.")],
    },
    {
        "family": "beamforming",
        "summary": 'Optimises the grid-of-beams pattern (beam azimuth, elevation, width) of massive-MIMO cells to the observed user distribution (writes beam_config).',
        "use_when": 'the beam pattern of massive-MIMO cells has to be adapted to where users are, e.g. high-rise or hotspot users poorly served by the default grid of beams',
        "avoid_when": 'the antenna tilt of a passive antenna is the lever (remote electrical tilt), or MIMO layers are to be muted for energy saving; declared conflict with tilt changes and RF channel muting on the same cells', "area": "Network Optimization", "use_case": "Massive MIMO beamforming / GoB optimisation (O-RAN UC6)",
        "name": "Beam Pattern Optimizer", "variants": 1, "timescale_s": 3600,
        "capabilities": ["beamforming_optimization", "gob_optimization"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "CARR.SINR_dist", "DRB.UEThpDl"], "produces": ["bf.beam_pattern_plan"],
        "control": [("cell", "write", "beam_config")], "requires": ["kpi_monitoring"], "conflicts_with": ["antenna_tilt", "rf_channel_sleep"],
        "tools": [("recommend_beam_pattern", "Choose a grid-of-beams pattern per cell from load and SINR."), ("apply_beam_pattern", "Configure the beam pattern via O1 and confirm.")],
    },
    {
        "family": "mimo_sleep",
        "summary": 'Saves energy at medium load by muting massive-MIMO RF channels / MIMO layers (e.g. 64T64R to 32T32R) while the cell stays on, and restores them when load rises (writes rf_channels).',
        "use_when": 'energy has to be saved on massive-MIMO cells that cannot be switched off because they still carry traffic, by reducing active antennas or MIMO layers',
        "avoid_when": 'whole cells or carriers can be switched off at low load (cell sleep energy saving) or capacity must be boosted; declared conflict with capacity-boost and beam-pattern changes', "area": "Network Optimization", "use_case": "RF channel reconfiguration / MIMO muting energy saving (O-RAN WG1 Network Energy Saving)",
        "name": "MIMO Sleep Controller", "variants": 2, "timescale_s": 300,
        "capabilities": ["rf_channel_sleep", "mimo_layer_muting", "energy_saving_mimo"],
        "interfaces": ["O1", "E2SM-KPM v3.00", "A1-P policy-type 20009"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl"], "produces": ["mimo.rf_channel_state"],
        "control": [("cell", "write", "rf_channels")], "requires": ["kpi_monitoring"], "conflicts_with": ["capacity_boost", "beamforming_optimization"],
        "tools": [("recommend_rf_channel_config", "Pick the active RF channel / layer count per cell."), ("apply_rf_channel_config", "Mute the selected RF channels and confirm."), ("restore_rf_channels", "Re-enable all RF channels.")],
    },
    {
        "family": "traffic_forecast",
        "summary": 'Forecasts per-cell and per-cluster traffic load for the next minutes to hours from KPM history. Read-only.',
        "use_when": 'a short-term traffic or load forecast is needed, alone or as input to another decision such as energy saving or load balancing',
        "avoid_when": 'long-term capacity planning or carrier additions are needed (site capacity management), or a control action is all that is needed; it never changes RAN state', "area": "Automation and AI Foundation", "use_case": "Network traffic / load prediction (3GPP TR 37.817, rApp traffic forecasting)",
        "name": "Traffic Forecaster", "variants": 2, "timescale_s": 900,
        "capabilities": ["traffic_forecasting", "load_prediction"],
        "interfaces": ["E2SM-KPM v3.00", "A1-EI enrichment"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl"], "produces": ["tf.load_forecast"],
        "control": [("cell", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("forecast_load", "Forecast per-cell PRB load and throughput for a horizon."), ("forecast_peak_hours", "List cells and hours where a load peak is expected.")],
    },
    {
        "family": "fault_prediction",
        "summary": 'Predicts imminent RAN hardware or cell faults from PM, power and alarm trends and recommends preventive maintenance. Read-only.',
        "use_when": 'faults have to be anticipated before they happen, e.g. which radios or sites are likely to fail and should get preventive maintenance',
        "avoid_when": 'a fault already happened and has to be explained (root cause analysis) or compensated; it never changes RAN state', "area": "Network Healing", "use_case": "RAN fault prediction / predictive maintenance (3GPP TS 28.104 MDA)",
        "name": "RAN Fault Predictor", "variants": 1, "timescale_s": 3600,
        "capabilities": ["fault_prediction", "predictive_maintenance"],
        "interfaces": ["E2SM-KPM v3.00", "O1 alarms", "O1 PM"],
        "consumes": ["PEE.AvgPower", "PEE.AvgTemperature", "DRB.RlcSduDelayDl"], "produces": ["fp.fault_risk"],
        "control": [("node", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("predict_faults", "Score each site/radio for failure risk over the next days."), ("recommend_maintenance", "List preventive actions for the riskiest units.")],
    },
    {
        "family": "slice_admission",
        "summary": 'Admits or rejects new sessions per slice or tenant against slice quotas and current load, protecting the guaranteed slices (writes slice_admission).',
        "use_when": 'new users or sessions of a slice or tenant have to be admitted, capped or rejected (admission control, quota per tenant)',
        "avoid_when": 'the PRB reservation of a slice has to be changed (slice SLA assurance / SLICE xApp), or one user needs priority (QoS priority control)', "area": "Network Optimization", "use_case": "Tenant / slice-aware admission control (O-RAN slicing, 3GPP TS 23.501 NSAC)",
        "name": "Slice Admission Controller", "variants": 1, "timescale_s": 10,
        "capabilities": ["slice_admission_control", "tenant_quota_enforcement"],
        "interfaces": ["A1-P policy-type 20011", "E2SM-RC v1.03", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["sac.admission_policy"],
        "control": [("slice", "write", "slice_admission")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("evaluate_admission", "Compute per-slice admission headroom from load and quotas."), ("apply_admission_policy", "Push per-slice admission limits and confirm.")],
    },
    {
        "family": "signalling_storm",
        "summary": 'Detects signalling storms (abnormal bursts of RRC connection attempts from many UEs or devices) and throttles or rejects the offending connection requests (writes rrc_admission).',
        "use_when": 'a flood of connection or registration attempts, e.g. from misbehaving IoT devices, overloads the control plane and has to be detected and throttled',
        "avoid_when": 'access failures are caused by RACH configuration (RACH optimisation) or admission per slice quota is wanted (slice admission control)', "area": "Network Healing", "use_case": "Signalling storm protection (O-RAN UC15)",
        "name": "Signalling Storm Protector", "variants": 1, "timescale_s": 1,
        "capabilities": ["signalling_storm_protection", "connection_throttling"],
        "interfaces": ["E2SM-RC v1.03", "A1-P policy-type 20040", "E2SM-KPM v3.00"],
        "consumes": ["RRC.ConnEstabAtt", "RRC.ConnEstabSucc"], "produces": ["ssp.throttle_policy"],
        "control": [("cell", "write", "rrc_admission")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_signalling_storm", "Flag cells with abnormal connection-attempt bursts."), ("apply_throttling_policy", "Throttle or reject the offending connection requests.")],
    },
    {
        "family": "ul_interference",
        "summary": 'Detects and classifies uplink interference (external, traffic-induced, infrastructure) and retunes uplink power control (P0 nominal PUSCH, alpha) per cell (writes ul_power_control).',
        "use_when": 'uplink SINR or uplink throughput is degraded by interference or a raised noise floor and uplink power control has to be retuned',
        "avoid_when": 'the interference is in the downlink (interference mitigation by power caps) or comes from a PCI clash (PCI optimisation)', "area": "Network Healing", "use_case": "Uplink interference detection and power-control optimisation (3GPP TS 38.300 RIM context)",
        "name": "Uplink Interference Optimizer", "variants": 1, "timescale_s": 3600,
        "capabilities": ["ul_interference_detection", "ul_power_control_tuning"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotUl", "CARR.UlInterference"], "produces": ["uli.power_control_plan"],
        "control": [("cell", "write", "ul_power_control")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_ul_interference", "Classify uplink-interfered cells by interference type."), ("apply_ul_power_control", "Apply P0/alpha changes via O1 and confirm.")],
    },
    {
        "family": "endc_steering",
        "summary": 'Steers EN-DC (NSA) devices between LTE anchors and NR legs by retuning dual-connectivity distribution profiles from NR and LTE load (writes dc_profile).',
        "use_when": 'traffic of 5G NSA / EN-DC devices has to be rebalanced between the LTE anchor and the NR secondary cell, e.g. NR legs overloaded or under-used',
        "avoid_when": 'the users are 5G standalone or the steering is between cells of the same RAT (traffic steering, mobility load balancing)', "area": "Network Evolution", "use_case": "5G NSA (EN-DC) traffic optimisation",
        "name": "EN-DC Traffic Optimizer", "variants": 1, "timescale_s": 900,
        "capabilities": ["endc_steering", "dual_connectivity_policy"],
        "interfaces": ["O1", "A1-P policy-type 20031", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "DRB.UEThpDl"], "produces": ["endc.dc_profile"],
        "control": [("cell", "write", "dc_profile")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("recommend_dc_profile", "Choose a dual-connectivity distribution profile per anchor cell."), ("apply_dc_profile", "Apply the profile and confirm.")],
    },
    {
        "family": "config_audit",
        "summary": 'Audits configuration (CM) consistency across cells and sites against a golden baseline and lists deviating parameters. Read-only.',
        "use_when": 'parameter settings have to be checked for inconsistencies or drift from the baseline, e.g. after a rollout or before a change',
        "avoid_when": 'configuration has to be changed or rolled out (RAN lifecycle orchestration) or KPI deviations are the question (KPI anomaly detection); it never changes RAN state', "area": "Network Deployment", "use_case": "Configuration consistency audit",
        "name": "Configuration Consistency Auditor", "variants": 1, "timescale_s": 3600,
        "capabilities": ["configuration_audit", "config_consistency_check"],
        "interfaces": ["O1 CM"],
        "consumes": [], "produces": ["cca.deviation_report"],
        "control": [("node", "read", "")], "requires": [], "conflicts_with": [],
        "tools": [("audit_configuration", "Compare cell/site parameters with the golden baseline."), ("list_deviations", "List deviating parameters per site.")],
    },
    {
        "family": "crossed_feeder",
        "summary": 'Detects crossed feeders / swapped sectors from UE measurement reports, handover patterns and site topology. Read-only.',
        "use_when": 'installation errors such as crossed feeders or swapped sector cabling are suspected, e.g. after a site build or antenna swap, or handovers go to the wrong sector',
        "avoid_when": 'handover parameters or neighbour lists are the problem (mobility robustness, neighbour relation management); it never changes RAN state', "area": "Network Deployment", "use_case": "Crossed feeder detection",
        "name": "Crossed Feeder Detector", "variants": 1, "timescale_s": 3600,
        "capabilities": ["crossed_feeder_detection", "sector_swap_detection"],
        "interfaces": ["E2SM-KPM v3.00", "O1"],
        "consumes": ["RRC.HO_attempts", "RRC.ConnMean"], "produces": ["cfd.suspect_sectors"],
        "control": [("cell", "read", "")], "requires": ["kpi_monitoring"], "conflicts_with": [],
        "tools": [("detect_crossed_feeders", "Rank sectors by crossed-feeder likelihood.")],
    },
    {
        "family": "special_events",
        "summary": 'Applies a temporary capacity profile (parameter set) to the cells around a planned event and reverts it afterwards (writes event_profile).',
        "use_when": 'a planned mass event (concert, match, fair) needs a temporary capacity configuration for a fixed time window that is reverted afterwards',
        "avoid_when": 'the change is permanent (RAN lifecycle orchestration) or unplanned congestion has to be relieved now (traffic steering); declared conflict with energy saving, which would switch the boosted cells off', "area": "Network Optimization", "use_case": "Special event handling",
        "name": "Special Event Handler", "variants": 1, "timescale_s": 3600,
        "capabilities": ["special_event_handling", "temporary_config_profile", "capacity_boost"],
        "interfaces": ["O1", "E2SM-KPM v3.00"],
        "consumes": ["RRU.PrbTotDl", "RRC.ConnMean"], "produces": ["sev.event_profile"],
        "control": [("cell", "write", "event_profile")], "requires": ["kpi_monitoring"], "conflicts_with": ["energy_saving", "rf_channel_sleep"],
        "tools": [("plan_event_profile", "Select cells and the temporary parameter set for the event window."), ("apply_event_profile", "Apply the event profile and schedule its revert."), ("revert_event_profile", "Revert the cells to their normal configuration.")],
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
