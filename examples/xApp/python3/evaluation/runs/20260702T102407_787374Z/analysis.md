# Evaluation Analysis

- records: 4
- methods: 2
- intents: 2

## Method Summary

| Method | Runs | Available runs | Workflow accuracy | Known accuracy | Open-world accuracy | Custom workflow rate | Tool success | Non-observation tool success | Cached observation rate | Policy validity | Hallucination | Recovery | Internal recovery | Conflict detection | Avg orchestration latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| langgraph_agentcard | 2 | 2 (100.0%) | 100.0% | 100.0% | n/a | 0.0% | 100.0% | 100.0% | 50.0% | 100.0% | 0.0% | n/a | n/a | 100.0% | 15964.0 |
| llm_only | 2 | 2 (100.0%) | 100.0% | 100.0% | n/a | 0.0% | 100.0% | 100.0% | 50.0% | 100.0% | 0.0% | n/a | n/a | 100.0% | 10941.2 |

## Intent Summary

| Intent ID | Runs | Workflow match | Failure rate | Conflict rate |
| --- | ---: | ---: | ---: | ---: |
| congestion_relief | 2 | 100.0% | 0.0% | 0.0% |
| xr_latency_guard | 2 | 100.0% | 0.0% | 0.0% |
