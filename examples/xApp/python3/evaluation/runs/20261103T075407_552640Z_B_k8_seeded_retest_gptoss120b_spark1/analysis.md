# Evaluation Analysis

- records: 108
- methods: 6
- intents: 6

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 18 (6×3) | 27.8% ±20.7% | 50.0% ±40.0% | 16.7% ±21.1% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 5.6% | 57 | 80.7% | 80.7% | 0 | 44.4% (8/18) | n/a | 0.0% | 34098.4±17800.7 / 30360.9 / 73429.5 / 73677.9 |
| langgraph_agentcard | 18 (6×3) | 33.3% ±21.8% | 50.0% ±40.0% | 25.0% ±24.5% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 52 | 100.0% | 100.0% | 0 | 50.0% (9/18) | n/a | 0.0% | 31646.7±9199.8 / 33759.4 / 42208.2 / 44329.6 |
| llm_blind | 18 (6×3) | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% ±0.0% | 0.0% | 7 | 71.4% | 71.4% | 51 | 11.1% (2/18) | n/a | 0.0% | 16225.1±7571.8 / 13649.8 / 33553.8 / 33583.1 |
| llm_only | 18 (6×3) | 5.6% ±10.6% | 16.7% ±29.8% | 0.0% ±0.0% | 5.6% ±10.6% | 16.7% ±29.8% | 0.0% ±0.0% | 5.6% | 67 | 83.6% | 83.6% | 0 | 44.4% (8/18) | n/a | 0.0% | 22335.9±18061.5 / 9174.3 / 54904.9 / 55411.9 |
| manual_rule | 18 (6×3) | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% | 54 | 61.1% | 61.1% | 0 | 100.0% (18/18) | n/a | 0.0% | 35266.2±4428.8 / 33547.7 / 45135.7 / 45157.8 |
| single_xapp | 18 (6×3) | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% ±17.2% | 50.0% ±40.0% | 0.0% ±0.0% | 16.7% | 30 | 60.0% | 60.0% | 0 | 66.7% (12/18) | n/a | 0.0% | 22257.4±15741.0 / 33543.2 / 33562.4 / 33563.3 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| backhaul_queue_conflict_recovery | 18 | 0.0% | 0.0% | 0.0% | 72.2% |
| enterprise_tunnel_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| latency_under_busy_tc | 18 | 0.0% | 0.0% | 0.0% | 33.3% |
| slice_policy_race_recovery | 18 | 27.8% | 0.0% | 0.0% | 66.7% |
| tc_conflict_recovery | 18 | 72.2% | 38.9% | 0.0% | 94.4% |
| unknown_busy_runtime_recovery | 18 | 0.0% | 0.0% | 0.0% | 16.7% |
