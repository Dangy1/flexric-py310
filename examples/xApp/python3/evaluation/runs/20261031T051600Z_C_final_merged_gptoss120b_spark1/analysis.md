# Evaluation Analysis

- records: 1980
- methods: 11
- intents: 60

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 180 (60×3) | 93.9% ±3.5% | 92.2% ±5.5% | 95.6% ±4.3% | 24.4% ±6.3% | 18.9% ±8.1% | 30.0% ±9.5% | 24.4% | 381 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 31140.7±16701.0 / 26405.7 / 71911.3 / 85681.8 |
| appweaver_guided | 180 (60×3) | 78.3% ±6.0% | 66.7% ±9.7% | 90.0% ±6.2% | 20.0% ±5.8% | 24.4% ±8.9% | 15.6% ±7.5% | 21.7% | 312 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 39002.5±15050.6 / 35423.4 / 67559.2 / 126406.0 |
| appweaver_mem | 180 (60×3) | 96.1% ±2.8% | 96.7% ±3.7% | 95.6% ±4.3% | 48.9% ±7.3% | 58.9% ±10.2% | 38.9% ±10.1% | 49.4% | 368 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 30978.1±15293.0 / 27606.7 / 61913.8 / 90363.7 |
| appweaver_mem2 | 180 (60×3) | 96.1% ±2.8% | 96.7% ±3.7% | 95.6% ±4.3% | 47.8% ±7.3% | 54.4% ±10.3% | 41.1% ±10.2% | 47.8% | 380 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29686.5±14412.4 / 26798.0 / 58015.0 / 85054.1 |
| appweaver_tpl | 180 (60×3) | 96.1% ±2.8% | 96.7% ±3.7% | 95.6% ±4.3% | 40.0% ±7.2% | 44.4% ±10.3% | 35.6% ±9.9% | 40.0% | 381 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29614.5±13868.8 / 26669.4 / 58065.8 / 74657.9 |
| appweaver_v2 | 180 (60×3) | 83.3% ±5.4% | 71.1% ±9.4% | 95.6% ±4.3% | 22.8% ±6.1% | 30.0% ±9.5% | 15.6% ±7.5% | 24.4% | 313 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 42197.5±15883.7 / 40531.4 / 70699.9 / 82363.4 |
| langgraph_agentcard | 180 (60×3) | 93.9% ±3.5% | 92.2% ±5.5% | 95.6% ±4.3% | 22.8% ±6.1% | 13.3% ±7.0% | 32.2% ±9.7% | 22.8% | 380 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 29871.5±15354.2 / 26018.5 / 63965.0 / 91225.4 |
| llm_blind | 180 (60×3) | 0.6% ±1.1% | 0.0% ±0.0% | 1.1% ±2.2% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 21 | 100.0% | 100.0% | 534 | n/a (0/0) | 0.0% | n/a | 18925.9±7422.8 / 18565.3 / 30006.8 / 49462.2 |
| llm_only | 180 (60×3) | 53.3% ±7.3% | 88.9% ±6.5% | 17.8% ±7.9% | 44.4% ±7.3% | 88.9% ±6.5% | 0.0% ±0.0% | 47.2% | 552 | 100.0% | 99.8% | 0 | n/a (0/0) | 0.0% | n/a | 9286.5±2896.7 / 8547.8 / 15026.1 / 20669.3 |
| manual_rule | 180 (60×3) | 20.0% ±5.8% | 36.7% ±10.0% | 3.3% ±3.7% | 18.3% ±5.7% | 36.7% ±10.0% | 0.0% ±0.0% | 18.3% | 648 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 2.2±0.9 / 2.5 / 3.2 / 3.5 |
| single_xapp | 180 (60×3) | 21.7% ±6.0% | 10.0% ±6.2% | 33.3% ±9.7% | 10.0% ±4.4% | 10.0% ±6.2% | 10.0% ±6.2% | 10.0% | 180 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 0.8±0.2 / 0.9 / 1.1 / 1.4 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| c_agv_cycle_deadline | 33 | 66.7% | 63.6% | 0.0% | 0.0% |
| c_aqm_right_away | 33 | 72.7% | 57.6% | 0.0% | 0.0% |
| c_ar_showroom_delay | 33 | 81.8% | 51.5% | 0.0% | 0.0% |
| c_boardroom_vip_slow | 33 | 66.7% | 57.6% | 0.0% | 0.0% |
| c_campus_throughput_drop | 33 | 33.3% | 3.0% | 0.0% | 0.0% |
| c_cctv_uplink_frames | 33 | 33.3% | 18.2% | 0.0% | 0.0% |
| c_codel_cell7 | 33 | 72.7% | 48.5% | 0.0% | 0.0% |
| c_concert_plan_signed_off | 33 | 84.8% | 9.1% | 0.0% | 0.0% |
| c_delay_spike_containment | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_drone_inspection_slice | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_dscp_ef_first | 33 | 90.9% | 60.6% | 0.0% | 0.0% |
| c_ecn_cutover_verify | 33 | 63.6% | 18.2% | 0.0% | 0.0% |
| c_ecn_default_bearer | 33 | 72.7% | 60.6% | 0.0% | 0.0% |
| c_edge_gaming_strict_priority | 33 | 90.9% | 66.7% | 0.0% | 0.0% |
| c_enterprise_partition_ack | 33 | 45.5% | 36.4% | 0.0% | 0.0% |
| c_esports_arena_jitter | 33 | 63.6% | 63.6% | 0.0% | 0.0% |
| c_full_queue_profile_cr | 33 | 66.7% | 27.3% | 0.0% | 0.0% |
| c_fwa_evening_calls | 33 | 63.6% | 48.5% | 0.0% | 0.0% |
| c_hospital_ue_outlier | 33 | 72.7% | 9.1% | 0.0% | 0.0% |
| c_hsr_rrc_churn | 33 | 72.7% | 45.5% | 0.0% | 0.0% |
| c_idle_embb_reservation | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_iot_telemetry_partition | 33 | 72.7% | 45.5% | 0.0% | 0.0% |
| c_lab_static_profile_push | 33 | 72.7% | 33.3% | 0.0% | 0.0% |
| c_lecture_hall_streaming | 33 | 81.8% | 33.3% | 0.0% | 0.0% |
| c_mall_rush_payment | 33 | 69.7% | 36.4% | 0.0% | 0.0% |
| c_marathon_media_slice | 33 | 69.7% | 9.1% | 0.0% | 0.0% |
| c_media_van_uploads | 33 | 63.6% | 6.1% | 0.0% | 0.0% |
| c_mission_critical_throughput | 33 | 63.6% | 3.0% | 0.0% | 0.0% |
| c_morning_sluggish | 33 | 54.5% | 9.1% | 0.0% | 0.0% |
| c_night_low_load_report | 33 | 72.7% | 72.7% | 0.0% | 0.0% |
| c_partner_jitter_report | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_platoon_v2x_delay | 33 | 72.7% | 33.3% | 0.0% | 0.0% |
| c_popup_slice_teardown | 33 | 54.5% | 9.1% | 0.0% | 0.0% |
| c_post_upgrade_slice_survival | 33 | 54.5% | 9.1% | 0.0% | 0.0% |
| c_prb_alarm_sanity | 33 | 66.7% | 0.0% | 0.0% | 0.0% |
| c_priority_ue_flow_remap | 33 | 63.6% | 63.6% | 0.0% | 0.0% |
| c_ran_sharing_entitlement | 33 | 48.5% | 3.0% | 0.0% | 0.0% |
| c_remote_ultrasound_stream | 33 | 63.6% | 45.5% | 0.0% | 0.0% |
| c_replication_shaper_ack | 33 | 66.7% | 0.0% | 0.0% | 0.0% |
| c_residential_peak_throughput | 33 | 81.8% | 60.6% | 0.0% | 0.0% |
| c_rlc_delay_dashboard | 33 | 72.7% | 72.7% | 0.0% | 0.0% |
| c_rlc_delay_gated_aqm | 33 | 63.6% | 39.4% | 0.0% | 0.0% |
| c_robotics_line_share | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_sharing_rebalance | 33 | 63.6% | 3.0% | 0.0% | 0.0% |
| c_sim_migration_slice_mapping | 33 | 69.7% | 6.1% | 0.0% | 0.0% |
| c_sla_dispute_evidence | 33 | 72.7% | 0.0% | 0.0% | 0.0% |
| c_slice_inventory | 33 | 66.7% | 6.1% | 0.0% | 0.0% |
| c_slice_quota_review | 33 | 45.5% | 0.0% | 0.0% | 0.0% |
| c_slice_rollback_confirm | 33 | 72.7% | 0.0% | 0.0% | 0.0% |
| c_software_update_cap | 33 | 72.7% | 36.4% | 0.0% | 0.0% |
| c_stadium_ue_throughput_snapshot | 33 | 72.7% | 72.7% | 0.0% | 0.0% |
| c_static_profile_trial | 33 | 72.7% | 9.1% | 0.0% | 0.0% |
| c_telemetry_ecn_switch | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_tenant_capacity_complaint | 33 | 57.6% | 9.1% | 0.0% | 0.0% |
| c_tenant_onboarding_check | 33 | 57.6% | 9.1% | 0.0% | 0.0% |
| c_transit_hub_voice | 33 | 63.6% | 0.0% | 0.0% | 0.0% |
| c_ue1_slice_lookup | 33 | 66.7% | 36.4% | 0.0% | 0.0% |
| c_urllc_sla_spotcheck | 33 | 54.5% | 9.1% | 0.0% | 0.0% |
| c_voice_queue_priority | 33 | 72.7% | 45.5% | 0.0% | 0.0% |
| c_vpn_standing_queue | 33 | 90.9% | 60.6% | 0.0% | 0.0% |
