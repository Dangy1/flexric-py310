# Evaluation Analysis

- records: 1308
- methods: 4
- intents: 109

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| appweaver_guided | 327 (109×3) | 62.7% ±5.2% | 36.4% ±16.4% | 65.6% ±5.4% | 26.6% ±4.8% | 6.1% ±8.1% | 28.9% ±5.2% | 26.9% | 754 | 100.0% | 99.9% | 0 | 50.0% (9/18) | 0.0% | 38.9% | 51084.3±28792.0 / 42532.2 / 117174.8 / 188379.6 |
| appweaver_mem | 327 (109×3) | 74.6% ±4.7% | 66.7% ±16.1% | 75.5% ±4.9% | 48.0% ±5.4% | 24.2% ±14.6% | 50.7% ±5.7% | 49.5% | 829 | 100.0% | 99.9% | 0 | 55.6% (10/18) | 0.0% | 44.4% | 34489.8±13453.1 / 32472.3 / 58310.8 / 120248.0 |
| appweaver_tpl | 327 (109×3) | 72.8% ±4.8% | 66.7% ±16.1% | 73.5% ±5.0% | 41.6% ±5.3% | 15.2% ±12.2% | 44.6% ±5.7% | 43.4% | 836 | 100.0% | 100.0% | 0 | 38.9% (7/18) | 0.0% | 33.3% | 31151.7±11217.6 / 30353.1 / 50787.9 / 88864.1 |
| appweaver_v2 | 327 (109×3) | 67.6% ±5.1% | 39.4% ±16.7% | 70.7% ±5.2% | 28.7% ±4.9% | 6.1% ±8.1% | 31.3% ±5.3% | 28.7% | 733 | 100.0% | 100.0% | 0 | 27.8% (5/18) | 0.0% | 22.2% | 50500.1±29294.0 / 41373.0 / 108700.3 / 232283.5 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| anomaly_containment_degraded_service | 12 | 41.7% | 8.3% | 0.0% | 0.0% |
| anomaly_to_transport_fix | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| antenna_swap_wrong_sector | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| arena_concert_profile | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| audit_then_rollout | 12 | 66.7% | 66.7% | 0.0% | 0.0% |
| backhaul_delay_mitigation | 12 | 66.7% | 25.0% | 0.0% | 0.0% |
| backhaul_policy_advice | 12 | 50.0% | 0.0% | 0.0% | 0.0% |
| backhaul_queue_conflict_recovery | 12 | 66.7% | 8.3% | 0.0% | 50.0% |
| beam_then_link_check | 12 | 100.0% | 91.7% | 0.0% | 0.0% |
| bearer_buffer_buildup | 12 | 100.0% | 25.0% | 0.0% | 0.0% |
| bearer_stall_triage | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| border_shift_keep_mro | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| campus_slice_drift_detection | 12 | 33.3% | 8.3% | 0.0% | 0.0% |
| capacity_headroom_forecast | 12 | 50.0% | 50.0% | 0.0% | 0.0% |
| cell_edge_fairness_protection | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
| cell_edge_qoe_protection | 12 | 100.0% | 58.3% | 0.0% | 0.0% |
| codel_rollback_verification | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| config_rollout_window | 12 | 50.0% | 16.7% | 0.0% | 0.0% |
| congestion_relief | 12 | 58.3% | 58.3% | 0.0% | 0.0% |
| coverage_hole_tilt | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| cross_slice_resource_rebalance | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| deprecated_card_trap | 12 | 100.0% | 16.7% | 0.0% | 0.0% |
| downlink_jitter_containment | 12 | 75.0% | 41.7% | 0.0% | 0.0% |
| drb_delay_hotspot | 12 | 75.0% | 0.0% | 0.0% | 0.0% |
| ecn_policy_validation | 12 | 50.0% | 8.3% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 12 | 91.7% | 50.0% | 0.0% | 0.0% |
| emergency_traffic_preemption | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| energy_saving_wakeup_guard | 12 | 91.7% | 25.0% | 0.0% | 0.0% |
| energy_vs_capacity_conflict | 12 | 50.0% | 8.3% | 0.0% | 0.0% |
| enterprise_slice_audit | 12 | 50.0% | 0.0% | 0.0% | 0.0% |
| enterprise_tunnel_busy_tc | 12 | 50.0% | 0.0% | 0.0% | 25.0% |
| evening_cell_border_shift | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| fair_boost_vs_night_saving | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| far_neighbour_blocklist | 12 | 83.3% | 83.3% | 0.0% | 0.0% |
| forecast_antenna_muting | 12 | 91.7% | 91.7% | 0.0% | 0.0% |
| forecast_then_cell_sleep | 12 | 75.0% | 75.0% | 0.0% | 0.0% |
| golden_config_drift | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| gtp_tunnel_health_validation | 12 | 8.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 12 | 25.0% | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| handover_route_risk_screening | 12 | 75.0% | 25.0% | 0.0% | 0.0% |
| healing_full_chain | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| highrise_beam_coverage | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| interference_hotspot | 12 | 100.0% | 33.3% | 0.0% | 0.0% |
| kpi_anomaly_sweep | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| latency_regression_root_cause | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| latency_under_busy_tc | 12 | 0.0% | 0.0% | 0.0% | 33.3% |
| load_balance_hotspot | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| low_priority_traffic_shaping_guard | 12 | 41.7% | 0.0% | 0.0% | 0.0% |
| meter_reconnect_storm | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| midday_antenna_muting | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 12 | 100.0% | 8.3% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 12 | 33.3% | 25.0% | 0.0% | 0.0% |
| mobility_root_cause | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| n3_tunnel_inventory | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| new_small_cells_neighbours | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| night_energy_saving | 12 | 100.0% | 16.7% | 0.0% | 0.0% |
| nsa_nr_leg_overload | 12 | 66.7% | 50.0% | 0.0% | 0.0% |
| pci_clash_fix | 12 | 100.0% | 91.7% | 0.0% | 0.0% |
| pci_then_neighbour_refresh | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| pdcp_discard_check | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| ping_pong_handover_fix | 12 | 100.0% | 41.7% | 0.0% | 0.0% |
| pm_report_daily | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| port_access_failures | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| prb_imbalance_correction | 12 | 100.0% | 16.7% | 0.0% | 0.0% |
| premium_qos_isolation | 12 | 91.7% | 41.7% | 0.0% | 0.0% |
| priority_for_emergency_ues | 12 | 75.0% | 33.3% | 0.0% | 0.0% |
| qoe_driven_steering | 12 | 91.7% | 41.7% | 0.0% | 0.0% |
| qoe_without_observation | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| qos_policy_sanity_check | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| radio_failure_outlook | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| report_then_tilt | 12 | 58.3% | 0.0% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| rollout_blocked_by_energy | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| rural_uplink_noise | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| silent_cell_compensation | 12 | 58.3% | 0.0% | 0.0% | 0.0% |
| silent_cell_sweep | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| slice_admission_control | 12 | 50.0% | 0.0% | 0.0% | 0.0% |
| slice_drift_correction | 12 | 75.0% | 41.7% | 0.0% | 0.0% |
| slice_fairness_assurance | 12 | 83.3% | 8.3% | 0.0% | 0.0% |
| slice_isolation_validation | 12 | 50.0% | 25.0% | 0.0% | 0.0% |
| slice_oversubscription_repair | 12 | 58.3% | 8.3% | 0.0% | 0.0% |
| slice_policy_race_recovery | 12 | 91.7% | 50.0% | 0.0% | 83.3% |
| slice_sla_breach | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
| slice_sla_report | 12 | 75.0% | 41.7% | 0.0% | 0.0% |
| spectrum_resplit | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| stadium_congestion_surge | 12 | 58.3% | 58.3% | 0.0% | 0.0% |
| station_load_outlook | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| steering_then_energy | 12 | 91.7% | 33.3% | 0.0% | 0.0% |
| tc_conflict_recovery | 12 | 100.0% | 16.7% | 0.0% | 66.7% |
| tenant_session_cap | 12 | 83.3% | 83.3% | 0.0% | 0.0% |
| tilt_after_outage | 12 | 75.0% | 50.0% | 0.0% | 0.0% |
| transport_bufferbloat_mitigation | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| transport_queue_partition_tuning | 12 | 91.7% | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| tunnel_retransmission_diagnosis | 12 | 100.0% | 0.0% | 0.0% | 0.0% |
| ue_link_quality_snapshot | 12 | 100.0% | 91.7% | 0.0% | 0.0% |
| unknown_busy_runtime_recovery | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
| unknown_enterprise_xr_slowdown | 12 | 100.0% | 50.0% | 0.0% | 0.0% |
| unknown_vertical_request | 12 | 0.0% | 0.0% | 0.0% | 0.0% |
| uplink_queue_stability | 12 | 91.7% | 0.0% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 12 | 91.7% | 66.7% | 0.0% | 0.0% |
| vendor_variant_trap | 12 | 91.7% | 0.0% | 0.0% | 0.0% |
| video_qoe_forecast | 12 | 100.0% | 100.0% | 0.0% | 0.0% |
| video_throughput_smoothing | 12 | 100.0% | 25.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 12 | 100.0% | 25.0% | 0.0% | 0.0% |
| xr_latency_guard | 12 | 33.3% | 33.3% | 0.0% | 0.0% |
