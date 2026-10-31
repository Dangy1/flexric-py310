# Evaluation Analysis

- records: 900
- methods: 5
- intents: 60

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| appweaver_mem | 180 (60×3) | 96.1% ±2.8% | 100.0% ±0.0% | 92.2% ±5.5% | 44.4% ±7.3% | 42.2% ±10.2% | 46.7% ±10.3% | 45.0% | 416 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 32029.9±18878.5 / 31423.9 / 66097.5 / 89261.3 |
| appweaver_mem2 | 180 (60×3) | 96.1% ±2.8% | 98.9% ±2.2% | 93.3% ±5.2% | 46.7% ±7.3% | 46.7% ±10.3% | 46.7% ±10.3% | 47.2% | 411 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 34333.9±20956.0 / 31682.1 / 72176.8 / 90133.8 |
| appweaver_tpl | 180 (60×3) | 94.4% ±3.3% | 98.9% ±2.2% | 90.0% ±6.2% | 30.0% ±6.7% | 25.6% ±9.0% | 34.4% ±9.8% | 30.6% | 403 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 26476.4±19140.8 / 19743.7 / 66054.0 / 91402.7 |
| langgraph_agentcard | 180 (60×3) | 93.9% ±3.5% | 100.0% ±0.0% | 87.8% ±6.8% | 20.6% ±5.9% | 12.2% ±6.8% | 28.9% ±9.4% | 20.6% | 388 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29909.1±20605.2 / 23295.3 / 76162.2 / 115142.3 |
| llm_only | 180 (60×3) | 60.0% ±7.2% | 98.9% ±2.2% | 21.1% ±8.4% | 49.4% ±7.3% | 98.9% ±2.2% | 0.0% ±0.0% | 51.1% | 552 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 4777.5±2278.1 / 4502.9 / 8857.8 / 15556.5 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| c_agv_cycle_deadline | 15 | 100.0% | 93.3% | 0.0% | 0.0% |
| c_aqm_right_away | 15 | 100.0% | 60.0% | 0.0% | 0.0% |
| c_ar_showroom_delay | 15 | 100.0% | 66.7% | 0.0% | 0.0% |
| c_boardroom_vip_slow | 15 | 73.3% | 73.3% | 6.7% | 0.0% |
| c_campus_throughput_drop | 15 | 40.0% | 40.0% | 6.7% | 0.0% |
| c_cctv_uplink_frames | 15 | 86.7% | 60.0% | 0.0% | 0.0% |
| c_codel_cell7 | 15 | 100.0% | 66.7% | 0.0% | 0.0% |
| c_concert_plan_signed_off | 15 | 100.0% | 66.7% | 0.0% | 0.0% |
| c_delay_spike_containment | 15 | 80.0% | 40.0% | 0.0% | 0.0% |
| c_drone_inspection_slice | 15 | 73.3% | 0.0% | 0.0% | 0.0% |
| c_dscp_ef_first | 15 | 100.0% | 33.3% | 0.0% | 0.0% |
| c_ecn_cutover_verify | 15 | 93.3% | 6.7% | 0.0% | 0.0% |
| c_ecn_default_bearer | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_edge_gaming_strict_priority | 15 | 100.0% | 26.7% | 0.0% | 0.0% |
| c_enterprise_partition_ack | 15 | 93.3% | 80.0% | 0.0% | 0.0% |
| c_esports_arena_jitter | 15 | 100.0% | 100.0% | 0.0% | 0.0% |
| c_full_queue_profile_cr | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_fwa_evening_calls | 15 | 100.0% | 86.7% | 0.0% | 0.0% |
| c_hospital_ue_outlier | 15 | 66.7% | 6.7% | 0.0% | 0.0% |
| c_hsr_rrc_churn | 15 | 80.0% | 80.0% | 6.7% | 0.0% |
| c_idle_embb_reservation | 15 | 80.0% | 0.0% | 0.0% | 0.0% |
| c_iot_telemetry_partition | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_lab_static_profile_push | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_lecture_hall_streaming | 15 | 100.0% | 66.7% | 0.0% | 0.0% |
| c_mall_rush_payment | 15 | 100.0% | 86.7% | 0.0% | 0.0% |
| c_marathon_media_slice | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_media_van_uploads | 15 | 80.0% | 40.0% | 0.0% | 0.0% |
| c_mission_critical_throughput | 15 | 73.3% | 0.0% | 6.7% | 0.0% |
| c_morning_sluggish | 15 | 0.0% | 0.0% | 0.0% | 0.0% |
| c_night_low_load_report | 15 | 80.0% | 80.0% | 0.0% | 0.0% |
| c_partner_jitter_report | 15 | 80.0% | 0.0% | 0.0% | 0.0% |
| c_platoon_v2x_delay | 15 | 100.0% | 80.0% | 0.0% | 0.0% |
| c_popup_slice_teardown | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_post_upgrade_slice_survival | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_prb_alarm_sanity | 15 | 20.0% | 6.7% | 0.0% | 0.0% |
| c_priority_ue_flow_remap | 15 | 80.0% | 80.0% | 0.0% | 0.0% |
| c_ran_sharing_entitlement | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_remote_ultrasound_stream | 15 | 100.0% | 100.0% | 0.0% | 0.0% |
| c_replication_shaper_ack | 15 | 80.0% | 13.3% | 0.0% | 0.0% |
| c_residential_peak_throughput | 15 | 100.0% | 73.3% | 0.0% | 0.0% |
| c_rlc_delay_dashboard | 15 | 80.0% | 80.0% | 0.0% | 0.0% |
| c_rlc_delay_gated_aqm | 15 | 80.0% | 66.7% | 0.0% | 0.0% |
| c_robotics_line_share | 15 | 80.0% | 0.0% | 0.0% | 0.0% |
| c_sharing_rebalance | 15 | 73.3% | 20.0% | 0.0% | 0.0% |
| c_sim_migration_slice_mapping | 15 | 93.3% | 13.3% | 0.0% | 0.0% |
| c_sla_dispute_evidence | 15 | 80.0% | 6.7% | 0.0% | 0.0% |
| c_slice_inventory | 15 | 100.0% | 6.7% | 0.0% | 0.0% |
| c_slice_quota_review | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_slice_rollback_confirm | 15 | 100.0% | 0.0% | 0.0% | 0.0% |
| c_software_update_cap | 15 | 100.0% | 26.7% | 0.0% | 0.0% |
| c_stadium_ue_throughput_snapshot | 15 | 80.0% | 80.0% | 0.0% | 0.0% |
| c_static_profile_trial | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_telemetry_ecn_switch | 15 | 80.0% | 13.3% | 0.0% | 0.0% |
| c_tenant_capacity_complaint | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_tenant_onboarding_check | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_transit_hub_voice | 15 | 80.0% | 0.0% | 0.0% | 0.0% |
| c_ue1_slice_lookup | 15 | 100.0% | 33.3% | 0.0% | 0.0% |
| c_urllc_sla_spotcheck | 15 | 100.0% | 20.0% | 0.0% | 0.0% |
| c_voice_queue_priority | 15 | 100.0% | 33.3% | 0.0% | 0.0% |
| c_vpn_standing_queue | 15 | 100.0% | 40.0% | 0.0% | 0.0% |
