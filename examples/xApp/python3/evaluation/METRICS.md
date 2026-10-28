# Evaluation metrics (definitions used by `analyze_results.py`)

All rates are over *available* records (records whose method could run; a method whose planner
provider was unreachable is marked unavailable and excluded, and the count is reported).
A record is one (intent, method, repeat). Accuracies carry a normal-approximation 95% CI half-width.

| Metric | Definition | Denominator |
|---|---|---|
| **Accuracy (rule)** — primary | `workflow_match_rule`: the chain satisfies the intent's pre-registered `label_rule` (section below) | available records |
| Known / open-world / unseen-capability accuracy | rule accuracy split by `intent.split` (`analyze_results` also reports `known_rule_accuracy` / `open_world_rule_accuracy` split by `intent.open_world`) | records of the split |
| **Exact accuracy** — secondary | `generated_workflow == expected_workflow` (ordered, exact; `workflow_match`) | available records |
| Set accuracy | same capability set as any accepted chain, order ignored, non-empty | available records |
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

## Primary accuracy: pre-registered label rule (2026-10-28)

**Pre-registered on 2026-10-28, before the final batches** (owner decisions O6/O8, `docs/REVISION_PLAN.md`
§3c; `docs/FABLE_REVIEW_AND_PLAN.md` §4.4–4.5). It applies to every method and both batches. It was
written from the labelled chains and the Agent Cards' declared roles/scopes; no method output was
consulted. Code: `evaluation/label_rules.py` (`derive_rule`, `rule_match`); every intent of
`intents_50.json` / `intents_v2.json` carries the derived rule as `label_rule`, generated by
`evaluation/build_label_rules.py` (deterministic; `--check` verifies the files are current);
`expected_workflow` and `accepted_workflows` are unchanged. Tests: `evaluation/tests/test_labels.py`.

**Roles** (from the cards, `label_rules.app_role`): a card's declared `workflow_role` if present, else
*validate* if it advertises `control_validation` (RC), *control* if any `control_scopes` entry is
`write` (SLICE, TC, write-scope rApps), *observe* if it provides `kpi_monitoring` (KPM, the PM/KPI rApp),
*analyze* otherwise (read-only rApps: QoE prediction, anomaly detection, root cause). A declared role
must agree with the scopes (tested).

**Rule.** A generated chain is correct iff

1. every step is an active (not deprecated), executable card of the run's Agent Registry (hallucinated,
   deprecated or action-less descriptive cards such as MAC make the chain wrong);
2. it contains every **required** app. Required = every non-validation app that appears in *all* labelled
   chains of the intent (`expected_workflow` ∪ `accepted_workflows`). Where accepted chains substitute one
   app for another of the same class (read-only vs write) the slot accepts either
   (`night_energy_saving`: KPM | RAPP.PM_KPI; `vendor_variant_trap`: canonical | Northwind variant);
3. it respects the **partial order** observe < analyze < control: for required apps a, b that every
   labelled chain orders a before b, a must precede b if role(a) ranks lower than role(b), or b depends
   on a (`requires` a capability / `consumes` a non-RAN data model of a), or a declares b in
   `conflicts_with` (the order compat enforces). Pairs that the labels order *against* the role ranks
   are unconstrained — this is how the slice-assurance template SLICE→KPM→RC and its observe-first
   reordering KPM→SLICE→RC are both correct (O6) — as are two control steps without a dependency
   (SLICE, TC);
4. every **validate** step comes after every control step in the chain (control < validate);
5. it contains no **forbidden writer**: a control-role app that no labelled chain of the intent contains
   (listed per intent as `forbidden_writers`; substituting `RAPP.TRANSPORT_QOS` for TC, or adding SLICE to
   a TC-only intent, is wrong);
6. any other extra step is read-only (observe/analyze/validate) and allowed (O8): e.g.
   KPM→RAPP.ANOMALY_DETECTION→TC→RC for a KPM→TC→RC intent is correct; dropping or replacing a required
   control step is not.

**One uniform policy for KPM and RC (all 80 intents).** *Validation (RC) is never required* but, when
present, must follow every control step (optional-but-ordered). Reason: the labels disagree on whether a
control chain ends in RC (`energy_saving_wakeup_guard` KPM→ES vs `night_energy_saving` KPM→ES→RC,
`priority_for_emergency_ues` vs `cell_edge_qoe_protection`, the TC-only templates); requiring RC
everywhere would contradict the labels, requiring it only where labelled would score the same chain
differently across near-identical intents; and the RC step issues no control (§3 of the review), so
it carries no task content. *Observation (KPM, or the PM/KPI rApp where an accepted chain uses it) is
required exactly when every labelled chain contains it*, like any other app: observation produces the
input that downstream analytics/control declare as `requires: kpi_monitoring`, and for the
investigation intents (KPM→RC) it is the only non-validation step, so dropping it leaves an empty task.
Extra observation is read-only and always allowed (e.g. KPM→TC for a TC-only intent).

**Edge cases.** TC-only intents (`transport_*`, `tc_conflict_recovery`): required {TC}; KPM and RC may
be added. Chains that end in an rApp (`video_qoe_forecast`, `kpi_anomaly_sweep`, `capacity_headroom_forecast`,
`energy_saving_wakeup_guard`, `priority_for_emergency_ues`): RC optional. Single-rApp intents
(`slice_sla_report`, `config_rollout_window`, `rollout_blocked_by_energy`): required {that rApp}; KPM may be
added; any other writer (e.g. energy saving in `rollout_blocked_by_energy`) is forbidden. Intents with
read-only accepted alternatives (11 base intents): the alternative's rApp is optional
(`optional_apps`). Vendor variants of a *required* rApp count as missing unless an accepted chain names
the variant; a vendor variant of a read-only analytic is an allowed extra; a write-scope variant is a
forbidden writer. The per-intent rule counts: 80 intents, 1–4 required slots (median 2); 0 intents
require RC.

**Scoring.** The harness stores `workflow_match_rule` (+ `workflow_rule_reasons`) per record from
`rule_match(generated_workflow, intent, AGENTS)`. `analyze_results.py` and
`paper_results/make_paper_figures.py` recompute it from `generated_workflow`, the run's `intents.json`
(or the labels each record carries) and the run's registry (current cards restricted to the manifest's
`registry.agent_ids`, so an rApp id in a Batch A record is a hallucination). Rule accuracy gets the same
intent-clustered bootstrap CIs as the other accuracies; macros `rule_accuracy`, `known_rule_accuracy`,
`open_world_rule_accuracy`, `unseen_capability_rule_accuracy` (old `*_accuracy` macros keep their
accepted-chain meaning). Card changes after this date change the derived rule only through
`build_label_rules.py`, whose output is committed with the cards.

## Accepted chains (secondary metrics)
`intents_50.json` has one labelled chain per intent. `intents_v2.json` adds alternatives: for the new
rApp intents where observation/prediction order is interchangeable, and for 11 of the 50 original
intents a read-only analytic rApp inserted after KPM when the intent text asks for that function (rule
in `build_intents_v2.py`). *Accepted accuracy* = exact ordered match with any accepted chain; it and
*exact accuracy* are reported next to rule accuracy. `notes` and `category` stay in the intent files as
annotations only; methods must not see them (P0-1).

## Seeded conflicts
See `CONFLICTS.md`.

## Inference settings
Recorded per batch in `manifest.json → planner_inference_settings` (temperature, seed, num_predict,
timeout) and per record in `planner_provider` / `planner_model`. Set them with
`FLEXRIC_LLM_TEMPERATURE`, `FLEXRIC_LLM_SEED`, `FLEXRIC_LLM_NUM_PREDICT`, and `FLEXRIC_LLM_THINK`
(true/false; unset = the model's default reasoning mode — Ollama `think`, vLLM
`chat_template_kwargs.enable_thinking`). The vLLM path (`LLM_PROVIDER=vllm`, `VLLM_BASE_URL`,
`VLLM_MODEL`, `VLLM_API_KEY`) sends the same temperature/seed/max_tokens plus
`FLEXRIC_LLM_REASONING_EFFORT` (gpt-oss low/medium/high); the pinned provider and effort are part of
`planner_inference_settings`. Hardware of the LLM host is recorded from `LLM_SERVER_HARDWARE`.
