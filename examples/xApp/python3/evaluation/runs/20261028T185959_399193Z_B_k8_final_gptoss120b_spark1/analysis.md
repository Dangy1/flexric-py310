# Evaluation Analysis

- records: 1962
- methods: 6
- intents: 109

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 327 (109×3) | 69.1% ±5.0% | 42.4% ±16.9% | 72.1% ±5.1% | 13.5% ±3.7% | 3.0% ±5.8% | 14.6% ±4.0% | 33.0% | 814 | 99.9% | 97.4% | 1 | 33.3% (6/18) | 1.3% | 0.0% | 33644.8±11023.2 / 32801.8 / 53904.3 / 70105.6 |
| langgraph_agentcard | 327 (109×3) | 68.5% ±5.0% | 45.5% ±17.0% | 71.1% ±5.2% | 32.4% ±5.1% | 3.0% ±5.8% | 35.7% ±5.5% | 33.9% | 837 | 100.0% | 97.8% | 0 | 44.4% (8/18) | 0.0% | 44.4% | 34309.8±11587.7 / 32837.8 / 55531.0 / 76932.6 |
| llm_blind | 327 (109×3) | 0.3% ±0.6% | 0.0% ±0.0% | 0.3% ±0.7% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 39 | 97.4% | 92.3% | 1024 | 5.6% (1/18) | 0.0% | 0.0% | 17519.3±11013.5 / 16083.6 / 28043.8 / 175105.4 |
| llm_only | 327 (109×3) | 16.8% ±4.1% | 75.8% ±14.6% | 10.2% ±3.5% | 14.1% ±3.8% | 75.8% ±14.6% | 7.1% ±2.9% | 14.1% | 1183 | 99.4% | 96.4% | 0 | 38.9% (7/18) | 0.0% | 0.0% | 8994.4±4549.2 / 7709.8 / 14544.9 / 36610.7 |
| manual_rule | 327 (109×3) | 16.5% ±4.0% | 81.8% ±13.2% | 9.2% ±3.3% | 13.8% ±3.7% | 81.8% ±13.2% | 6.1% ±2.7% | 13.8% | 1149 | 98.3% | 95.7% | 0 | 100.0% (18/18) | 0.0% | 0.0% | 1898.0±7908.2 / 1.1 / 32543.4 / 45149.6 |
| single_xapp | 327 (109×3) | 11.0% ±3.4% | 27.3% ±15.2% | 9.2% ±3.3% | 2.8% ±1.8% | 27.3% ±15.2% | 0.0% ±0.0% | 2.8% | 339 | 96.5% | 95.0% | 0 | 66.7% (12/18) | 0.0% | 0.0% | 1228.7±6292.6 / 0.5 / 1.1 / 33563.9 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| anomaly_to_transport_fix | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| antenna_swap_wrong_sector | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| arena_concert_profile | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| audit_then_rollout | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| backhaul_policy_advice | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 18 | 0.0% | 0.0% | 0.0% | 72.2% |
| beam_then_link_check | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| bearer_buffer_buildup | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| bearer_stall_triage | 18 | 44.4% | 0.0% | 0.0% | 0.0% |
| border_shift_keep_mro | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| campus_slice_drift_detection | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| capacity_headroom_forecast | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 18 | 5.6% | 0.0% | 0.0% | 0.0% |
| cell_edge_qoe_protection | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| codel_rollback_verification | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| config_rollout_window | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| congestion_relief | 18 | 38.9% | 33.3% | 0.0% | 0.0% |
| coverage_hole_tilt | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 18 | 38.9% | 33.3% | 0.0% | 0.0% |
| deprecated_card_trap | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| downlink_jitter_containment | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| drb_delay_hotspot | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| ecn_policy_validation | 18 | 61.1% | 0.0% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 18 | 50.0% | 33.3% | 0.0% | 0.0% |
| emergency_traffic_preemption | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| energy_saving_wakeup_guard | 18 | 27.8% | 5.6% | 0.0% | 0.0% |
| energy_vs_capacity_conflict | 18 | 27.8% | 5.6% | 0.0% | 0.0% |
| enterprise_slice_audit | 18 | 50.0% | 16.7% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| evening_cell_border_shift | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| fair_boost_vs_night_saving | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| far_neighbour_blocklist | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| forecast_antenna_muting | 18 | 22.2% | 11.1% | 0.0% | 0.0% |
| forecast_then_cell_sleep | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| golden_config_drift | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| gtp_tunnel_health_validation | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| handover_route_risk_screening | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| healing_full_chain | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| highrise_beam_coverage | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| interference_hotspot | 18 | 33.3% | 5.6% | 0.0% | 0.0% |
| kpi_anomaly_sweep | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| latency_regression_root_cause | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| latency_under_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| load_balance_hotspot | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| low_priority_traffic_shaping_guard | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| meter_reconnect_storm | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| midday_antenna_muting | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| mobility_root_cause | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| n3_tunnel_inventory | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| new_small_cells_neighbours | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| night_energy_saving | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| nsa_nr_leg_overload | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| pci_clash_fix | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| pci_then_neighbour_refresh | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| pdcp_discard_check | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| ping_pong_handover_fix | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| pm_report_daily | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| port_access_failures | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| prb_imbalance_correction | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| premium_qos_isolation | 18 | 33.3% | 16.7% | 0.0% | 5.6% |
| priority_for_emergency_ues | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| qoe_driven_steering | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| qoe_without_observation | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| qos_policy_sanity_check | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 18 | 33.3% | 33.3% | 0.0% | 5.6% |
| radio_failure_outlook | 18 | 33.3% | 27.8% | 0.0% | 0.0% |
| report_then_tilt | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 18 | 50.0% | 0.0% | 0.0% | 0.0% |
| rollout_blocked_by_energy | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| rural_uplink_noise | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| silent_cell_compensation | 18 | 27.8% | 0.0% | 0.0% | 0.0% |
| silent_cell_sweep | 18 | 33.3% | 22.2% | 0.0% | 0.0% |
| slice_admission_control | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| slice_drift_correction | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| slice_fairness_assurance | 18 | 16.7% | 16.7% | 0.0% | 0.0% |
| slice_isolation_validation | 18 | 66.7% | 33.3% | 0.0% | 0.0% |
| slice_oversubscription_repair | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| slice_policy_race_recovery | 18 | 33.3% | 5.6% | 0.0% | 55.6% |
| slice_sla_breach | 18 | 16.7% | 0.0% | 0.0% | 0.0% |
| slice_sla_report | 18 | 16.7% | 5.6% | 0.0% | 0.0% |
| spectrum_resplit | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| stadium_congestion_surge | 18 | 44.4% | 33.3% | 0.0% | 0.0% |
| station_load_outlook | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| steering_then_energy | 18 | 33.3% | 11.1% | 0.0% | 0.0% |
| tc_conflict_recovery | 18 | 72.2% | 38.9% | 0.0% | 77.8% |
| tenant_session_cap | 18 | 22.2% | 16.7% | 0.0% | 0.0% |
| tilt_after_outage | 18 | 11.1% | 11.1% | 0.0% | 11.1% |
| transport_bufferbloat_mitigation | 18 | 83.3% | 50.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 18 | 55.6% | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 18 | 61.1% | 50.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| ue_link_quality_snapshot | 18 | 33.3% | 33.3% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 18 | 0.0% | 0.0% | 0.0% | 16.7% |
| unknown_enterprise_xr_slowdown | 18 | 55.6% | 44.4% | 0.0% | 0.0% |
| unknown_vertical_request | 18 | 0.0% | 0.0% | 0.0% | 0.0% |
| uplink_queue_stability | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 18 | 66.7% | 38.9% | 0.0% | 0.0% |
| vendor_variant_trap | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| video_qoe_forecast | 18 | 33.3% | 16.7% | 0.0% | 0.0% |
| video_throughput_smoothing | 18 | 33.3% | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 18 | 11.1% | 0.0% | 0.0% | 0.0% |
| xr_latency_guard | 18 | 44.4% | 44.4% | 0.0% | 0.0% |
