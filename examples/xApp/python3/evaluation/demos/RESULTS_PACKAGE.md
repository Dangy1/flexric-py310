# AppWeaver revision: results package (WCM-26-00422)

Everything the revision can report, in one place, for the authors to choose from. Every number comes from
a committed run under `evaluation/runs/` (manifest + records/results); no May-2026 number is used.
Planner gpt-oss-120b on spark1 (vLLM, reasoning effort medium) unless stated.

**Page budget.** The submitted paper sits exactly at the magazine limits: 6 floats (Table I, Figs. 1-5),
15 references, ~3,700 of 4,500 words. New material must replace floats, not add them. The candidates below
are built for that: D1 replaces Fig. 2, the compact figure replaces Fig. 5, and everything else is text
with numbers (full tables stay in the repository and the response letter).

## 1. Candidate floats

| Float | File | Replaces | Answers |
|---|---|---|---|
| **Fig. 2' real trace (D1)** | `demos/fig_trace_real.tex` (same `awstep` boxes as Fig. 2; preview `demos/d1_preview.pdf`) | Fig. 2 (hand-written ReAct trace naming the skill, invented KPIs) | R1.7 (Fig. 2 hints the skill), R1.1/R3.7 (what is checked at composition), R2.2 (shown, not claimed) |
| **Fig. 5' compact results** | `demos/fig_results_compact.{pdf,png}` (`demos/make_compact_figure.py`) | Fig. 5 (3 panels) | R1.4/R1.5 (splits, catalog-aware baseline), R2.2/R1.2/R3.1 (network effect), R4 (scale) |

Fig. 5' panels: (a) rule accuracy for A / B k=8 / B all cards / C, four methods, 95% CIs; (b) open-world
accuracy on intents that no operator template solves (baselines 0 everywhere); (c) network effect of the
deployed workflows, live measurement, mean +- sd (D2 ns-3, D3 real link).

## 2. Workflow composition (Batches A, B, C)

Rule accuracy (pre-registered label rule), 95% intent-clustered bootstrap CIs in `paper_results/README.md`.

| Batch | Records | AppWeaver | Best variant | LLM (catalog) | Rule router | AppWeaver, open-world no template | Baselines, same split |
|---|---|---|---|---|---|---|---|
| A: 50 intents, 9 cards, 5 rep. | 1500 | 70.4% | -- | 34.8% | 36.0% | 67.4% (27 intents) | 0% |
| B k=8: 109 intents, 81 cards, 3 rep. | 3270 | 68.8% | tpl+memory 74.6% | 16.8% | 16.5% | 55.6% (v2: 79.0%) | 0% |
| B all cards (k=0) | 1962 | 68.8% | -- | 16.5% | 16.5% | 54.3% | 0% |
| C: 60 held-out intents, 9 cards, 3 rep. | 1980 | 93.9% | tpl / mem / mem2 96.1% | 53.3% | 20.0% | 93.9% (v2: 98.5%) | 0% |

- Unseen capability (B): AppWeaver 82.5% (k=8), 87.0% (all cards); baselines 0%.
- Retrieval: k=8 matches all 81 cards in accuracy (68.8% both) with ~9k vs ~25k prompt tokens and 32.5 s
  vs 36.2 s median; the right card is retrieved 94.5% vs 98.2% of the time.
- Learning variants: templates + memory best overall; guided / v2 trade ~25 points on known intents for the
  best template-free open-world accuracy (B 79%, C 98.5%).
- Second planner (C, GLM-5.3-Flash via the Aalto gateway, 900 records, `PLANNERS_C.md`): AppWeaver 93.9%
  (same as gpt-oss), memory variants 96.1%; template-free open-world 83-91% vs 94% on gpt-oss; LLM (catalog)
  60.0%, still 0% template-free.
- A is harder than C (11 vs 25 words per intent, control domain named 68% vs 83%; `DIFFICULTY_A_VS_C.md`).

## 3. Reliability, conflicts, cost

- Acknowledged control calls: 96.8-100% for every method in every batch (A AppWeaver 97.2%, B/C 99.6-100%);
  0 hallucinated references for AppWeaver, 705-1002 for the LLM without catalog.
- Seeded busy-app conflicts (lease, no pre-emption; A: 6 seeds x 5 rep., B: 18 cases): AppWeaver meets the
  conflict, waits for the lease and completes in 36.7% (A) / 44.4% (B k=8) of cases with 0 unresolved
  refusals; the rule router runs straight into the lease (100% met) and completes 88.9-96.7%, but with the
  wrong chain (correct 16.7%). 0 pre-emptions anywhere. C has no busy-app intents.
- Time per intent (median): AppWeaver 26 s (C) - 36 s (B all cards), almost all planner; twin dry-run
  ~8 s, acknowledgement 2-3 s; guided / v2 35-42 s; LLM (catalog) 7-9 s. Within the Non-RT (>1 s) loop.
- Host: the live nearRT-RIC is the largest CPU consumer; every component < 130 MiB RSS
  (`runs/<batch>/resources_summary.md`).

## 4. Network effect (new: Demos D2 and D3)

### D2: deployed AppWeaver chains on ns-3 (5G-LENA, ns-O-RAN-flexric, E2SM-KPM/RC)

`runs/20261101T103300Z_D2_{hotspot,night}/` (`twin/run_twin_validation.py --layout`, layouts in
`twin/layouts/`). Twin and live share the UE layout and differ in seed (mobility, fading); the policy is
decided on the twin and deployed unchanged on live; every delta is against the same seed's no-op. 5 seed
pairs, 50 simulations, 0 failures. Measured = live.

| Scenario | Chain | Live effect (mean over 5 seeds) | Twin prediction | Gate (pre-declared) |
|---|---|---|---|---|
| Night: 6 UEs on one gNB, one UE close to each of two others | KPM -> energy_saving rApp -> RC (sleeps 2 cells) | gNB energy **-41.3%**, throughput **-22.7%** (2 UEs stranded), delay +2.8 ms | energy -39.7% (2.5 pp error), throughput -22.4% (0.3 pp), sign 5/5 | accepts 5/5 (energy criteria do not check throughput) |
| Hotspot: 9 UEs on one gNB's edge | KPM -> traffic_steering rApp -> RC | throughput **+7.8%**, hot-cell PRB cut in 4/5 seeds, delay +32 ms, energy +20% | throughput -0.9% (sign 3/5), PRB / energy sign 5/5 | correct 5/5 |
| Hotspot | KPM -> qoe_prediction -> traffic_steering -> RC (the D1 chain) | throughput **+6.2%**, hot-cell PRB **-29%** (sd 27), delay +95 ms, energy +30% | throughput -2.5% (sign 3/5) | correct 3/5 |

**Users served (added after the per-user check).** In the hotspot layout the simulator leaves 6 of the 9
hotspot users unserved even without any action (0 Mbit/s; the same happens to 0-3 of 10 users in the
random T6v3 layouts). The QoE chain's throughput gain comes from restoring two of them in seeds 101 and 104
(they then see 1-2 s delay from their backlog); in the other seeds load moves without a throughput change.
Users served (>= half the 3.2 Mbit/s offered rate), live vs twin: QoE steering +10% vs -2%; energy saving
-22.5% vs -22.5% (2 users lose service). Fig. 5(c) and Fig. 4 now show users served instead of mean delay,
which is misleading here (unserved users carry no delay).

What it shows: (1) composed rApp chains change real KPIs on a 5G RAN model: steering rebalances a hotspot
and raises throughput 6-8%, at a delay and energy cost; (2) energy saving as decided by the emulated rApp
saves 41% energy but strands two users (-23% throughput); the twin predicts both effects within 3 pp when
it knows the layout, so validate-before-deploy has the information to stop it, but the pre-declared gate
for energy saving (energy >= 5% and remaining PRB <= +30%) does not test throughput and accepts it. With
the steering rule (throughput loss <= 5%) added post hoc, it would reject 5/5 (state as post hoc if used).
Caveats: ns-3 live, not a physical network; 8-s simulations; only RC-actuated chains (ns-O-RAN has no TC or
slicing control); the rApps are emulated decision rules; the layouts were chosen so that the rules act (the
rApp threshold was not changed: energy saving fires only when a cell carries < 0.15 of the busiest cell's
PRB, which in this model means a lone UE close to its gNB, i.e. far from any neighbour).

### D2S: the twin fed with the live state at action time (used in the paper since 2026-11-02)

`runs/20261102T081207Z_D2S_{hotspot,night}/` and `runs/20261102T081207Z_D2S_age{0.5,1.0,1.5}_hotspot/`
(`twin/run_twin_validation.py --layout ... --sync state [--state-age A]`). Why: in D2 each instance resolved
the cell-level policy to UEs on its own KPM, so twin and live moved different users (pair 1: twin UEs 1, 3;
live UEs 4, 9) although the same 6 hotspot UEs are unserved in both no-ops. Protocol: AppWeaver decides on
the live E2 KPM snapshot taken A s before t_act (from the live no-op, identical to the live run up to
t_act), resolves it to UE-level RC commands there, the twin rehearses exactly these commands, and live
executes them at t_act. No-ops copied from D2 (identical inputs). 90 new simulations, 0 failures.

| Twin sync | QoE steering err (pp) thp / served / PRB | Traffic steering err thp / served / PRB | Gate agreement |
|---|---|---|---|
| D2 layout only | 10.0 / 12.0 / 29.4 | 9.3 / 9.5 / 30.1 | 8/10 |
| live state, age 0 | 5.0 / 7.0 / 2.6 | 3.9 / 5.0 / 3.5 | 7/10 |
| age 0.5 s | 4.6 / 5.0 / 4.5 | 2.4 / 2.5 / 5.9 | 10/10 |
| age 1.0 s | 0.6 / 0.0 / 3.5 | 2.2 / 2.5 / 5.2 | 9/10 |
| age 1.5 s | 6.8 / 9.5 / 2.8 | 4.9 / 7.0 / 2.1 | 8/10 |
| pooled ages (n = 20 each) | 4.2 / 5.4 / 3.4 | 3.3 / 4.2 / 4.2 | 34/40 = 85% [71, 93] |

Live effect pooled over the 20 decisions: QoE steering throughput +3.1 +- 7.2% (range -14.6 to +10.9),
users served +5.6%, source PRB -32.7%; traffic steering throughput -0.9 to +10.5%. Night (age 0): the live
snapshot of seed 101 does not meet the energy rule (no action on either side); the other four: energy -41%,
throughput and users served -25%, twin error < 1 pp, gate 5/5. Gate misses: 5 of 6 are conservative
(twin rejects, live would accept); one false accept (age 0, pair 3: twin -1.9% vs live -14.6% throughput).
Energy decisions are identical at every snapshot age except seed 101, so the age sweep is hotspot only.
The steering effect is therefore not robust: the D2 figure of +6.2% throughput / +10% served came from two
lucky seeds and is replaced in the paper by the pooled numbers. Fig. 5(c): `make_compact_figure.py
--d2-hotspot <the four D2S hotspot batches, comma-separated> --d2-night runs/..._D2S_night --d3 ...`.
Fig. 4 (dynamics) still shows the D2 live run of seed 104.

### D3: the AppWeaver TC action on a real bottleneck

`runs/20261101T104040Z_D3_tc_dataplane/` (`demos/tc_dataplane/run_tc_demo.py`). Neither the FlexRIC
emulator nor OAI's TC RAN function applies TC control (both return random statistics). D3 adds an E2 agent
(`examples/emulator/agent/sm_tc_dp.c`, target `tc_dp_agent_gnb`) whose E2SM-TC queue control replaces the
queue of a real Linux link: 10 Mbit/s tbf bottleneck with a 2000-packet FIFO, 4 bulk TCP (CUBIC) flows,
unprivileged user/network namespaces, private nearRT-RIC on 127.0.0.3. At t = 15 s the demo runs exactly
AppWeaver's `apply-codel` action (`xapp_tc_suite.py --profile codel`, CoDel target 20 ms, interval 400 ms);
the only path from the xApp to the queue is E2.

| | Before (FIFO) | After (CoDel via E2) |
|---|---|---|
| Ping RTT median (5 repeats) | 416-426 ms (one repeat 64 ms: queue not yet full) | 33-37 ms |
| Ping RTT p95, mean of repeats | 370 ms | 87 ms |
| Goodput | 9.51 Mbit/s | 9.60 Mbit/s |
| Control applied after xApp launch | -- | 2.11-2.16 s (E2 setup + control) |

Caveats: a Linux link, not a RAN bearer; the TC indication statistics remain the emulator's; one queue
discipline (CoDel). It shows that the TC actions AppWeaver composes are real controls with a measurable
effect, which the emulator batches could not.

### KPM dynamics when the action chain is applied

`demos/fig_kpm_dynamics.{pdf,png}` (`demos/make_kpm_dynamics.py`; reads the per-run traces in the build
tree: E2 KPM `kpm.csv`, ns-3 `energyfilecell<c>.csv` and `DlPdcpStats.txt`). Live runs, solid = action,
dashed = the same seed without it; vertical lines = RC dispatch (handover dotted, cell off solid).

| Column | What happens at the action | Visible change |
|---|---|---|
| (a) Hotspot, QoE chain, live seed 104 | t = 2.0 s: HO 10/6/7 -> cell 5 (cell 3's single UE also leaves) | users cell 2: 9 -> 7, cell 5: 2 -> 5; cell 5 PRB 18 -> ~115 of 139; DL received 29 -> ~33 Mbit/s vs no-op |
| (b) Night, energy chain, live seed 101 | t = 2.0 s: HO 7, 8 -> cell 2; t = 2.3 s: OFF 4, OFF 5 | cells 4/5 power ~920 W -> 0; cell 2 users 6 -> 8; DL received 29.5 -> 22.1 Mbit/s (2 UEs stranded) |
| (c) Real link, AppWeaver apply-codel, repeat 1 | xApp launched at 15.0 s, E2 control applied at 17.1 s (FIFO -> CoDel) | RTT climbs to ~420 ms under FIFO, falls to ~35 ms; goodput ~9.6 Mbit/s before and after (one dip at the swap: deleting the FIFO drops its backlog) |

Seed choice for (a): seed 104 is one of the two seeds with a throughput gain; per seed the live QoE-chain
throughput change is +18.8 / +0.7 / -0.9 / +12.8 / -0.4 % (seeds 101-105). The typical, flat case is
`demos/fig_kpm_dynamics_hotspot_s105.{pdf,png}` (HO 3, 1 -> cell 3; load moves, throughput -0.4%).
Say which seed is shown in the caption.

## 5. Suggested text-only statements (no float needed)

- "Across 8,700 records on three intent sets, AppWeaver composes the correct workflow for 69-94% of intents;
  on intents that no operator template solves, the catalog-aware LLM and the rule router score 0% while
  AppWeaver scores 55-94%."
- "Retrieving 8 of 81 Agent Cards matches putting all cards in the prompt (68.8% both) at one third of the
  prompt tokens."
- "Deployed on a 5G RAN model, the composed steering chain raised hotspot throughput by 6-8%; the
  energy-saving chain cut gNB energy by 41% but cost 23% throughput, which the twin predicted within 3 pp."
- "On a real 10 Mbit/s bufferbloated link, AppWeaver's CoDel action over E2 cut median RTT from ~420 ms to
  ~35 ms without goodput loss."

## 6. Not addressed / honest limits

- Batches A-C run on the FlexRIC emulator: composition and execution are measured, network effect is not
  (its KPM is random). D2/D3 provide the network effect for RC and TC chains; slice control has none.
- The energy-saving gate gap above; n = 5 per D2 cell (CIs wide).
- GLM comparison on C only.
