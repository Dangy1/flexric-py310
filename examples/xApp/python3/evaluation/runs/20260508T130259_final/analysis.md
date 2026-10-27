# Evaluation Analysis

- records: 700
- methods: 7
- intents: 50

## Method Summary

| Method | Runs | Available runs | Workflow accuracy | Known accuracy | Open-world accuracy | Custom workflow rate | Tool success | Non-observation tool success | Cached observation rate | Policy validity | Hallucination | Recovery | Internal recovery | Conflict detection | Avg orchestration latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| langgraph_agentcard | 100 | 100 (100.0%) | 61.0% | 100.0% | 50.0% | 62.0% | 100.0% | 100.0% | 93.6% | 100.0% | 0.0% | 100.0% | 100.0% | 96.0% | 3249.7 |
| langgraph_enforced | 100 | 100 (100.0%) | 32.0% | 100.0% | 12.8% | 0.0% | 89.7% | 89.5% | 90.3% | 100.0% | 0.0% | 100.0% | n/a | 100.0% | 47.0 |
| langgraph_llm | 100 | 100 (100.0%) | 32.0% | 100.0% | 12.8% | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 100.0% | 100.0% | 314.6 |
| langgraph_override | 100 | 100 (100.0%) | 32.0% | 100.0% | 12.8% | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | n/a | 100.0% | 134.8 |
| llm_only | 100 | 100 (100.0%) | 30.0% | 72.7% | 17.9% | 0.0% | 98.2% | 97.6% | 98.8% | 100.0% | 0.0% | 100.0% | n/a | 88.0% | 1013.7 |
| manual_rule | 100 | 100 (100.0%) | 32.0% | 100.0% | 12.8% | 0.0% | 95.6% | 94.3% | 95.2% | 100.0% | 0.0% | 100.0% | n/a | 88.0% | 1.3 |
| single_xapp | 100 | 100 (100.0%) | 6.0% | 27.3% | 0.0% | 0.0% | 92.0% | 84.6% | 100.0% | 100.0% | 0.0% | 100.0% | n/a | 88.0% | 0.4 |

## Intent Summary

| Intent ID | Runs | Workflow match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 14 | 0.0% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 14 | 14.3% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 14 | 7.1% | 42.9% | 28.6% |
| bearer_stall_triage | 14 | 0.0% | 0.0% | 0.0% |
| campus_slice_drift_detection | 14 | 0.0% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 14 | 7.1% | 0.0% | 0.0% |
| codel_rollback_verification | 14 | 0.0% | 0.0% | 0.0% |
| congestion_relief | 14 | 85.7% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 14 | 28.6% | 0.0% | 0.0% |
| downlink_jitter_containment | 14 | 14.3% | 0.0% | 0.0% |
| drb_delay_hotspot | 14 | 14.3% | 0.0% | 0.0% |
| ecn_policy_validation | 14 | 0.0% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 14 | 85.7% | 0.0% | 0.0% |
| emergency_traffic_preemption | 14 | 78.6% | 0.0% | 0.0% |
| enterprise_slice_audit | 14 | 71.4% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 14 | 0.0% | 28.6% | 28.6% |
| gtp_tunnel_health_validation | 14 | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 14 | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 14 | 85.7% | 0.0% | 0.0% |
| handover_route_risk_screening | 14 | 0.0% | 0.0% | 0.0% |
| latency_regression_root_cause | 14 | 0.0% | 0.0% | 0.0% |
| latency_under_busy_tc | 14 | 71.4% | 14.3% | 28.6% |
| low_priority_traffic_shaping_guard | 14 | 0.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 14 | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 14 | 14.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 14 | 7.1% | 0.0% | 0.0% |
| prb_imbalance_correction | 14 | 14.3% | 0.0% | 0.0% |
| premium_qos_isolation | 14 | 28.6% | 0.0% | 0.0% |
| qos_policy_sanity_check | 14 | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 14 | 85.7% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 14 | 0.0% | 0.0% | 0.0% |
| slice_admission_control | 14 | 14.3% | 0.0% | 0.0% |
| slice_drift_correction | 14 | 14.3% | 0.0% | 0.0% |
| slice_fairness_assurance | 14 | 71.4% | 0.0% | 0.0% |
| slice_isolation_validation | 14 | 85.7% | 0.0% | 0.0% |
| slice_oversubscription_repair | 14 | 14.3% | 0.0% | 0.0% |
| slice_policy_race_recovery | 14 | 14.3% | 42.9% | 28.6% |
| stadium_congestion_surge | 14 | 85.7% | 0.0% | 0.0% |
| tc_conflict_recovery | 14 | 100.0% | 42.9% | 28.6% |
| transport_bufferbloat_mitigation | 14 | 100.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 14 | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 14 | 100.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 14 | 14.3% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 14 | 0.0% | 14.3% | 28.6% |
| unknown_enterprise_xr_slowdown | 14 | 85.7% | 0.0% | 0.0% |
| uplink_queue_stability | 14 | 14.3% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 14 | 78.6% | 0.0% | 0.0% |
| video_throughput_smoothing | 14 | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 14 | 14.3% | 0.0% | 0.0% |
| xr_latency_guard | 14 | 85.7% | 0.0% | 0.0% |
