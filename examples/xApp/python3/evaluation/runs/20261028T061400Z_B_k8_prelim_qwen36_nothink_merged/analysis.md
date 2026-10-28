# Evaluation Analysis

- records: 1440
- methods: 6
- intents: 80

## Method Summary

Metric definitions: `evaluation/METRICS.md`. Accuracies are exact ordered matches with ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Workflow acc. | Known acc. | Open-world acc. | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 240 (80×3) | 26.7% ±5.6% | 0.0% ±0.0% | 30.9% ±6.3% | 27.9% | 759 | 99.6% | 99.1% | 0 | 16.7% (3/18) | 0.0% | 0.0% | 6133.0±1728.2 / 5890.9 / 7769.4 / 28424.6 |
| langgraph_agentcard | 240 (80×3) | 27.9% ±5.7% | 0.0% ±0.0% | 32.4% ±6.4% | 30.8% | 718 | 100.0% | 99.0% | 0 | 61.1% (11/18) | 0.0% | 61.1% | 6559.3±2681.4 / 6029.4 / 9457.1 / 31940.7 |
| llm_blind | 239 (80×3) | 4.6% ±2.7% | 9.1% ±9.8% | 3.9% ±2.6% | 5.4% | 493 | 96.3% | 92.7% | 136 | 100.0% (18/18) | 0.0% | 0.0% | 3043.6±431.1 / 2987.9 / 3801.0 / 4157.5 |
| llm_only | 240 (80×3) | 20.0% ±5.1% | 81.8% ±13.2% | 10.1% ±4.1% | 22.5% | 834 | 98.2% | 98.1% | 0 | 83.3% (15/18) | 0.0% | 0.0% | 2998.0±344.4 / 2970.9 / 3635.3 / 4155.3 |
| manual_rule | 240 (80×3) | 20.0% ±5.1% | 100.0% ±0.0% | 7.2% ±3.5% | 23.8% | 747 | 97.6% | 97.3% | 0 | 100.0% (18/18) | 0.0% | 0.0% | 1.7±0.8 / 2.2 / 2.6 / 2.8 |
| single_xapp | 240 (80×3) | 3.8% ±2.4% | 27.3% ±15.2% | 0.0% ±0.0% | 3.8% | 240 | 95.0% | 93.8% | 0 | 66.7% (12/18) | 0.0% | 0.0% | 0.7±0.2 / 0.8 / 0.9 / 1.0 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Workflow match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 18 | 0.0% | 0.0% | 0.0% |
| anomaly_to_transport_fix | 18 | 33.3% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 18 | 0.0% | 0.0% | 0.0% |
| backhaul_policy_advice | 18 | 33.3% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 18 | 0.0% | 66.7% | 66.7% |
| bearer_stall_triage | 18 | 0.0% | 0.0% | 0.0% |
| campus_slice_drift_detection | 18 | 0.0% | 0.0% | 0.0% |
| capacity_headroom_forecast | 18 | 5.6% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 18 | 0.0% | 0.0% | 0.0% |
| cell_edge_qoe_protection | 18 | 33.3% | 0.0% | 0.0% |
| codel_rollback_verification | 18 | 0.0% | 0.0% | 0.0% |
| config_rollout_window | 18 | 0.0% | 0.0% | 0.0% |
| congestion_relief | 18 | 33.3% | 0.0% | 0.0% |
| coverage_hole_tilt | 18 | 33.3% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 18 | 16.7% | 0.0% | 0.0% |
| deprecated_card_trap | 18 | 0.0% | 0.0% | 0.0% |
| downlink_jitter_containment | 18 | 0.0% | 0.0% | 0.0% |
| drb_delay_hotspot | 18 | 0.0% | 0.0% | 0.0% |
| ecn_policy_validation | 18 | 16.7% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 18 | 33.3% | 0.0% | 0.0% |
| emergency_traffic_preemption | 18 | 44.4% | 0.0% | 0.0% |
| energy_saving_wakeup_guard | 18 | 16.7% | 0.0% | 0.0% |
| energy_vs_capacity_conflict | 18 | 33.3% | 0.0% | 0.0% |
| enterprise_slice_audit | 18 | 33.3% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 18 | 11.1% | 66.7% | 77.8% |
| gtp_tunnel_health_validation | 18 | 33.3% | 0.0% | 0.0% |
| handover_ping_pong_detection | 18 | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 18 | 33.3% | 0.0% | 0.0% |
| handover_route_risk_screening | 18 | 0.0% | 0.0% | 0.0% |
| healing_full_chain | 18 | 0.0% | 0.0% | 0.0% |
| interference_hotspot | 18 | 33.3% | 0.0% | 0.0% |
| kpi_anomaly_sweep | 18 | 33.3% | 0.0% | 0.0% |
| latency_regression_root_cause | 18 | 0.0% | 0.0% | 0.0% |
| latency_under_busy_tc | 18 | 16.7% | 33.3% | 33.3% |
| load_balance_hotspot | 18 | 33.3% | 0.0% | 0.0% |
| low_priority_traffic_shaping_guard | 18 | 0.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 18 | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 18 | 0.0% | 0.0% | 0.0% |
| mobility_root_cause | 18 | 0.0% | 0.0% | 0.0% |
| night_energy_saving | 18 | 33.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 18 | 0.0% | 0.0% | 0.0% |
| ping_pong_handover_fix | 18 | 33.3% | 0.0% | 0.0% |
| pm_report_daily | 18 | 33.3% | 0.0% | 0.0% |
| prb_imbalance_correction | 18 | 0.0% | 0.0% | 0.0% |
| premium_qos_isolation | 18 | 16.7% | 0.0% | 0.0% |
| priority_for_emergency_ues | 18 | 0.0% | 0.0% | 0.0% |
| qoe_driven_steering | 18 | 33.3% | 0.0% | 0.0% |
| qoe_without_observation | 18 | 33.3% | 0.0% | 0.0% |
| qos_policy_sanity_check | 18 | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 18 | 33.3% | 0.0% | 0.0% |
| report_then_tilt | 18 | 33.3% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 18 | 0.0% | 0.0% | 0.0% |
| rollout_blocked_by_energy | 18 | 0.0% | 0.0% | 0.0% |
| slice_admission_control | 18 | 27.8% | 0.0% | 0.0% |
| slice_drift_correction | 18 | 5.6% | 0.0% | 0.0% |
| slice_fairness_assurance | 18 | 16.7% | 0.0% | 0.0% |
| slice_isolation_validation | 18 | 33.3% | 0.0% | 0.0% |
| slice_oversubscription_repair | 18 | 0.0% | 0.0% | 0.0% |
| slice_policy_race_recovery | 18 | 5.6% | 66.7% | 83.3% |
| slice_sla_breach | 18 | 0.0% | 0.0% | 0.0% |
| slice_sla_report | 18 | 0.0% | 0.0% | 0.0% |
| spectrum_resplit | 18 | 16.7% | 0.0% | 0.0% |
| stadium_congestion_surge | 18 | 38.9% | 0.0% | 0.0% |
| steering_then_energy | 18 | 33.3% | 0.0% | 0.0% |
| tc_conflict_recovery | 18 | 50.0% | 83.3% | 100.0% |
| tilt_after_outage | 18 | 33.3% | 0.0% | 0.0% |
| transport_bufferbloat_mitigation | 18 | 50.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 18 | 16.7% | 0.0% | 0.0% |
| transport_tunnel_stability | 18 | 50.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 18 | 0.0% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 18 | 0.0% | 50.0% | 66.7% |
| unknown_enterprise_xr_slowdown | 18 | 66.7% | 0.0% | 0.0% |
| unknown_vertical_request | 18 | 0.0% | 0.0% | 0.0% |
| uplink_queue_stability | 18 | 0.0% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 18 | 33.3% | 0.0% | 0.0% |
| vendor_variant_trap | 18 | 0.0% | 0.0% | 0.0% |
| video_qoe_forecast | 18 | 33.3% | 0.0% | 0.0% |
| video_throughput_smoothing | 18 | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 18 | 0.0% | 0.0% | 0.0% |
| xr_latency_guard | 18 | 50.0% | 0.0% | 0.0% |
