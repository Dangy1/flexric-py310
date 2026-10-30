# Evaluation Analysis

- records: 1962
- methods: 6
- intents: 109

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 327 (109×3) | 65.1% ±5.2% | 42.4% ±16.9% | 67.7% ±5.3% | 19.3% ±4.3% | 3.0% ±5.8% | 21.1% ±4.7% | 35.5% | 861 | 99.9% | 99.9% | 2 | 38.9% (7/18) | 1.0% | 0.0% | 37862.6±12067.9 / 35416.6 / 62301.9 / 88856.9 |
| langgraph_agentcard | 327 (109×3) | 68.8% ±5.0% | 45.5% ±17.0% | 71.4% ±5.2% | 37.6% ±5.3% | 9.1% ±9.8% | 40.8% ±5.6% | 38.5% | 867 | 100.0% | 100.0% | 0 | 33.3% (6/18) | 0.0% | 27.8% | 38293.2±12223.4 / 36208.6 / 58717.8 / 104110.0 |
| llm_blind | 327 (109×3) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 35 | 88.6% | 88.6% | 898 | 16.7% (3/18) | 0.0% | 0.0% | 16108.3±7103.7 / 14911.9 / 27046.2 / 60228.9 |
| llm_only | 327 (109×3) | 16.5% ±4.0% | 75.8% ±14.6% | 9.9% ±3.4% | 14.1% ±3.8% | 75.8% ±14.6% | 7.1% ±2.9% | 14.1% | 1162 | 99.2% | 99.2% | 0 | 44.4% (8/18) | 0.0% | 0.0% | 8549.2±4955.3 / 7237.1 / 14135.9 / 53967.3 |
| manual_rule | 327 (109×3) | 16.5% ±4.0% | 81.8% ±13.2% | 9.2% ±3.3% | 13.8% ±3.7% | 81.8% ±13.2% | 6.1% ±2.7% | 13.8% | 1149 | 98.3% | 98.3% | 0 | 100.0% (18/18) | 0.0% | 0.0% | 1873.3±7779.3 / 2.3 / 32560.6 / 45153.2 |
| single_xapp | 327 (109×3) | 11.0% ±3.4% | 27.3% ±15.2% | 9.2% ±3.3% | 2.8% ±1.8% | 27.3% ±15.2% | 0.0% ±0.0% | 2.8% | 339 | 96.5% | 96.5% | 0 | 66.7% (12/18) | 0.0% | 0.0% | 1223.1±6263.1 / 0.9 / 1.2 / 33560.7 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| anomaly_to_transport_fix | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| antenna_swap_wrong_sector | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| arena_concert_profile | 18 | 27.8% | 16.7% | 0.0% | 0.0% |
| audit_then_rollout | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| backhaul_policy_advice | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 18 | 0.0% | 0.0% | 0.0% | 55.6% |
| beam_then_link_check | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| bearer_buffer_buildup | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| bearer_stall_triage | 18 | 38.9% | 0.0% | 0.0% | 0.0% |
| border_shift_keep_mro | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| campus_slice_drift_detection | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| capacity_headroom_forecast | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| cell_edge_qoe_protection | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| codel_rollback_verification | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| config_rollout_window | 18 | 33.3% | 5.6% | 0.0% | 0.0% |
| congestion_relief | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| coverage_hole_tilt | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| deprecated_card_trap | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| downlink_jitter_containment | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| drb_delay_hotspot | 18 | 38.9% | 0.0% | 0.0% | 0.0% |
| ecn_policy_validation | 18 | 61.1% | 0.0% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 18 | 38.9% | 38.9% | 0.0% | 0.0% |
| emergency_traffic_preemption | 18 | 33.3% | 33.3% | 5.6% | 0.0% |
| energy_saving_wakeup_guard | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| energy_vs_capacity_conflict | 18 | 33.3% | 5.6% | 0.0% | 0.0% |
| enterprise_slice_audit | 18 | 44.4% | 11.1% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| evening_cell_border_shift | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| fair_boost_vs_night_saving | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| far_neighbour_blocklist | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| forecast_antenna_muting | 18 | 27.8% | 22.2% | 0.0% | 0.0% |
| forecast_then_cell_sleep | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| golden_config_drift | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| gtp_tunnel_health_validation | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| handover_route_risk_screening | 18 | 22.2% | 0.0% | 0.0% | 0.0% |
| healing_full_chain | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| highrise_beam_coverage | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| interference_hotspot | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| kpi_anomaly_sweep | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| latency_regression_root_cause | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| latency_under_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| load_balance_hotspot | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| low_priority_traffic_shaping_guard | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| meter_reconnect_storm | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| midday_antenna_muting | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| mobility_root_cause | 18 | 16.7% | 16.7% | 0.0% | 0.0% |
| n3_tunnel_inventory | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| new_small_cells_neighbours | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| night_energy_saving | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| nsa_nr_leg_overload | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| pci_clash_fix | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| pci_then_neighbour_refresh | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| pdcp_discard_check | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| ping_pong_handover_fix | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| pm_report_daily | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| port_access_failures | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| prb_imbalance_correction | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| premium_qos_isolation | 18 | 38.9% | 16.7% | 0.0% | 0.0% |
| priority_for_emergency_ues | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| qoe_driven_steering | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| qoe_without_observation | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| qos_policy_sanity_check | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| radio_failure_outlook | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| report_then_tilt | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| rollout_blocked_by_energy | 18 | 0.0% | 0.0% | 0.0% | 5.6% |
| rural_uplink_noise | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| silent_cell_compensation | 18 | 27.8% | 16.7% | 0.0% | 5.6% |
| silent_cell_sweep | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| slice_admission_control | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| slice_drift_correction | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| slice_fairness_assurance | 18 | 22.2% | 16.7% | 0.0% | 0.0% |
| slice_isolation_validation | 18 | 66.7% | 33.3% | 0.0% | 0.0% |
| slice_oversubscription_repair | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| slice_policy_race_recovery | 18 | 33.3% | 11.1% | 0.0% | 77.8% |
| slice_sla_breach | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| slice_sla_report | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| spectrum_resplit | 18 | 27.8% | 0.0% | 5.6% | 0.0% |
| stadium_congestion_surge | 18 | 38.9% | 38.9% | 0.0% | 0.0% |
| station_load_outlook | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| steering_then_energy | 18 | 27.8% | 11.1% | 0.0% | 0.0% |
| tc_conflict_recovery | 18 | 77.8% | 44.4% | 0.0% | 83.3% |
| tenant_session_cap | 18 | 22.2% | 16.7% | 0.0% | 0.0% |
| tilt_after_outage | 18 | 27.8% | 27.8% | 0.0% | 0.0% |
| transport_bufferbloat_mitigation | 18 | 61.1% | 50.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 18 | 66.7% | 50.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| ue_link_quality_snapshot | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 18 | 0.0% | 0.0% | 0.0% | 16.7% |
| unknown_enterprise_xr_slowdown | 18 | 50.0% | 50.0% | 0.0% | 0.0% |
| unknown_vertical_request | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| uplink_queue_stability | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 18 | 61.1% | 38.9% | 0.0% | 0.0% |
| vendor_variant_trap | 18 | 27.8% | 0.0% | 0.0% | 5.6% |
| video_qoe_forecast | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| video_throughput_smoothing | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| xr_latency_guard | 18 | 61.1% | 55.6% | 0.0% | 0.0% |
