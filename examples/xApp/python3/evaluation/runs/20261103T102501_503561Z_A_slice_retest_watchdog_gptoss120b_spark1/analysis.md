# Evaluation Analysis

- records: 18
- methods: 6
- intents: 1

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 3 (1×3) | 100.0% ±0.0% | n/a ±n/a | 100.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 9 | 66.7% | 66.7% | 0 | 100.0% (3/3) | n/a | 0.0% | 35086.7±1856.6 / 36185.6 / 36602.3 / 36602.3 |
| langgraph_agentcard | 3 (1×3) | 100.0% ±0.0% | n/a ±n/a | 100.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 6 | 100.0% | 100.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 33782.6±2027.9 / 32451.1 / 36648.0 / 36648.0 |
| llm_blind | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 2 | 50.0% | 50.0% | 7 | 33.3% (1/3) | n/a | 0.0% | 18746.1±9573.9 / 12718.2 / 32259.5 / 32259.5 |
| llm_only | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 15 | 80.0% | 80.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 32342.4±137.8 / 32385.9 / 32485.0 / 32485.0 |
| manual_rule | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 15 | 80.0% | 80.0% | 0 | 100.0% (3/3) | n/a | 0.0% | 33937.5±1894.6 / 32599.0 / 36616.9 / 36616.9 |
| single_xapp | 3 (1×3) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 3 | 100.0% | 100.0% | 0 | 0.0% (0/3) | n/a | 0.0% | 0.7±0.3 / 0.8 / 0.9 / 0.9 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| slice_policy_race_recovery | 18 | 33.3% | 0.0% | 0.0% | 72.2% |
