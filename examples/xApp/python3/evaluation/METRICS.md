# Evaluation metrics (definitions used by `analyze_results.py`)

All rates are over *available* records (records whose method could run; a method whose planner
provider was unreachable is marked unavailable and excluded, and the count is reported).
A record is one (intent, method, repeat). Accuracies carry a normal-approximation 95% CI half-width.

| Metric | Definition | Denominator |
|---|---|---|
| **Workflow accuracy** | `generated_workflow == expected_workflow` (ordered, exact) | available records |
| Known / open-world accuracy | same, split by `intent.open_world` | known / open-world records |
| **Set accuracy** | same capability set as any accepted chain, order ignored, non-empty | available records |
| Accepted accuracy | exact ordered match with *any* chain in `intent.accepted_workflows` (defaults to the single expected chain) | available records |
| **Tool calls** | number of application invocations the method issued (one per `(agent, action)` launch, including cached observations and calls that were refused) | — |
| Launched | call's launch status is `running/starting/completed` (the xApp process started) | tool calls |
| **Acknowledged** | within `--tool-ack-timeout-s` the run log shows evidence of real work: KPM records for observation, a subscription/`Applied …` line for slice/TC control, an RC subscription line for validation (markers in `run_harness.TOOL_ACK_MARKERS`). Refused/queued/failed calls are unacknowledged. | tool calls with a verdict |
| **Hallucinated references** | count of application names in the generated workflow, or `(agent, action)` pairs in tool calls, that do not exist in the Agent Registry | summed over records |
| **Conflict recall** | seeded-conflict records where the method flagged the conflict *before* issuing control (`conflict_detected`: lease/queue refusal, blocked reason, twin rejection) | seeded records (6 intents × repeats) |
| Conflict precision | TP / (TP + FP) where FP = unseeded records flagged as conflict | — |
| Conflict FP rate | unseeded records flagged as conflict | unseeded records |
| Seeded recovered | seeded records where the method's *internal* recovery produced a clean execution after the conflict | seeded records |
| **Latency** | wall-clock from intent submission to a validated, launched plan (planner calls + validation + launch). Excludes the acknowledgement wait and the 30 s xApp run. Reported as n, mean ± sd, median, p95, max. Planner caching is off in headline runs; `planner_cached_record_count` must be 0. | records with a latency |

Legacy fields still emitted for comparison with the May-2026 batch, **not for the paper**:
`conflict_detection_accuracy` (includes true negatives and after-the-fact recoveries),
`tool_call_success_rate` (= launch success), `recovery_rate` (includes external replay).

## Seeded conflicts
See `CONFLICTS.md`.

## Inference settings
Recorded per batch in `manifest.json → planner_inference_settings` (temperature, seed, num_predict,
timeout) and per record in `planner_provider` / `planner_model`. Set them with
`FLEXRIC_LLM_TEMPERATURE`, `FLEXRIC_LLM_SEED`, `FLEXRIC_LLM_NUM_PREDICT`. Hardware of the LLM host is
recorded from `LLM_SERVER_HARDWARE`.
