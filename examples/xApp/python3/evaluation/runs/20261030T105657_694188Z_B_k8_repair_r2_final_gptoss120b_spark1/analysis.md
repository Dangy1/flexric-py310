# Evaluation Analysis

- records: 144
- methods: 6
- intents: 12

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 24 (12×2) | 70.8% ±18.2% | 100.0% ±0.0% | 68.2% ±19.5% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 61 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 33471.6±15468.0 / 29980.4 / 71755.4 / 72681.0 |
| langgraph_agentcard | 24 (12×2) | 70.8% ±18.2% | 100.0% ±0.0% | 68.2% ±19.5% | 4.2% ±8.0% | 0.0% ±0.0% | 4.5% ±8.7% | 4.2% | 60 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 33232.6±11433.4 / 33270.6 / 47761.7 / 64494.2 |
| llm_blind | 24 (12×2) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 2 | 100.0% | 100.0% | 74 | n/a (0/0) | 0.0% | n/a | 12972.2±5536.7 / 10987.6 / 24025.2 / 27055.3 |
| llm_only | 24 (12×2) | 25.0% ±17.3% | 100.0% ±0.0% | 18.2% ±16.1% | 25.0% ±17.3% | 100.0% ±0.0% | 18.2% ±16.1% | 25.0% | 82 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 7706.2±1917.4 / 7097.6 / 12668.5 / 13113.1 |
| manual_rule | 24 (12×2) | 16.7% ±14.9% | 0.0% ±0.0% | 18.2% ±16.1% | 16.7% ±14.9% | 0.0% ±0.0% | 18.2% ±16.1% | 16.7% | 72 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 1.7±1.0 / 1.5 / 3.2 / 3.8 |
| single_xapp | 24 (12×2) | 8.3% ±11.1% | 0.0% ±0.0% | 9.1% ±12.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 24 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 0.9±0.2 / 0.9 / 1.1 / 1.1 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| edge_gaming_jitter_protection | 12 | 41.7% | 33.3% | 0.0% | 0.0% |
| enterprise_slice_audit | 12 | 50.0% | 16.7% | 0.0% | 0.0% |
| gtp_tunnel_health_validation | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| handover_ping_pong_detection | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
| mmtc_capacity_preservation | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| mobility_hotspot_stabilization | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| pdcp_reorder_investigation | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| slice_admission_control | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
| slice_oversubscription_repair | 12 | 8.3% | 0.0% | 0.0% | 0.0% |
| urllc_reliability_safeguard | 12 | 66.7% | 41.7% | 0.0% | 0.0% |
| video_throughput_smoothing | 12 | 33.3% | 0.0% | 0.0% | 0.0% |
| volte_latency_safeguard | 12 | 16.7% | 0.0% | 0.0% | 0.0% |
