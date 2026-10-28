# Evaluation Analysis

- records: 1500
- methods: 6
- intents: 50

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 250 (50×5) | 70.0% ±5.7% | 67.3% ±12.4% | 70.8% ±6.4% | 12.4% ±4.1% | 10.9% ±8.2% | 12.8% ±4.7% | 12.4% | 550 | 98.5% | 97.1% | 0 | 46.7% (14/30) | 0.0% | 0.0% | 30403.3±13345.9 / 26546.2 / 54904.9 / 106653.6 |
| langgraph_agentcard | 250 (50×5) | 70.4% ±5.7% | 65.5% ±12.6% | 71.8% ±6.3% | 13.6% ±4.2% | 7.3% ±6.9% | 15.4% ±5.1% | 14.0% | 554 | 100.0% | 98.7% | 0 | 36.7% (11/30) | 0.0% | 6.7% | 31012.2±13247.5 / 27279.6 / 59217.6 / 87997.7 |
| llm_blind | 250 (50×5) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 23 | 87.0% | 87.0% | 706 | 6.7% (2/30) | 0.0% | 0.0% | 16691.3±6815.4 / 15307.8 / 27738.8 / 54908.2 |
| llm_only | 250 (50×5) | 34.4% ±5.9% | 67.3% ±12.4% | 25.1% ±6.1% | 28.8% ±5.6% | 67.3% ±12.4% | 17.9% ±5.4% | 29.2% | 856 | 98.5% | 97.5% | 0 | 36.7% (11/30) | 0.0% | 0.0% | 9585.2±6627.4 / 7570.3 / 18714.5 / 57219.6 |
| manual_rule | 250 (50×5) | 36.0% ±6.0% | 81.8% ±10.2% | 23.1% ±5.9% | 30.0% ±5.7% | 81.8% ±10.2% | 15.4% ±5.1% | 30.0% | 780 | 95.9% | 94.7% | 0 | 100.0% (30/30) | 0.0% | 0.0% | 4087.5±11114.4 / 1.1 / 33545.5 / 45092.5 |
| single_xapp | 250 (50×5) | 24.0% ±5.3% | 27.3% ±11.8% | 23.1% ±5.9% | 6.0% ±2.9% | 27.3% ±11.8% | 0.0% ±0.0% | 6.0% | 270 | 92.6% | 92.2% | 0 | 66.7% (20/30) | 0.0% | 0.0% | 2659.9±9019.7 / 0.4 / 33539.4 / 33548.6 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 30 | 33.3% | 3.3% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 30 | 16.7% | 3.3% | 0.0% | 53.3% |
| bearer_stall_triage | 30 | 46.7% | 10.0% | 0.0% | 0.0% |
| campus_slice_drift_detection | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 30 | 6.7% | 3.3% | 0.0% | 0.0% |
| codel_rollback_verification | 30 | 23.3% | 0.0% | 0.0% | 0.0% |
| congestion_relief | 30 | 43.3% | 36.7% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 30 | 56.7% | 33.3% | 0.0% | 0.0% |
| downlink_jitter_containment | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| drb_delay_hotspot | 30 | 16.7% | 0.0% | 0.0% | 0.0% |
| ecn_policy_validation | 30 | 70.0% | 0.0% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 30 | 66.7% | 33.3% | 0.0% | 0.0% |
| emergency_traffic_preemption | 30 | 33.3% | 33.3% | 0.0% | 0.0% |
| enterprise_slice_audit | 30 | 43.3% | 10.0% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 30 | 0.0% | 0.0% | 0.0% | 33.3% |
| gtp_tunnel_health_validation | 30 | 13.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 30 | 50.0% | 33.3% | 0.0% | 0.0% |
| handover_resilience_triage | 30 | 33.3% | 33.3% | 0.0% | 0.0% |
| handover_route_risk_screening | 30 | 46.7% | 13.3% | 0.0% | 0.0% |
| latency_regression_root_cause | 30 | 20.0% | 3.3% | 0.0% | 0.0% |
| latency_under_busy_tc | 30 | 0.0% | 0.0% | 0.0% | 33.3% |
| low_priority_traffic_shaping_guard | 30 | 50.0% | 0.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 30 | 6.7% | 6.7% | 0.0% | 0.0% |
| prb_imbalance_correction | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| premium_qos_isolation | 30 | 50.0% | 20.0% | 0.0% | 0.0% |
| qos_policy_sanity_check | 30 | 76.7% | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 30 | 33.3% | 33.3% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 30 | 16.7% | 0.0% | 0.0% | 0.0% |
| slice_admission_control | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| slice_drift_correction | 30 | 33.3% | 3.3% | 0.0% | 0.0% |
| slice_fairness_assurance | 30 | 50.0% | 16.7% | 0.0% | 0.0% |
| slice_isolation_validation | 30 | 66.7% | 33.3% | 0.0% | 0.0% |
| slice_oversubscription_repair | 30 | 10.0% | 0.0% | 0.0% | 0.0% |
| slice_policy_race_recovery | 30 | 33.3% | 0.0% | 0.0% | 70.0% |
| stadium_congestion_surge | 30 | 33.3% | 33.3% | 0.0% | 0.0% |
| tc_conflict_recovery | 30 | 76.7% | 43.3% | 0.0% | 86.7% |
| transport_bufferbloat_mitigation | 30 | 83.3% | 50.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 30 | 83.3% | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 30 | 70.0% | 36.7% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 30 | 30.0% | 30.0% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 30 | 0.0% | 0.0% | 0.0% | 16.7% |
| unknown_enterprise_xr_slowdown | 30 | 66.7% | 63.3% | 0.0% | 0.0% |
| uplink_queue_stability | 30 | 33.3% | 6.7% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 30 | 66.7% | 53.3% | 0.0% | 0.0% |
| video_throughput_smoothing | 30 | 33.3% | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 30 | 33.3% | 13.3% | 0.0% | 0.0% |
| xr_latency_guard | 30 | 66.7% | 63.3% | 0.0% | 0.0% |
