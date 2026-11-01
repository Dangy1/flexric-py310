# Response to reviewers — WCM-26-00422 (major revision)

**AppWeaver: Agentic Discovery and Composition of O-RAN Apps for AI-Native 6G**

Every number below comes from a run under `evaluation/runs/<id>/` (manifest + records/results) and is
recomputed by the scripts named next to it; no number from the first submission is reused. Revised
manuscript: `paper/main.tex`. Results package for the authors: `evaluation/demos/RESULTS_PACKAGE.md`.

We thank the reviewers. Their comments made us rebuild the evaluation rather than polish it. While
answering them we found a flaw in our own harness (a repair step could read the labelled chain), so the
first submission's numbers are withdrawn and every result is new: three intent sets (219 intents), a
registry scaled from 9 to 81 Agent Cards, six methods including two new baselines and an ablation, a second
planner model, and, new in this revision, measured network effects of the composed workflows on a 5G RAN
model and on a real transport link. The magazine limits (6 floats, 15 references) are kept: Fig. 2 is now
a recorded trace, Fig. 4 shows KPIs while workflows act, and Fig. 5 summarizes all accuracy and network
results. Full per-method tables with confidence intervals are in the public repository.

Comment labels follow the decision letter (R*n*.*m* = Reviewer *n*, comment *m*).

---

## Summary of changes

| Area | What changed | Where |
|---|---|---|
| Harness | Label leak removed (no method or repair step reads the labelled chain); caches off; every batch has a manifest with model, settings, hardware, prompt hashes and git commit | §IV-A/B, `evaluation/run_harness.py` |
| Correctness metric | Rule accuracy, pre-registered before the runs: all required applications present in a valid partial order, extra steps read-only; exact-match and a label-sensitivity reading reported alongside | §IV-B, `evaluation/METRICS.md` |
| Methods | Rule router, single app, **LLM without catalog** (new), LLM with the full catalog (single pass), **AppWeaver without repair** (new ablation), AppWeaver; plus template/memory variants | §IV-B |
| Benchmarks | A: 50 intents / 9 cards / 5 repeats; B: 109 intents / 81 cards / 3 repeats incl. 59 unseen-capability intents, top-8 retrieval vs all cards; C: 60 held-out intents written after the design was frozen; 8,712 records | §IV-B, Fig. 5 |
| Agent Cards | Schema with O-RAN fields (app type, RIC, interfaces, data models, control scope, timescale, requires, conflicts_with, lifecycle); five compose-time checks logged per record | §III-B, Fig. 2 |
| Digital twin | Stated precisely: an E2 twin (second RIC + emulated node) dry-runs every E2 step; a network twin (second ns-3 instance) predicts KPI effects, with measured fidelity | §III-A, §IV-D |
| Network effect (new) | Composed workflows deployed on a 5G-LENA ns-3 RAN (steering, energy saving) and AppWeaver's TC action on a real Linux bottleneck through a new E2 agent; KPIs over time and over seeds | §IV-D, Figs. 4, 5(c) |
| Second model | GLM-5.3-Flash on Batch C | §IV-C |
| Release | Code, intents, cards, run records, figure scripts | footnote §IV-A |

---

## Reviewer 1

**R1.1 — Distinction from AgentRAN and related work; what Agent Cards add; how dependency, interface and control-scope compatibility are checked.**

AppWeaver's Agent Cards add O-RAN-specific content to the generic A2A card: application type and RIC,
service models and A1/O1 interfaces, data models consumed and produced, control scope (cell, UE, slice,
node, transport; read or write), timescale, `requires`, `conflicts_with` and lifecycle state. Every
composed chain is checked against them before anything runs: dependency (each step's inputs are produced
upstream), interface, control scope (no two writers on one resource without serialization), timescale
and lifecycle (deprecated releases rejected). Errors send the plan back for repair; the verdict of each
check is stored per record. Fig. 2 now shows these checks on a recorded run (0 errors, 2 warnings).
Table I's comparison uses these criteria (discovery from machine-readable cards, explicit compatibility
checks, conflict handling, pre-deployment validation).

*Where.* §II, §III-B, Fig. 2, Table I; code `backend/orchestration/compat.py`.

**R1.2 — How faithful is the digital twin; predicted vs actual KPIs.**

We now separate two twins and measure the one that predicts KPIs. The E2 twin (a second FlexRIC RIC and
emulated node) dry-runs every E2 step and catches interface, lease and acknowledgement errors; it does not
predict KPIs and we no longer claim so. The network twin is a second 5G-LENA ns-3 instance that shares the
UE layout with the "live" instance but not its mobility or fading seed; the policy is decided on the twin
and deployed unchanged on live, and both are compared with the same seed without the action.

Result (§IV-D, Figs. 4 and 5(c), 5 seeds): for energy saving the twin predicts gNB energy −39.7% vs −41.3%
measured, throughput −22.4% vs −22.7% and users served −22.5% vs −22.5% (correct sign 5/5); for steering it
predicts the load shift (source-cell PRB) in 5/5 seeds but not the throughput gain from users restored to
service (−2.5% predicted vs +6.2% measured). A larger study without a shared layout
(`evaluation/TWIN_VALIDATION.md`, 9 seed pairs per setting) shows the dependence on state sync: with
random UE placement the twin's throughput error is 6–12 points, with synced placement 3.8–6.7 points.
We narrow the claim accordingly: the twin predicts cell-level effects well when it knows where users are,
and per-user QoS less well.

*Where.* §III-A, §IV-D, Figs. 4–5; runs `20261101T103300Z_D2_{hotspot,night}`, `20261028T173841Z_T6v3_*`.

**R1.3 — Which applications are real xApps and which are emulated.**

Real: four FlexRIC xApps used over E2 (KPM monitoring, SLICE, TC, RC) and the MAC/RLC/PDCP/GTP
monitors. Emulated: the rApps (QoE prediction, traffic steering, energy saving and 29 other families),
served as decision services behind standard tool interfaces. The QoE-prediction and mobility xApps of the
first submission are no longer claimed. The composition benchmark runs on FlexRIC's E2 emulator, whose KPM
values are synthetic; network effects are therefore measured separately on ns-3 and on a real link
(§IV-D). For TC we found that neither the emulator nor OAI's TC RAN function applies TC control, so we
wrote an E2 agent whose TC service model applies the received queue control to a real Linux link.

*Where.* §IV-A, Fig. 4(c); code `examples/emulator/agent/sm_tc_dp.c`.

**R1.4 — What "open-world" means; registry size and composition.**

*Known*: the intent matches one of the three operator workflow templates; *open-world*: no template
matches; we also report the open-world intents that no template solves even partially (27 in A, 22 in
C), since only there must a method compose. *Unseen capability* (Batch B, 59 intents): the intent needs an
rApp absent from every template. The registry grows from 9 cards to 81 (80 executable): 32 rApp families
with vendor variants, deprecated releases and distractors.

*Where.* §IV-B, Fig. 5(a,b).

**R1.5 — Catalog-aware LLM baseline and ablation.**

The baseline the first submission called "LLM only" was catalog-grounded and rule-repaired; it is now
*LLM (catalog)*: the same planner model with the full catalog in its prompt, one pass, no Agent Card
checks, output executed as returned. We add *LLM (no catalog)*, which shows the cost of no grounding
(705 references to non-existent applications in Batch A), and *AppWeaver (no repair)*. Result: the
catalog-aware LLM reaches 34.8% / 16.8% / 53.3% (A/B/C) against AppWeaver's 70.4% / 68.8% / 93.9%, and
0% on the intents no template solves, where AppWeaver reaches 55–94%.

*Where.* §IV-B/C, Fig. 5.

**R1.6 — Reliability denominators, seeded conflicts, hallucination counts.**

Tool success now means the target application acknowledged the call (E2 control ack, KPM indication or
rApp reply): 97–100% for AppWeaver over 380–867 calls per batch. Hallucinated references: 0 for AppWeaver
in every batch. Seeded conflicts: 6 intents × 5 repeats (A) and × 3 (B), documented in
`evaluation/CONFLICTS.md`. A shared lease protects busy applications for every method; AppWeaver never
preempts, waits for the lease and completes 37% (A) to 44% (B) of these cases with no unresolved refusal;
the rule router completes with a wrong workflow in 83% of its cases.

*Where.* §IV-E; per-method numbers with CIs in `evaluation/paper_results/README.md`.

**R1.7 — Presentation.** Fig. 2 is now a trace recorded from a run: the intent names no application, and
every line (retrieved cards, composed chain, checks, dry-run, acknowledgements, baselines' output) is
taken from the record. Fig. 3 was simplified (MCP panel removed). Other minor comments: see the table at
the end.

---

## Reviewer 2

**R2.1 — Benchmark transparency, number of trials, variance; code release.**

219 intents with labels and labelling rules, the Agent Cards, the harness and every run record are
public; 5 repeats (A) or 3 (B, C) per intent and method; 95% intent-clustered bootstrap CIs on every
rate (Fig. 5).

*Where.* §IV-A footnote, §IV-B, `README.md`.

**R2.2 — Network-level effect of the composed workflows.**

New §IV-D, Fig. 4 (system KPIs over time around each action: users per cell, cell load or power, received
throughput, users served; RTT and goodput on the real link) and Fig. 5(c) (change over seeds, measured and
predicted). On ns-3, the composed QoE-steering chain moves load out of a hotspot (source-cell PRB −29%);
users served rise by 10% and throughput by 6.2% on average, because in this layout the simulator leaves some
hotspot users unserved and steering restores two of them in two of five seeds; in the other seeds load
moves without a throughput change. The baselines' chain for this intent has no steering step. The
energy-saving chain cuts gNB energy by 41.3% but two users lose service (users served and throughput
−22–23%). On a real 10 Mbit/s bufferbloated link, the TC action AppWeaver deploys (CoDel) reaches the queue
over E2 in 2.1 s and cuts the median RTT from about 420 ms to 35 ms (pings above 100 ms: 100% → 0%) with
unchanged goodput, in 5/5 repeats.

**R2.3 — Model and inference settings.**

gpt-oss-120b served by vLLM on an NVIDIA DGX Spark (GB10, 128 GB unified memory), reasoning effort
medium, temperature 0.2, seed 7; every manifest records these plus prompt hashes and hardware. A second
planner (GLM-5.3-Flash) gives the same accuracy on Batch C (§IV-C).

---

## Reviewer 3

**R3.1 — Twin fidelity.** See R1.2.

**R3.2 — How intents were labelled; can more than one chain be valid?**

Yes. Each intent is labelled with the applications it requires and their partial order; any chain that
contains them in a valid order, with only read-only extra steps, is correct. This rule was fixed before
the final runs. We also report exact match with the labelled chain and a sensitivity reading for four
questioned labels; conclusions do not change.

**R3.3 — Variance and number of runs.** See R2.1.

**R3.4 — Ablation of the components.** LLM without catalog, LLM with catalog, AppWeaver without repair;
retrieval depth (top-8 vs all 81 cards: 68.8% both, one third of the prompt tokens); template and memory
variants (up to 74.6% on B, 96.1% on C); a second planner model.

**R3.5 — Conflict detection is reported as accuracy.** Replaced by what happens on seeded conflicts: met
the busy application, waited and completed, unresolved, preempted (never), and correctness of the
completed workflow; plus false positives on unseeded intents. See R1.6.

**R3.6 — Latency distribution and the Non-RT timescale.** Median 26–36 s from intent to deployable
workflow (planner-dominated; the E2 dry-run adds about 8 s); p95 and max in the repository tables; within
the Non-RT timescale (>1 s). Planner caching is off in every batch.

**R3.7 — What is checked at composition time.** See R1.1.

---

## Reviewer 4

**R4 — Scalability ("RAG is overkill for 9 cards"), an extra capability, hardware, reliability detail.**

The registry is now 81 cards, so discovery is a real retrieval problem: BM25 over the cards, top 8 in the
prompt. Top-8 retrieval matches putting all cards in the prompt (68.8% both) at one third of the tokens
and a lower latency (32.5 s vs 36.2 s median); the needed cards are retrieved 94.5% of the time. New
capabilities (energy saving, QoE prediction, traffic steering, and others) are picked up from their cards
without code changes: on the 59 unseen-capability intents AppWeaver reaches 82.5% and every baseline 0%.
The term RAG was replaced by BM25 retrieval over Agent Cards. Hardware: R2.3. Reliability: R1.6.

---

## Minor comments

| Comment | Change |
|---|---|
| p3 l54 "leaving this step manually" | "leaving this step manual" |
| p5 l64 "an feedback loop" | "a feedback loop" |
| Capitalization ("Planner agent", "Agent Card") | unified |
| Fig. 3 density | MCP panel removed, remaining panels enlarged |
| Fig. 5 labels | Fig. 5 regenerated from the final runs, every bar labelled, 95% CIs |
| References | all 15 checked against Crossref; duplicates removed; preprints replaced by published versions; Non-RT timescale, A2A and MCP specifications cited as footnotes |

---

## Notes for the authors (remove before sending)

- The network-effect experiments are a 5G RAN model (ns-3) and a Linux link, not a physical RAN; the
  paper says so. Fig. 4(a) shows seed 104, one of two seeds with a throughput gain (per-seed:
  +18.8/+0.7/−0.9/+12.8/−0.4%); the caption names the seed and §IV-D gives the mean.
- The pre-declared energy-saving acceptance rule (energy and load only) accepts the harmful policy; §IV-D
  states this rather than changing the rule after the fact.
