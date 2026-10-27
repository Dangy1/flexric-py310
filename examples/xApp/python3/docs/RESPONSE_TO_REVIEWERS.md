# Response to reviewers — WCM-26-00422 (major revision)

**AppWeaver: Agentic Composition of O-RAN Applications with Agent Cards**

Draft written 2026-10-27 by the execution session. Every number below comes from a batch under
`evaluation/runs/<id>/` (manifest + `records.jsonl`) through `evaluation/paper_results/make_paper_figures.py`.
No number from the first submission's May-2026 batch is reused: that batch had a label leak in the
repair step, counted subprocess launch as tool success, credited after-the-fact recovery as conflict
detection, and used a planner cache (see `docs/REVIEW_ASSESSMENT_2026-10-27.md`).

<!-- NUMBERS: filled from evaluation/runs (see "Status of the numbers" at the end). -->

We thank the reviewers. The revision changes the evaluation more than the text: we found and removed
a flaw in our own harness (the repair step could read the labelled chain for known-template intents),
redefined every reliability metric, added two baselines and an ablation, scaled the registry from 9 to
55 Agent Cards, released the benchmark and code, and added a twin-versus-live KPI experiment. The
headline numbers changed accordingly; we report them with confidence intervals and per-split detail.

Comment labels follow the decision letter (R*n*.*m* = Reviewer *n*, comment *m*).

---

## Summary of changes

| Area | What changed | Where |
|---|---|---|
| Evaluation harness | Label leak removed: repair may only use the registry (unknown ids dropped, duplicates collapsed); the labelled chain is never read by any method | §IV-A, `evaluation/run_harness.py` |
| Metrics | Accuracy = exact ordered match with any *accepted* chain, plus set match; tool call = **acknowledged** by the RAN (E2 CONTROL-ACK / KPM indication / rApp ack), launch reported separately; conflict detection = recall and false-positive rate over seeded conflicts, flagged *before* control; hallucinated references counted per record | §IV-A, Table II, `evaluation/METRICS.md` |
| Baselines | Rule router, single app, **LLM without catalog** (new), LLM with catalog, **AppWeaver without repair** (new ablation), AppWeaver | §IV-A, Table II |
| Variance | 5 repeats per (intent, method), planner and observation caches off, fixed temperature 0.2 and seed 7; 95% CIs (intent-clustered bootstrap; Wilson for conflicts); latency median / p95 / max | Table II, Figs. 4–5 |
| Agent Cards | Schema v2 (app type, RIC, interfaces, data models, control scope, timescale, requires, conflicts_with, version, endpoints) and four explicit compose-time checks (dependency, interface, control scope, timescale), logged per record | §III-B, Table I, `backend/orchestration/compat.py` |
| Registry | rApp Directory of 46 emulated rApp cards (16 families, 3 fictional vendors, 13 deprecated releases, 30 distractor cards) on top of the 9 FlexRIC cards → 55 cards, 50 executable; BM25 retrieval of the top-*k* cards | §IV-B, Table III, `rapps/` |
| Benchmark | `intents_v2.json`: 80 intents in three splits (11 known-template, 39 open-world, 30 unseen-capability) | §IV-B, Fig. 6 |
| Digital twin | Twin = ns-3/5G-LENA instance A behind FlexRIC; live = instance B (different seed, +25 % UEs or matched load); predicted vs measured KPI deltas for energy saving, traffic steering and QoE steering (TC/slice not actuatable in ns-O-RAN) | §IV-C, Fig. 7, `evaluation/TWIN_VALIDATION.md` |
| Release | Code, benchmark, cards and per-record results public; one command per batch | footnote §IV, `README.md` |

---

## Reviewer 1

**R1.1 — Distinction from AgentRAN and related work; what Agent Cards add; how dependency, interface and control-scope compatibility are checked.**

*Change.* Agent Cards are now a concrete schema (v2) rather than a description. Beyond A2A's generic
card, each card declares O-RAN-specific fields: `app_type` (xApp/rApp), `ric` (near-RT/non-RT),
`interfaces` (E2SM-KPM v3, E2SM-RC, A1 policy types, O1), `data_models` consumed/produced,
`control_scope` (target cell/UE/slice/node/transport, read/write, resource class), `timescale_s`,
`requires`, `conflicts_with`. Compose runs four explicit checks on every candidate chain:
(i) *dependency* — every `requires` of step *k* is produced by a step before *k*;
(ii) *interface* — consecutive steps share a data model or interface;
(iii) *control scope* — two writers on one resource class, or a declared capability conflict, are rejected unless leased in order;
(iv) *timescale* — no near-RT control after a non-RT step without an observation step between.
A failing check triggers repair (drop/reorder) or rejection, never a silent pass; each check's
verdict is logged per record (`compat_report`). The comparison with AgentRAN and LLM-xApp frameworks
is now a table row set ("discovery from machine-readable cards", "explicit compatibility checks",
"registry scale evaluated") with the criteria defined in a footnote.

*Where.* §II (related work paragraph), §III-B, Table I, `backend/orchestration/compat.py`.

**R1.2 — How faithful is the digital twin; predicted vs actual KPIs.**

*Change.* The first submission's "twin" was not implemented as a network model; we say so and replace
it. The twin is now an ns-3/5G-LENA instance (ns-O-RAN) behind its own FlexRIC nearRT-RIC; the "live"
network is a second instance with a different seed (UE drop, mobility, fading) and, in the main batch,
25 % more UEs. AppWeaver composes the workflow, the rApps decide a policy on the twin's KPM, and the
same policy is deployed on live. We report predicted (twin) vs measured (live) deltas against a
same-seed no-op for DL PRB use, DL throughput, RLC queue and gNB energy: mean relative change, absolute
error, MAPE and sign agreement over 8 seed pairs, for energy saving (cell switch-off), traffic steering
and QoE-driven steering (handover). Transport-QoS and slice workflows cannot be validated this way:
ns-O-RAN exposes only KPM and RC (handover, cell on/off), not TC or slicing control; we state this.
Simulator noise was measured by re-running every no-op with the same seed (≤0.3 % on PRB, ≤0.01 % on
energy and throughput).

*Result (in the paper's words).* With the twin's load matched to live, the energy effect of switching
cells off is predicted to within 4.1 percentage points (−11.9 % predicted vs −13.9 % measured) with the
correct sign in 8/8 pairs; the direction of the PRB change is right in 62–75 % of pairs; throughput and
queue changes are not predicted reliably (sign agreement ≤62 %), because they depend on which users
move, which the twin does not know. With an under-loaded twin, PRB predictions had the wrong sign in
most energy-saving pairs (25 % agreement). We therefore narrow the claim: the twin guards against the
wrong policy class (e.g. sleeping a loaded cell) and predicts cell-level energy, not per-user QoS.
The MOS values of the old Fig. 2 are removed.

*Where.* §III-C, §IV-C, Fig. 7, `evaluation/TWIN_VALIDATION.md`,
`evaluation/runs/20261027T171217Z_T6_twin_vs_live{,_loadcal}/`.

**R1.3 — Which applications are real xApps and which are emulated.**

*Change.* New inventory table. Real: the four FlexRIC xApps exercised over E2 (KPM monitor, SLICE
control, TC control, RC validation) plus monitor cards for MAC/RLC/PDCP/GTP. Emulated: the 46 rApps of
the rApp Directory, served by one process (`rapps/runtime.py`) whose tools read live KPM from the KPM
bus and return documented rule/regression outputs. The QoE-prediction and mobility xApps named in the
first submission are not claimed any more; their functions appear as emulated rApps and are labelled as
such. Tool success counts only acknowledged calls, so an emulated rApp scores only if it answered.

*Where.* §III-B, Table I (inventory column), §IV-A.

**R1.4 — What "open-world" means; registry size and composition.**

*Change.* Three splits are now defined: *known* (intent matches one of the portal's three workflow
templates), *open-world* (no template; composable from the four FlexRIC xApps), *unseen-capability*
(needs at least one rApp capability that appears in no template and in no deterministic fallback
rule). The registry grew from 9 cards (4 executable) to 55 cards (50 executable), including vendor
variants, deprecated releases and cards with conflicting control scopes as distractors.

*Where.* §IV-B, Table III, Fig. 6.

**R1.5 — Catalog-aware LLM baseline and ablation.**

*Change.* The first submission's "LLM-only" baseline was in fact catalog-grounded and rule-repaired
(we state this). It is now *LLM (catalog-aware)*. We add *LLM (no catalog)* — the prompt has no
registry; plans are executed only where they name a real application, and hallucinated references are
counted — and *AppWeaver (no repair)*, which isolates the repair step.

*Where.* §IV-A, Table II, Fig. 4.

**R1.6 — Reliability denominators, seeded conflicts, hallucination counts.**

*Change.* Table II reports the number of tool calls and the acknowledged fraction, the number of seeded
conflict records (6 intents × 5 repeats), conflict recall and false-positive rate, and hallucinated
references per method. `evaluation/CONFLICTS.md` documents each seed (what runs first, which lease it
holds, what counts as a correct detection).

*Where.* §IV-A, Table II, Fig. 5.

**R1.7 — Presentation.** Fig. 2 must no longer hint the skill to be composed (redraw: intent text only, no
application names); Fig. 3 split; labels and typos — see "Minor comments" (manuscript edits).

---

## Reviewer 2

**R2.1 — Benchmark transparency, number of trials, variance; code release.**

*Change.* Benchmark (50 + 30 intents with labelled and accepted chains), cards, harness and per-record
results are released. Five repeats per (intent, method); CIs on every rate; labelling rules in
`evaluation/build_intents_v2.py` (alternative chains accepted only under a written, conservative rule).

*Where.* §IV-A, footnote with repository URL, `README.md`.

**R2.2 — Network-level effect of the composed workflows.**

*Change.* See R1.2: measured KPI deltas on the live instance and their agreement with the twin's
prediction. The first submission's before/after KPIs were not available (telemetry services were down
during that batch); the revised batches verify that RPC, MCP and KPM-bus services are up in the manifest.

*Where.* §IV-C, Fig. 7.

**R2.3 — Model and inference settings.**

*Change.* Every manifest records the planner provider, model, temperature, seed, token limit, reasoning
mode, timeout, a SHA-256 of each prompt builder (from Batch B on; Batch A's builders are byte-identical)
and LLM host hardware; the paper states them in §IV-A.

---

## Reviewer 3

**R3.1 — Twin fidelity.** See R1.2.

**R3.2 — How intents were labelled; can more than one chain be valid?**

*Change.* Yes; intents now carry `accepted_workflows`. We report exact ordered match against any
accepted chain (headline), exact match against the single labelled chain, and set match (same
applications, any order).

**R3.3 — Variance and number of runs.** See R2.1.

**R3.4 — Ablation of the components.** See R1.5 (no-catalog LLM, no-repair AppWeaver) and Batch B's
retrieval-depth comparison (top-8 cards vs. all cards in the prompt).

**R3.5 — Conflict detection is reported as accuracy.**

*Change.* Replaced by recall over seeded conflicts and false-positive rate over unseeded records; a
detection counts only if the method flags the conflict before issuing control. After-the-fact recovery
is a separate column.

**R3.6 — Latency distribution and the Non-RT timescale.**

*Change.* Fig. 5 shows the per-record distribution (median, IQR, 5–95th percentiles, outliers);
Table II gives median / p95; the text relates them to the ≥1 s Non-RT RIC control loop. Planner caching
is off (`planner_cached_records = 0` in every headline batch).

**R3.7 — What is checked at composition time.** See R1.1.

---

## Reviewer 4

**R4 — Scalability ("RAG is overkill for 9 cards"), an extra capability, hardware, reliability detail.**

*Change.* With 55 cards the full registry no longer fits a compact prompt, so discovery is a real
retrieval problem: BM25 over card text with family de-duplication, top-*k* in the prompt. We report
retrieval hit rate (all needed cards retrieved) and accuracy at *k* = 8 vs. all cards. Energy saving,
RET tilt, root-cause analysis and QoE prediction are new capabilities that discovery picks up without
code changes (unseen-capability split). Hardware of the LLM host and the orchestration host is in the
manifest and §IV-A. Reliability detail: see R1.6.

---

## Minor comments

These are edits to the paper source, which is not in this repository; the authors apply them in the
manuscript. Proposed wording/changes:

| Comment | Change to make in the manuscript |
|---|---|
| p3 l54, p5 l64 typos | fix |
| Capitalisation of "Agent Card" | unify to "Agent Card" |
| Fig. 5a axis labels | replace with `paper_results/figures/fig_accuracy.pdf` (both bars labelled with intent counts, 95% CI) |
| Fig. 3 density | split into two panels |
| References | add O-RAN WG2 Non-RT RIC architecture (≥1 s loop), A2A and MCP specifications |

---

## Status of the numbers

<!-- STATUS -->
