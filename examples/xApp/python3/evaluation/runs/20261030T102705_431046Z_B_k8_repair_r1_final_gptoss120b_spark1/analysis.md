# Evaluation Analysis

- records: 102
- methods: 6
- intents: 17

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 17 (17×1) | 76.5% ±20.2% | 50.0% ±49.0% | 84.6% ±19.6% | 17.6% ±18.1% | 0.0% ±0.0% | 23.1% ±22.9% | 29.4% | 38 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 27402.0±10163.2 / 26268.5 / 44415.6 / 45974.3 |
| langgraph_agentcard | 17 (17×1) | 64.7% ±22.7% | 50.0% ±49.0% | 69.2% ±25.1% | 29.4% ±21.7% | 0.0% ±0.0% | 38.5% ±26.4% | 29.4% | 37 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 27844.4±14312.8 / 22326.8 / 48229.6 / 72559.8 |
| llm_blind | 17 (17×1) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 0 | n/a | n/a | 48 | n/a (0/0) | 0.0% | n/a | 14572.0±6039.9 / 14136.3 / 25874.9 / 26524.2 |
| llm_only | 17 (17×1) | 29.4% ±21.7% | 100.0% ±0.0% | 7.7% ±14.5% | 29.4% ±21.7% | 100.0% ±0.0% | 7.7% ±14.5% | 29.4% | 64 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 7351.3±1253.2 / 7174.0 / 9406.5 / 10340.2 |
| manual_rule | 17 (17×1) | 23.5% ±20.2% | 75.0% ±42.4% | 7.7% ±14.5% | 23.5% ±20.2% | 75.0% ±42.4% | 7.7% ±14.5% | 23.5% | 59 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 2.1±0.8 / 2.4 / 3.1 / 3.3 |
| single_xapp | 17 (17×1) | 17.6% ±18.1% | 25.0% ±42.4% | 15.4% ±19.6% | 5.9% ±11.2% | 25.0% ±42.4% | 0.0% ±0.0% | 5.9% | 17 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 0.8±0.2 / 0.8 / 1.1 / 1.2 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| antenna_swap_wrong_sector | 6 | 33.3% | 33.3% | 0.0% | 0.0% |
| arena_concert_profile | 6 | 33.3% | 16.7% | 0.0% | 0.0% |
| bearer_buffer_buildup | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| edge_gaming_jitter_protection | 6 | 50.0% | 33.3% | 0.0% | 0.0% |
| enterprise_slice_audit | 6 | 50.0% | 16.7% | 0.0% | 0.0% |
| fair_boost_vs_night_saving | 6 | 33.3% | 16.7% | 0.0% | 0.0% |
| gtp_tunnel_health_validation | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 6 | 16.7% | 0.0% | 0.0% | 0.0% |
| handover_resilience_triage | 6 | 33.3% | 33.3% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 6 | 16.7% | 0.0% | 0.0% | 0.0% |
| pdcp_discard_check | 6 | 33.3% | 33.3% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| radio_capacity_headroom | 6 | 33.3% | 33.3% | 0.0% | 0.0% |
| rlc_queue_anomaly_detection | 6 | 50.0% | 0.0% | 0.0% | 0.0% |
| slice_admission_control | 6 | 0.0% | 0.0% | 0.0% | 0.0% |
| transport_tunnel_stability | 6 | 83.3% | 50.0% | 0.0% | 0.0% |
| ue_link_quality_snapshot | 6 | 33.3% | 33.3% | 0.0% | 0.0% |
