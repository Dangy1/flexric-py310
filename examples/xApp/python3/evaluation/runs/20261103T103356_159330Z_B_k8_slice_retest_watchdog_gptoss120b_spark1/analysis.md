# Evaluation Analysis

- records: 18
- methods: 6
- intents: 1

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 3 (1×3) | 100.0% ±0.0% | n/a ±n/a | 100.0% ±0.0% | 33.3% ±53.3% | n/a ±n/a | 33.3% ±53.3% | 33.3% | 11 | 72.7% | 72.7% | 0 | 100.0% (3/3) | n/a | 0.0% | 36404.9±80.6 / 36414.6 / 36498.4 / 36498.4 |
| langgraph_agentcard | 3 (1×3) | 66.7% ±53.3% | n/a ±n/a | 66.7% ±53.3% | 33.3% ±53.3% | n/a ±n/a | 33.3% ±53.3% | 33.3% | 8 | 100.0% | 100.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 40899.1±1171.6 / 41297.8 / 42092.6 / 42092.6 |
| llm_blind | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 0 | n/a | n/a | 8 | 0.0% (0/3) | n/a | 0.0% | 12135.7±1243.6 / 12745.5 / 13259.4 / 13259.4 |
| llm_only | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 15 | 80.0% | 80.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 33745.7±1967.0 / 32492.6 / 36523.0 / 36523.0 |
| manual_rule | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 15 | 80.0% | 80.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 33937.2±1890.8 / 32602.2 / 36611.2 / 36611.2 |
| single_xapp | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 3 | 100.0% | 100.0% | 0 | 0.0% (0/3) | n/a | 0.0% | 0.6±0.2 / 0.6 / 0.9 / 0.9 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| slice_policy_race_recovery | 18 | 27.8% | 11.1% | 0.0% | 66.7% |
