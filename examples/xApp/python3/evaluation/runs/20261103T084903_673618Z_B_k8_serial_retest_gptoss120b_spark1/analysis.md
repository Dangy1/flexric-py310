# Evaluation Analysis

- records: 72
- methods: 6
- intents: 12

## Method Summary

Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.

| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| agentcard_no_repair | 12 (12×1) | 66.7% ±26.7% | n/a ±n/a | 66.7% ±26.7% | 25.0% ±24.5% | n/a ±n/a | 25.0% ±24.5% | 33.3% | 37 | 94.6% | 94.6% | 0 | n/a (0/0) | 16.7% | n/a | 32953.1±10542.6 / 31038.0 / 50076.5 / 54787.3 |
| langgraph_agentcard | 12 (12×1) | 75.0% ±24.5% | n/a ±n/a | 75.0% ±24.5% | 33.3% ±26.7% | n/a ±n/a | 33.3% ±26.7% | 33.3% | 38 | 94.7% | 94.7% | 0 | n/a (0/0) | 16.7% | n/a | 34244.5±4777.2 / 33824.4 / 37877.1 / 44282.5 |
| llm_blind | 12 (12×1) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 1 | 100.0% | 100.0% | 35 | n/a (0/0) | 0.0% | n/a | 13813.0±5414.1 / 13456.4 / 22184.7 / 25162.1 |
| llm_only | 12 (12×1) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 42 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 8372.5±1776.3 / 8129.1 / 10467.9 / 12717.6 |
| manual_rule | 12 (12×1) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 42 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 2.2±0.9 / 2.4 / 3.1 / 3.2 |
| single_xapp | 12 (12×1) | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% ±0.0% | n/a ±n/a | 0.0% ±0.0% | 0.0% | 12 | 100.0% | 100.0% | 0 | n/a (0/0) | 0.0% | n/a | 0.8±0.2 / 0.8 / 1.1 / 1.2 |

Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.

## Intent Summary

| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| anomaly_to_transport_fix | 6 | 0.0% | 0.0% | 0.0% | 0.0% |
| backhaul_policy_advice | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| cell_edge_qoe_protection | 6 | 33.3% | 33.3% | 0.0% | 16.7% |
| coverage_hole_tilt | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| deprecated_card_trap | 6 | 33.3% | 0.0% | 0.0% | 0.0% |
| energy_vs_capacity_conflict | 6 | 33.3% | 16.7% | 0.0% | 0.0% |
| healing_full_chain | 6 | 0.0% | 0.0% | 0.0% | 16.7% |
| interference_hotspot | 6 | 33.3% | 16.7% | 0.0% | 0.0% |
| load_balance_hotspot | 6 | 0.0% | 0.0% | 0.0% | 16.7% |
| meter_reconnect_storm | 6 | 16.7% | 0.0% | 0.0% | 0.0% |
| night_energy_saving | 6 | 33.3% | 16.7% | 0.0% | 0.0% |
| ping_pong_handover_fix | 6 | 33.3% | 33.3% | 0.0% | 16.7% |
