# Evaluation Analysis

- records: 1440
- methods: 8
- intents: 60

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 180 (60×3) | 93.9% ±3.5% | 92.2% ±5.5% | 95.6% ±4.3% | 24.4% ±6.3% | 18.9% ±8.1% | 30.0% ±9.5% | 24.4% | 381 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 31140.7±16701.0 / 26405.7 / 71911.3 / 85681.8 |
| appweaver_mem | 180 (60×3) | 96.1% ±2.8% | 96.7% ±3.7% | 95.6% ±4.3% | 48.9% ±7.3% | 58.9% ±10.2% | 38.9% ±10.1% | 49.4% | 368 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 30978.1±15293.0 / 27606.7 / 61913.8 / 90363.7 |
| appweaver_tpl | 180 (60×3) | 96.1% ±2.8% | 96.7% ±3.7% | 95.6% ±4.3% | 40.0% ±7.2% | 44.4% ±10.3% | 35.6% ±9.9% | 40.0% | 381 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29614.5±13868.8 / 26669.4 / 58065.8 / 74657.9 |
| langgraph_agentcard | 180 (60×3) | 93.9% ±3.5% | 92.2% ±5.5% | 95.6% ±4.3% | 22.8% ±6.1% | 13.3% ±7.0% | 32.2% ±9.7% | 22.8% | 380 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29871.5±15354.2 / 26018.5 / 63965.0 / 91225.4 |
| llm_blind | 180 (60×3) | 0.6% ±1.1% | 0.0% ±0.0% | 1.1% ±2.2% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 21 | 100.0% | 100.0% | 534 | n/a (0/0) | 0.0% | n/a | 18925.9±7422.8 / 18565.3 / 30006.8 / 49462.2 |
| llm_only | 180 (60×3) | 53.3% ±7.3% | 88.9% ±6.5% | 17.8% ±7.9% | 44.4% ±7.3% | 88.9% ±6.5% | 0.0% ±0.0% | 47.2% | 552 | 100.0% | 99.8% | 0 | n/a (0/0) | 0.0% | n/a | 9286.5±2896.7 / 8547.8 / 15026.1 / 20669.3 |
| manual_rule | 180 (60×3) | 20.0% ±5.8% | 36.7% ±10.0% | 3.3% ±3.7% | 18.3% ±5.7% | 36.7% ±10.0% | 0.0% ±0.0% | 18.3% | 648 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 2.2±0.9 / 2.5 / 3.2 / 3.5 |
| single_xapp | 180 (60×3) | 21.7% ±6.0% | 10.0% ±6.2% | 33.3% ±9.7% | 10.0% ±4.4% | 10.0% ±6.2% | 10.0% ±6.2% | 10.0% | 180 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 0.8±0.2 / 0.9 / 1.1 / 1.4 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| c_agv_cycle_deadline | 24 | 75.0% | 75.0% | 0.0% | 0.0% |
| c_aqm_right_away | 24 | 62.5% | 45.8% | 0.0% | 0.0% |
| c_ar_showroom_delay | 24 | 75.0% | 58.3% | 0.0% | 0.0% |
| c_boardroom_vip_slow | 24 | 62.5% | 50.0% | 0.0% | 0.0% |
| c_campus_throughput_drop | 24 | 16.7% | 0.0% | 0.0% | 0.0% |
| c_cctv_uplink_frames | 24 | 25.0% | 25.0% | 0.0% | 0.0% |
| c_codel_cell7 | 24 | 62.5% | 37.5% | 0.0% | 0.0% |
| c_concert_plan_signed_off | 24 | 79.2% | 4.2% | 0.0% | 0.0% |
| c_delay_spike_containment | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_drone_inspection_slice | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_dscp_ef_first | 24 | 87.5% | 54.2% | 0.0% | 0.0% |
| c_ecn_cutover_verify | 24 | 50.0% | 12.5% | 0.0% | 0.0% |
| c_ecn_default_bearer | 24 | 62.5% | 45.8% | 0.0% | 0.0% |
| c_edge_gaming_strict_priority | 24 | 87.5% | 54.2% | 0.0% | 0.0% |
| c_enterprise_partition_ack | 24 | 50.0% | 45.8% | 0.0% | 0.0% |
| c_esports_arena_jitter | 24 | 75.0% | 75.0% | 0.0% | 0.0% |
| c_full_queue_profile_cr | 24 | 54.2% | 25.0% | 0.0% | 0.0% |
| c_fwa_evening_calls | 24 | 54.2% | 54.2% | 0.0% | 0.0% |
| c_hospital_ue_outlier | 24 | 62.5% | 4.2% | 0.0% | 0.0% |
| c_hsr_rrc_churn | 24 | 62.5% | 50.0% | 0.0% | 0.0% |
| c_idle_embb_reservation | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_iot_telemetry_partition | 24 | 62.5% | 37.5% | 0.0% | 0.0% |
| c_lab_static_profile_push | 24 | 62.5% | 37.5% | 0.0% | 0.0% |
| c_lecture_hall_streaming | 24 | 75.0% | 33.3% | 0.0% | 0.0% |
| c_mall_rush_payment | 24 | 75.0% | 37.5% | 0.0% | 0.0% |
| c_marathon_media_slice | 24 | 58.3% | 12.5% | 0.0% | 0.0% |
| c_media_van_uploads | 24 | 50.0% | 4.2% | 0.0% | 0.0% |
| c_mission_critical_throughput | 24 | 50.0% | 4.2% | 0.0% | 0.0% |
| c_morning_sluggish | 24 | 50.0% | 12.5% | 0.0% | 0.0% |
| c_night_low_load_report | 24 | 62.5% | 62.5% | 0.0% | 0.0% |
| c_partner_jitter_report | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_platoon_v2x_delay | 24 | 62.5% | 33.3% | 0.0% | 0.0% |
| c_popup_slice_teardown | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_post_upgrade_slice_survival | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_prb_alarm_sanity | 24 | 54.2% | 0.0% | 0.0% | 0.0% |
| c_priority_ue_flow_remap | 24 | 50.0% | 50.0% | 0.0% | 0.0% |
| c_ran_sharing_entitlement | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_remote_ultrasound_stream | 24 | 50.0% | 50.0% | 0.0% | 0.0% |
| c_replication_shaper_ack | 24 | 54.2% | 0.0% | 0.0% | 0.0% |
| c_residential_peak_throughput | 24 | 75.0% | 70.8% | 0.0% | 0.0% |
| c_rlc_delay_dashboard | 24 | 62.5% | 62.5% | 0.0% | 0.0% |
| c_rlc_delay_gated_aqm | 24 | 50.0% | 41.7% | 0.0% | 0.0% |
| c_robotics_line_share | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_sharing_rebalance | 24 | 50.0% | 4.2% | 0.0% | 0.0% |
| c_sim_migration_slice_mapping | 24 | 58.3% | 8.3% | 0.0% | 0.0% |
| c_sla_dispute_evidence | 24 | 62.5% | 0.0% | 0.0% | 0.0% |
| c_slice_inventory | 24 | 62.5% | 0.0% | 0.0% | 0.0% |
| c_slice_quota_review | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_slice_rollback_confirm | 24 | 62.5% | 0.0% | 0.0% | 0.0% |
| c_software_update_cap | 24 | 62.5% | 25.0% | 0.0% | 0.0% |
| c_stadium_ue_throughput_snapshot | 24 | 62.5% | 62.5% | 0.0% | 0.0% |
| c_static_profile_trial | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_telemetry_ecn_switch | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_tenant_capacity_complaint | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_tenant_onboarding_check | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_transit_hub_voice | 24 | 50.0% | 0.0% | 0.0% | 0.0% |
| c_ue1_slice_lookup | 24 | 62.5% | 41.7% | 0.0% | 0.0% |
| c_urllc_sla_spotcheck | 24 | 62.5% | 12.5% | 0.0% | 0.0% |
| c_voice_queue_priority | 24 | 62.5% | 33.3% | 0.0% | 0.0% |
| c_vpn_standing_queue | 24 | 87.5% | 50.0% | 0.0% | 0.0% |
