# Evaluation Analysis

- records: 1500
- methods: 6
- intents: 50

## Method Summary

Metric definitions: `evaluation/METRICS.md`. Accuracies are exact ordered matches with ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Workflow acc. | Known acc. | Open-world acc. | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 250 (50×5) | 58.4% ±6.1% | 9.1% ±7.6% | 72.3% ±6.3% | 64.4% | 699 | 97.7% | 95.4% | 0 | 53.3% (16/30) | 0.0% | 0.0% | 4880.5±546.9 / 4903.9 / 5730.2 / 6373.8 |
| langgraph_agentcard | 250 (50×5) | 57.6% ±6.1% | 9.1% ±7.6% | 71.3% ±6.4% | 63.6% | 721 | 100.0% | 97.9% | 0 | 80.0% (24/30) | 0.0% | 80.0% | 5484.4±1728.5 / 5098.3 / 10337.3 / 11868.4 |
| llm_blind | 250 (50×5) | 8.0% ±3.4% | 9.1% ±7.6% | 7.7% ±3.7% | 10.0% | 640 | 95.3% | 91.1% | 25 | 100.0% (30/30) | 0.0% | 0.0% | 3074.1±420.7 / 3064.8 / 3746.5 / 4208.7 |
| llm_only | 250 (50×5) | 32.0% ±5.8% | 81.8% ±10.2% | 17.9% ±5.4% | 36.0% | 807 | 97.3% | 96.5% | 0 | 73.3% (22/30) | 0.0% | 0.0% | 2897.2±324.5 / 2900.9 / 3451.3 / 3827.4 |
| manual_rule | 250 (50×5) | 32.0% ±5.8% | 100.0% ±0.0% | 12.8% ±4.7% | 38.0% | 680 | 95.6% | 93.2% | 0 | 100.0% (30/30) | 0.0% | 0.0% | 1.3±0.8 / 0.9 / 2.5 / 2.8 |
| single_xapp | 250 (50×5) | 6.0% ±2.9% | 27.3% ±11.8% | 0.0% ±0.0% | 6.0% | 250 | 92.0% | 87.2% | 0 | 66.7% (20/30) | 0.0% | 0.0% | 0.6±0.2 / 0.7 / 0.8 / 0.9 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Workflow match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 30 | 33.3% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 30 | 33.3% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 30 | 33.3% | 83.3% | 100.0% |
| bearer_stall_triage | 30 | 33.3% | 0.0% | 0.0% |
| campus_slice_drift_detection | 30 | 36.7% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 30 | 33.3% | 0.0% | 0.0% |
| codel_rollback_verification | 30 | 0.0% | 0.0% | 0.0% |
| congestion_relief | 30 | 33.3% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 30 | 50.0% | 0.0% | 0.0% |
| downlink_jitter_containment | 30 | 33.3% | 0.0% | 0.0% |
| drb_delay_hotspot | 30 | 33.3% | 0.0% | 0.0% |
| ecn_policy_validation | 30 | 16.7% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 30 | 33.3% | 0.0% | 0.0% |
| emergency_traffic_preemption | 30 | 60.0% | 0.0% | 0.0% |
| enterprise_slice_audit | 30 | 33.3% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 30 | 3.3% | 66.7% | 83.3% |
| gtp_tunnel_health_validation | 30 | 33.3% | 0.0% | 0.0% |
| handover_ping_pong_detection | 30 | 33.3% | 0.0% | 0.0% |
| handover_resilience_triage | 30 | 33.3% | 0.0% | 0.0% |
| handover_route_risk_screening | 30 | 33.3% | 0.0% | 0.0% |
| latency_regression_root_cause | 30 | 33.3% | 0.0% | 0.0% |
| latency_under_busy_tc | 30 | 16.7% | 36.7% | 50.0% |
| low_priority_traffic_shaping_guard | 30 | 0.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 30 | 33.3% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 30 | 33.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 30 | 33.3% | 0.0% | 0.0% |
| prb_imbalance_correction | 30 | 33.3% | 0.0% | 0.0% |
| premium_qos_isolation | 30 | 50.0% | 0.0% | 0.0% |
| qos_policy_sanity_check | 30 | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 30 | 33.3% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 30 | 20.0% | 0.0% | 0.0% |
| slice_admission_control | 30 | 16.7% | 0.0% | 0.0% |
| slice_drift_correction | 30 | 33.3% | 0.0% | 0.0% |
| slice_fairness_assurance | 30 | 16.7% | 0.0% | 0.0% |
| slice_isolation_validation | 30 | 33.3% | 0.0% | 0.0% |
| slice_oversubscription_repair | 30 | 33.3% | 0.0% | 0.0% |
| slice_policy_race_recovery | 30 | 33.3% | 83.3% | 100.0% |
| stadium_congestion_surge | 30 | 46.7% | 0.0% | 0.0% |
| tc_conflict_recovery | 30 | 50.0% | 83.3% | 100.0% |
| transport_bufferbloat_mitigation | 30 | 50.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 30 | 16.7% | 0.0% | 0.0% |
| transport_tunnel_stability | 30 | 50.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 30 | 33.3% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 30 | 0.0% | 40.0% | 40.0% |
| unknown_enterprise_xr_slowdown | 30 | 66.7% | 0.0% | 0.0% |
| uplink_queue_stability | 30 | 33.3% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 30 | 66.7% | 0.0% | 0.0% |
| video_throughput_smoothing | 30 | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 30 | 33.3% | 0.0% | 0.0% |
| xr_latency_guard | 30 | 83.3% | 0.0% | 0.0% |
