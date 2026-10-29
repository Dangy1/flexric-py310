# Evaluation Analysis

- records: 180
- methods: 6
- intents: 6

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 30 (6×5) | 50.0% ±17.9% | 50.0% ±31.0% | 50.0% ±21.9% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 76 | 81.6% | 68.4% | 0 | 50.0% (15/30) | n/a | 0.0% | 33631.9±15520.5 / 32227.2 / 64201.7 / 94320.4 |
| langgraph_agentcard | 30 (6×5) | 36.7% ±17.2% | 50.0% ±31.0% | 30.0% ±20.1% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 63 | 100.0% | 85.7% | 0 | 36.7% (11/30) | n/a | 36.7% | 29986.6±8814.7 / 26566.3 / 42829.4 / 51164.6 |
| llm_blind | 30 (6×5) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 7 | 85.7% | 57.1% | 75 | 3.3% (1/30) | n/a | 0.0% | 16327.3±6230.5 / 13601.0 / 28836.7 / 33324.2 |
| llm_only | 30 (6×5) | 13.3% ±12.2% | 40.0% ±30.4% | 0.0% ±0.0% | 13.3% ±12.2% | 40.0% ±30.4% | 0.0% ±0.0% | 13.3% | 102 | 87.3% | 87.3% | 0 | 40.0% (12/30) | n/a | 0.0% | 20076.1±15607.4 / 8534.1 / 42721.2 / 55638.0 |
| manual_rule | 30 (6×5) | 16.7% ±13.3% | 50.0% ±31.0% | 0.0% ±0.0% | 16.7% ±13.3% | 50.0% ±31.0% | 0.0% ±0.0% | 16.7% | 90 | 65.6% | 65.6% | 0 | 100.0% (30/30) | n/a | 0.0% | 36775.6±3778.6 / 36082.9 / 42582.2 / 45087.9 |
| single_xapp | 30 (6×5) | 16.7% ±13.3% | 50.0% ±31.0% | 0.0% ±0.0% | 16.7% ±13.3% | 50.0% ±31.0% | 0.0% ±0.0% | 16.7% | 50 | 60.0% | 60.0% | 0 | 66.7% (20/30) | n/a | 0.0% | 24366.7±17470.3 / 33546.1 / 40556.7 / 40556.8 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| backhaul_queue_conflict_recovery | 30 | 20.0% | 0.0% | 0.0% | 63.3% |
| enterprise_tunnel_busy_tc | 30 | 0.0% | 0.0% | 0.0% | 33.3% |
| latency_under_busy_tc | 30 | 0.0% | 0.0% | 0.0% | 33.3% |
| slice_policy_race_recovery | 30 | 33.3% | 0.0% | 0.0% | 66.7% |
| tc_conflict_recovery | 30 | 80.0% | 46.7% | 0.0% | 83.3% |
| unknown_busy_runtime_recovery | 30 | 0.0% | 0.0% | 0.0% | 16.7% |
