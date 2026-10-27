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
| **Acknowledged** | within `--tool-ack-timeout-s` the run log shows evidence of real work: KPM records for observation, the E2 `CONTROL-ACK` from the RAN or a subscription/`Applied …` line for slice/TC control, an RC subscription line for validation, an `rApp ack:` line for emulated rApps (markers in `run_harness.TOOL_ACK_MARKERS`). A negative line (`Error`, `Traceback`, …) is final only once the process has exited; while it runs the harness keeps polling until the deadline. Refused/queued/failed calls are unacknowledged. | tool calls with a verdict |
| **Hallucinated references** | count of application names in the generated workflow, or `(agent, action)` pairs in tool calls, that do not exist in the Agent Registry | summed over records |
| **Conflict refused** (`conflict_recall`) | seeded-conflict records in which the conflict was caught *before* control was issued, on the record's first or final execution (`analyze_results.conflict_flagged`): queue, `blocked_reason`, or a tool call refused by the portal's per-agent lease (HTTP 409, `already has an active action`). The lease is shared by every method, so this measures whether the method's chain reached the busy application, not a method-specific check. | seeded records (6 intents × repeats) |
| Conflict precision | TP / (TP + FP) where FP = unseeded records flagged as conflict | — |
| Conflict FP rate | unseeded records flagged as conflict | unseeded records |
| **Seeded recovered** | seeded records where the method's *internal* recovery produced a clean execution after the refusal — the method-specific part of conflict handling | seeded records |
| **Latency** | wall-clock from intent submission to a validated, launched plan (planner calls + validation + launch). Excludes the acknowledgement wait and the 30 s xApp run. Reported as n, mean ± sd, median, p95, max. Planner caching is off in headline runs; `planner_cached_record_count` must be 0. | records with a latency |

Until 2026-10-28 `conflict_detected` was set from the final execution only, and a lease refusal inside a
template workflow (recorded as a failed tool call) was not counted while the same refusal on a custom
chain (`blocked_reason`) was. Both are fixed in `run_harness.py`; `conflict_flagged` re-derives the
unified rule from the raw record, so earlier batches score the same as new ones.

Legacy fields still emitted for comparison with the May-2026 batch, **not for the paper**:
`conflict_detection_accuracy` (includes true negatives and after-the-fact recoveries),
`tool_call_success_rate` (= launch success), `recovery_rate` (includes external replay).

## Confidence intervals in the paper figures and tables
`summary.json` keeps the normal-approximation half-width (`*_ci95`) for quick reads. The paper
artefacts (`paper_results/make_paper_figures.py`) recompute every number from `records.jsonl` and use
an **intent-clustered percentile bootstrap** (2000 resamples, seed 0) for accuracies, the
acknowledged-call rate and hallucinations per record — the 5 repeats of one intent are correlated, so
intents are resampled, not records — and a **Wilson score interval** for conflict recall and
false-positive rate (only 6 seeded intents, too few clusters to bootstrap).

## Accepted chains
`intents_50.json` has one labelled chain per intent. `intents_v2.json` adds alternatives: for the new
rApp intents where observation/prediction order is interchangeable, and for 11 of the 50 original
intents a read-only analytic rApp inserted after KPM when the intent text asks for that function (rule
in `build_intents_v2.py`). *Accuracy* in the paper = exact ordered match with any accepted chain.

## Seeded conflicts
See `CONFLICTS.md`.

## Inference settings
Recorded per batch in `manifest.json → planner_inference_settings` (temperature, seed, num_predict,
timeout) and per record in `planner_provider` / `planner_model`. Set them with
`FLEXRIC_LLM_TEMPERATURE`, `FLEXRIC_LLM_SEED`, `FLEXRIC_LLM_NUM_PREDICT`, and `FLEXRIC_LLM_THINK`
(true/false; unset = the model's default reasoning mode — Ollama `think`, vLLM
`chat_template_kwargs.enable_thinking`). The OpenAI-compatible path (vLLM on spark1) sends the same
temperature/seed/max_tokens. Hardware of the LLM host is
recorded from `LLM_SERVER_HARDWARE`.
