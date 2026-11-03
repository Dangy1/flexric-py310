# Evaluation Analysis

- records: 108
- methods: 6
- intents: 6

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 18 (6×3) | 44.4% ±23.0% | 50.0% ±40.0% | 41.7% ±27.9% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 44 | 79.5% | 79.5% | 0 | 44.4% (8/18) | n/a | 0.0% | 25553.6±13037.6 / 22067.3 / 33436.3 / 67580.1 |
| langgraph_agentcard | 18 (6×3) | 44.4% ±23.0% | 50.0% ±40.0% | 41.7% ±27.9% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 35 | 100.0% | 100.0% | 0 | 44.4% (8/18) | n/a | 0.0% | 26137.9±15923.8 / 17816.6 / 35529.0 / 81533.1 |
| llm_blind | 18 (6×3) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 0 | n/a | n/a | 44 | 0.0% (0/18) | n/a | 0.0% | 15006.5±5833.4 / 13004.2 / 26282.9 / 27083.0 |
| llm_only | 18 (6×3) | 11.1% ±14.5% | 33.3% ±37.7% | 0.0% ±0.0% | 11.1% ±14.5% | 33.3% ±37.7% | 0.0% ±0.0% | 22.2% | 62 | 85.5% | 85.5% | 0 | 44.4% (8/18) | n/a | 0.0% | 20107.8±14391.1 / 10247.0 / 33597.4 / 52470.4 |
| manual_rule | 18 (6×3) | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% | 54 | 63.0% | 63.0% | 0 | 100.0% (18/18) | n/a | 0.0% | 34469.5±3805.1 / 33558.4 / 45145.7 / 45155.1 |
| single_xapp | 18 (6×3) | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% | 30 | 60.0% | 60.0% | 0 | 66.7% (12/18) | n/a | 0.0% | 22150.4±15667.1 / 32559.2 / 33561.2 / 33561.3 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| backhaul_queue_conflict_recovery | 18 | 22.2% | 0.0% | 0.0% | 66.7% |
| enterprise_tunnel_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| latency_under_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| slice_policy_race_recovery | 18 | 33.3% | 0.0% | 0.0% | 66.7% |
| tc_conflict_recovery | 18 | 77.8% | 44.4% | 0.0% | 83.3% |
| unknown_busy_runtime_recovery | 18 | 0.0% | 0.0% | 0.0% | 16.7% |
