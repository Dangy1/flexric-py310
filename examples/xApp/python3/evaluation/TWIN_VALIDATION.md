# Twin-vs-live KPI validation and deploy gate (T6v2)

Answers R1.2, R2.2 and R3.1: *how well does the digital twin predict what a composed workflow does to
the network, and does validating on the twin keep harmful policies from being deployed?* (owner item
P1-2, `docs/FABLE_REVIEW_AND_PLAN.md` §5.2: Validate-2 as a deploy gate, fidelity by sync level).

Code: `evaluation/twin/` (`run_twin_validation.py`, `xapp_appweaver_actuator.c`, `Makefile`,
`prefix_gate.py`, `test_twin_validation.py`). Results (T6v2, simulator fixed on 2026-10-28):

| Batch | Twin state sync | Directory (`evaluation/runs/`) |
|---|---|---|
| base | none: twin 8 UEs, live 10 UEs | `20261028T085338Z_T6v2_twin_vs_live/` (+ `aa_noop_repeat/`, `prefix_reanalysis/`) |
| load-calibrated | load: twin 10 UEs = live | `20261028T085338Z_T6v2_twin_vs_live_loadcal/` (+ `aa_noop_repeat/`) |
| placement-synced | load + live UE positions at t_act | `20261028T085338Z_T6v2_twin_vs_live_positions/` (+ `ue_positions/`) |

Each directory has `manifest.json` (written before the first run: protocol, gate thresholds, exclusion
rule, binaries' SHA-256, host context; completed at the end with the excluded pairs and the host
state), `summary.{json,md}` (KPIs from the ns-3 traces, the primary analysis), `summary_e2kpm.{json,md}`
(the same analysis on the E2 KPM stream) and per run `result.json` (policy, RC commands with their
simulated dispatch time, KPI window, both KPI sources), `ns3.cmd`, `rc_commands.txt`, `rc_acks.txt`.
Bulky per-run traces (`kpm.csv`, `ns3_out/`, logs; ≈35 MB per run) stay in
`~/flexric/build/examples/xApp/python3/evaluation/twin/build/runs/`.

The 2026-10-27 batches (`20261027T171217Z_T6_twin_vs_live{,_loadcal}`) ran on the simulator before its
fixes; they are kept as the **pre-fix** rows (Appendix), not as paper numbers.

## Substrate

- **RAN:** ns-3.42 with the mmWave/5G-LENA modules and the O-RAN E2 interface of Orange's
  ns-O-RAN-flexric (`scenario-zero-with_parallel_loging`): 1 LTE anchor eNB + 4 mmWave gNBs at 3.5 GHz,
  20 MHz, 600 m inter-site distance, UEs dropped uniformly in a 500 m disc (or at given positions, below)
  with random-walk mobility (2–4 m/s), each with a 3.2 Mb/s downlink CBR flow. Setup, build and the
  2026-10-28 fixes (sim-time KPM stamps, immediate reporting, noValue records, RC cell ids > 9 and
  switch-on, subscription delete, `uePositionFile`): `simulator/ns-oran-flexric/APPWEAVER_SETUP.md` §11.
- **RIC:** the pinned FlexRIC of that project (`~/flexric-taap`, E2AP v1.01, E2SM-KPM v3.00, E2SM-RC
  v1.03). One nearRT-RIC per simulation on its own ports (E2 36500 + 10·slot, E42 36501 + 10·slot, two
  slots) so two simulations run side by side without touching the simulator session's RIC (36423) or
  AppWeaver's live stack (36421/36422, 127.0.0.2).
- **xApp:** `xapp_appweaver_actuator` subscribes to KPM on every node (100 ms reports, immediate start)
  and executes RC commands: handover control (E2SM-RC style 3, action 1), cell switch-off/on (ns-O-RAN
  energy-state style 300, `OFF <cell>` / `ON <cell>`), cell ids as decimal strings of any length
  (patch `simulator/ns-oran-flexric/patches/appweaver-actuator-0001-*`, applied).
- **Decisions:** the AppWeaver emulated rApps (`rapps/runtime.py: decide()`), fed with the E2 KPM
  aggregated per cell exactly as on the portal (PRB normalised by the cluster maximum, per-UE throughput
  in Mbit/s). Decisions always use the E2 stream, as a RIC would.

ns-3's RAN functions accept only these RC actions, so the workflows are the composed chains from the
benchmark that end in an RC action the simulator can execute. TC and SLICE control have no service model
in ns-O-RAN and are not part of the twin experiment.

## Workflows

| Workflow | Chain (from `intents_v2.json`) | Policy (decided by the rApps) | RC execution |
|---|---|---|---|
| Energy saving | KPM → RAPP.ENERGY_SAVING → RC | cells whose normalised PRB load < 0.15 sleep | hand over each served UE to its best awake neighbour (L3 SINR from KPM), switch the cell off 0.3 s later; at least half the gNBs stay on; a cell is not switched off if a UE has no awake neighbour |
| Traffic steering | KPM → RAPP.TRAFFIC_STEERING → RC | hottest → coldest cell, 20 % of the hot cell's UEs if the PRB gap > 0.3 | hand over the hot cell's UEs with the best SINR towards the cold cell |
| QoE-driven steering | KPM → RAPP.QOE_PREDICTION → RAPP.TRAFFIC_STEERING → RC | at-risk cells (forecast MOS < 3) below the median forecast MOS shed 20 % of their UEs, preferably to the steering rApp's coldest cell | hand over the weakest-SINR UEs of each source cell to their best neighbour outside the source set |

## Protocol

- **Twin** = ns-3 instance A, `RngRun = p`; **live** = instance B, `RngRun = p + 100` (independent UE
  drop, mobility and fading), 10 UEs. Pairs p = 1…9 in every batch.
- **Sync levels of the twin.** *none*: 8 UEs (load unknown, live has +25 %). *load*: 10 UEs.
  *positions*: 10 UEs placed at the live UEs' positions at t_act: the live no-op of the pair runs first,
  its `ue_position.txt` rows at sim time t_act (IMSI = id, sim ms = timestamp − simid) are written as
  `ue_index,x,y,z` (`ue_positions/pair<p>_*.csv`, copied into each twin run as `ue_positions_in.csv`) and
  passed as `--uePositionFile`. Only positions are synced: the twin's random walk (direction, speed) and
  fading come from its own seed, and UEs attach to the closest node at t = 0 rather than inheriting the
  live serving cell. By t_act the twin UEs have walked 4–8 m from the synced points.
- **Clock.** Since the fixes, KPM `collectStartTime` is simulated time and reporting starts at
  subscription (first report at 0.16–0.21 s). t_act and the window are therefore absolute simulated
  times, identical for twin, live and no-op: the chain runs at **t_act = 2.0 s** (≥ 1.8 s of KPM history;
  a run with < 0.5 s is marked failed), KPIs are averaged over **(2.5 s, 7.9 s]** (traffic stops at
  7.9 s). Pre-fix: t_act = 1.5 s after the first report (≈2.6 s), window ≈ [3.1, 7.9] s.
- At t_act AppWeaver runs the chain **on the twin** and obtains a cell-level policy (which cells sleep,
  which cells shed load and where to). The same policy is deployed **unchanged on live** at t_act of its
  own run; UE-level handovers are resolved on the instance that executes them, from its own KPM.
- Every instance also runs a **no-op** (KPM only) with the same seed; a KPI delta is workflow run minus
  no-op run of the same instance. Predicted delta = twin delta, actual delta = live delta.
- **Exclusion rule (declared in every manifest before the runs):** a pair is excluded iff one of its
  runs still fails after one automatic retry; no replacement pairs. The live no-op runs of the
  load-calibrated and placement-synced batches are copied from the base batch (identical inputs).

### KPI sources (changed in T6v2)

The base batch showed that the E2 KPM values are not usable as KPIs: in same-seed runs with **no** RC
command the E2 PRB of a cell differed by up to 13× (twin pair 9: cell 2 at 3.6 vs 46.9 PRBs), while the
ns-3 traces, serving cells and energy were identical. Cause: ns-3's E2 DU report and its own 100 ms DU
logger (`du-cell-<c>.txt`) read and reset one shared per-UE calculator; the E2 report covers only the
φ ms since the logger's last write. With immediate reporting, φ is the wall-clock-dependent subscription
phase (0.3–98 ms across runs; pre-fix the gated start fixed it). The KPIs of T6v2 are therefore taken
from the ns-3 traces (`KPI_SOURCE` in the code, `kpi_source` in `summary.json`):

| KPI | Source |
|---|---|
| `prb_used_dl` (total and per cell) | full-period PRB rebuilt from both consumers of the calculator: period k = (φ·E2[k] + (100−φ)·logger[(k+1)·100 ms]) / 100, Σ `RRU.PrbUsedDl.UEID` over UEs, mean over the 54 periods of the window (pre-fix runs: logger alone) |
| `dl_throughput_mbps` | `DlPdcpStats.txt` (ns-3 PDCP stats, 0.25 s epochs, epochs inside the window: [2.5, 7.75) s): bytes received by all UEs — UE-side goodput, so UEs left without service count |
| `dl_delay_ms` (new) | `DlPdcpStats.txt`: PDCP DL delay, mean weighted by received PDUs |
| `dl_buffer_kbytes` | `du-cell-<c>.txt`: Σ `DRB.BufferSize.Qos.UEID` (RLC queue) at the logger writes |
| `energy_j_per_s` | ns-3 radio energy model (`energyfilecell<c>.csv`), unchanged |

The E2-sourced analysis is kept in `summary_e2kpm.*`. The switch was decided after looking at the base
batch's E2 results (the anomaly was found there); thresholds, windows, pairs and decisions are unchanged,
and every batch, including the pre-fix ones, is reported with both sources. The gate's confusion counts
are the same under both PRB estimators of the trace source (logger alone vs rebuilt).

**A/A noise (same-seed no-op repeats, `aa_noop_repeat/noise.md`):** pairs 1–4 twin (8 UEs) and live,
pairs 1–4 twin (10 UEs). Throughput, delay, buffer and energy repeat exactly (0.00 %). PRB repeats to
≤ 2.6 % (total) / ≤ 5.2 % (per cell) in the worst case (twin pair 2, report phases 0.25 vs 98.4 ms), ≤ 0.3 %
otherwise. The E2 values of the same repeats differ by up to 74 % (PRB), 8 % (throughput), 172 % (buffer).
Deltas below ≈ 3 % PRB are therefore noise; the throughput and energy deltas are exact.

## Deploy gate (Validate-2)

Thresholds, declared in the code (`GATE`) and written into every manifest before the first run:

| Workflow | Accept iff | Quantities (each instance vs its own no-op, KPI window) |
|---|---|---|
| energy_saving | energy saving ≥ 5 % **and** PRB increase on remaining cells ≤ 30 % | energy over all gNBs; PRB summed over the gNBs that instance did not switch off |
| traffic_steering, qoe_steering | hot-cell PRB reduction ≥ 5 % **and** throughput loss ≤ 5 % | PRB summed over the policy's source cells; throughput over all UEs |

The twin verdict uses the predicted (twin) quantities, the live outcome the measured (live) quantities
under the same thresholds. A policy that yields no RC command changes nothing and is rejected by these
rules on both sides. Reported per workflow and pooled: accuracy, precision and recall of *accept*,
specificity (harmful or useless policies blocked), and the live accept rate (= precision of deploying
everything without a twin), all with Wilson 95 % CIs. Per-pair verdicts and quantities: `summary.md`.

## Runs and host

Each batch: 9 pairs × (no-op + 3 workflows) × (twin, live) = 72 jobs, 2 in parallel under `nice -n 10`,
≈ 250–300 s wall per 8-s simulation (incl. E2 setup). Base 10:53–13:24, load-calibrated 13:24–15:53,
placement-synced 15:53–18:30, A/A 18:30–18:58 (2026-10-28, local time). AppWeaver's final Batch A
(`run_harness.py --label A_final_gptoss120b_spark1`: portal, nearRT-RIC 36421/36422, emulator, twin
emulator on 127.0.0.2, LLM calls to spark1) ran during all of it; manifests record the process list and
load average at start and end (1-min load 0.7–2.3 on 16 threads).

Excluded pairs (rule above): load-calibrated pairs **3** (twin `RngRun=3`, 10 UEs: ns-3 aborts with
`malloc(): invalid size` before t_act, every time — as pre-fix) and **7** (twin traffic steering: ns-3
aborts with the same error 0.1 s after the handover `HO 6 2`, both attempts). No exclusions in the base and
placement-synced batches (pair 3 runs with the position input).

## Results

Fidelity per sync level, trace KPIs. Cells: sign agreement / mean absolute error of the relative change
(pp); in brackets the number of pairs and the sign agreement over pairs where both twin and live issued RC
commands ("acted"; elsewhere both deltas are noise). Pre-fix columns: the 2026-10-27 runs re-analysed with
the same KPI sources and gate (`prefix_reanalysis/`).

| Workflow / KPI | pre-fix, none | pre-fix, load | fixed, none | fixed, load | fixed, load + positions |
|---|---|---|---|---|---|
| energy_saving / energy | 88% / 10.5 (8; acted 100% of 7) | 100% / 4.1 (8; 100% of 5) | 100% / 1.7 (9; 100% of 2) | 86% / 4.6 (7; 0% of 1) | 100% / 0.0 (9; none acted) |
| energy_saving / PRB | 38% / 32.2 (8; 43% of 7) | 38% / 10.0 (8; 20% of 5) | 22% / 2.7 (9; 50% of 2) | 43% / 10.4 (7; 0% of 1) | 22% / 0.3 (9; none) |
| energy_saving / throughput | 25% / 14.1 (8; 14% of 7) | 38% / 6.1 (8; 0% of 5) | 89% / 0.4 (9; 50% of 2) | 86% / 4.4 (7; 0% of 1) | 100% / 0.0 (9; none) |
| traffic_steering / energy | 88% / 15.5 (8; 100% of 7) | 88% / 14.5 (8; 88% of 8) | 56% / 15.8 (9; 56% of 9) | 71% / 7.4 (7; 80% of 5) | 78% / 6.5 (9; 75% of 8) |
| traffic_steering / PRB | 88% / 34.6 (8; 100% of 7) | 75% / 34.0 (8; 75% of 8) | 56% / 32.0 (9; 56% of 9) | 71% / 16.3 (7; 80% of 5) | 67% / 12.5 (9; 75% of 8) |
| traffic_steering / throughput | 75% / 9.5 (8; 86% of 7) | 62% / 13.3 (8; 62% of 8) | 67% / 8.5 (9; 67% of 9) | 57% / 7.4 (7; 60% of 5) | **89% / 5.0** (9; 88% of 8) |
| traffic_steering / delay | 88% (8) | 88% (8) | 67% (9) | 86% (7) | 100% (9) |
| qoe_steering / energy | 12% / 13.5 (8; 20% of 5) | 25% / 15.6 (8; 50% of 4) | 56% / 12.5 (9; 62% of 8) | 86% / 16.4 (7; 86% of 7) | 44% / 15.3 (9; 50% of 8) |
| qoe_steering / PRB | 12% / 23.6 (8; 20% of 5) | 50% / 29.0 (8; 75% of 4) | 56% / 26.1 (9; 62% of 8) | 86% / 33.5 (7; 86% of 7) | 44% / 24.6 (9; 50% of 8) |
| qoe_steering / throughput | 25% / 9.6 (8; 40% of 5) | 38% / 14.1 (8; 75% of 4) | 67% / 7.7 (9; 75% of 8) | 43% / 15.8 (7; 43% of 7) | 78% / 8.8 (9; 88% of 8) |
| qoe_steering / delay | 25% (8) | 38% (8) | 67% (9) | 86% (7) | 67% (9) |

Mean predicted vs measured relative change, selected rows (all rows: `summary.md` of each batch):

| Workflow / KPI | pre-fix, none | pre-fix, load | fixed, none | fixed, load | fixed, load + positions |
|---|---|---|---|---|---|
| energy_saving / energy | −21.4 % vs −25.7 % | −11.9 % vs −13.9 % | −5.2 % vs −3.5 % | +1.0 % vs −3.6 % | 0 vs 0 |
| traffic_steering / PRB | +36.0 % vs +16.3 % | +35.2 % vs +10.9 % | +27.9 % vs −4.1 % | +16.7 % vs +9.6 % | +17.1 % vs +18.4 % |
| traffic_steering / throughput | −4.3 % vs −2.7 % | −5.2 % vs −8.0 % | −6.4 % vs −6.7 % | −1.8 % vs −4.7 % | −5.7 % vs −6.7 % |
| traffic_steering / energy | +16.6 % vs +7.5 % | +15.2 % vs +6.7 % | +13.2 % vs −2.5 % | +8.9 % vs +5.0 % | +10.0 % vs +10.0 % |
| qoe_steering / PRB | +7.6 % vs −13.1 % | +21.5 % vs +3.1 % | +11.2 % vs −6.6 % | +23.6 % vs −8.0 % | +7.8 % vs +1.9 % |
| qoe_steering / throughput | −0.6 % vs −5.4 % | −4.3 % vs −6.8 % | −6.6 % vs −3.2 % | +3.4 % vs −7.7 % | −8.2 % vs −6.5 % |

### Gate

| Batch | Workflow | n | TP/FP/FN/TN | Accuracy | Precision (accept) | Recall (accept) | Specificity | Live accept rate |
|---|---|---|---|---|---|---|---|---|
| pre-fix, none | energy_saving | 8 | 4/3/0/1 | 62% (5/8) [31–86] | 57% (4/7) [25–84] | 100% (4/4) [51–100] | 25% (1/4) [5–70] | 50% (4/8) [22–78] |
| pre-fix, none | traffic_steering | 8 | 0/4/4/0 | 0% (0/8) [0–32] | 0% (0/4) [0–49] | 0% (0/4) [0–49] | 0% (0/4) [0–49] | 50% (4/8) [22–78] |
| pre-fix, none | qoe_steering | 8 | 0/2/3/3 | 38% (3/8) [14–69] | 0% (0/2) [0–66] | 0% (0/3) [0–56] | 60% (3/5) [23–88] | 38% (3/8) [14–69] |
| pre-fix, none | **pooled** | 24 | 4/9/7/4 | 33% (8/24) [18–53] | 31% (4/13) [13–58] | 36% (4/11) [15–65] | 31% (4/13) [13–58] | 46% (11/24) [28–65] |
| pre-fix, load | energy_saving | 8 | 3/2/0/3 | 75% (6/8) [41–93] | 60% (3/5) [23–88] | 100% (3/3) [44–100] | 60% (3/5) [23–88] | 38% (3/8) [14–69] |
| pre-fix, load | traffic_steering | 8 | 0/4/2/2 | 25% (2/8) [7–59] | 0% (0/4) [0–49] | 0% (0/2) [0–66] | 33% (2/6) [10–70] | 25% (2/8) [7–59] |
| pre-fix, load | qoe_steering | 8 | 0/1/4/3 | 38% (3/8) [14–69] | 0% (0/1) [0–79] | 0% (0/4) [0–49] | 75% (3/4) [30–95] | 50% (4/8) [22–78] |
| pre-fix, load | **pooled** | 24 | 3/7/6/8 | 46% (11/24) [28–65] | 30% (3/10) [11–60] | 33% (3/9) [12–65] | 53% (8/15) [30–75] | 38% (9/24) [21–57] |
| fixed, none | energy_saving | 9 | 1/1/0/7 | 89% (8/9) [57–98] | 50% (1/2) [9–91] | 100% (1/1) [21–100] | 88% (7/8) [53–98] | 11% (1/9) [2–43] |
| fixed, none | traffic_steering | 9 | 2/3/1/3 | 56% (5/9) [27–81] | 40% (2/5) [12–77] | 67% (2/3) [21–94] | 50% (3/6) [19–81] | 33% (3/9) [12–65] |
| fixed, none | qoe_steering | 9 | 1/2/5/1 | 22% (2/9) [6–55] | 33% (1/3) [6–79] | 17% (1/6) [3–56] | 33% (1/3) [6–79] | 67% (6/9) [35–88] |
| fixed, none | **pooled** | 27 | 4/6/6/11 | 56% (15/27) [37–72] | 40% (4/10) [17–69] | 40% (4/10) [17–69] | 65% (11/17) [41–83] | 37% (10/27) [22–56] |
| fixed, load | energy_saving | 7 | 0/0/1/6 | 86% (6/7) [49–97] | -- (0/0) | 0% (0/1) [0–79] | 100% (6/6) [61–100] | 14% (1/7) [3–51] |
| fixed, load | traffic_steering | 7 | 2/2/1/2 | 57% (4/7) [25–84] | 50% (2/4) [15–85] | 67% (2/3) [21–94] | 50% (2/4) [15–85] | 43% (3/7) [16–75] |
| fixed, load | qoe_steering | 7 | 2/2/3/0 | 29% (2/7) [8–64] | 50% (2/4) [15–85] | 40% (2/5) [12–77] | 0% (0/2) [0–66] | 71% (5/7) [36–92] |
| fixed, load | **pooled** | 21 | 4/4/5/8 | 57% (12/21) [37–76] | 50% (4/8) [22–78] | 44% (4/9) [19–73] | 67% (8/12) [39–86] | 43% (9/21) [24–63] |
| fixed, load + positions | energy_saving | 9 | 0/0/0/9 | 100% (9/9) [70–100] | -- (0/0) | -- (0/0) | 100% (9/9) [70–100] | 0% (0/9) [0–30] |
| fixed, load + positions | traffic_steering | 9 | 2/2/1/4 | 67% (6/9) [35–88] | 50% (2/4) [15–85] | 67% (2/3) [21–94] | 67% (4/6) [30–90] | 33% (3/9) [12–65] |
| fixed, load + positions | qoe_steering | 9 | 1/1/4/3 | 44% (4/9) [19–73] | 50% (1/2) [9–91] | 20% (1/5) [4–62] | 75% (3/4) [30–95] | 56% (5/9) [27–81] |
| fixed, load + positions | **pooled** | 27 | 3/3/5/16 | 70% (19/27) [52–84] | 50% (3/6) [19–81] | 38% (3/8) [14–69] | 84% (16/19) [62–94] | 30% (8/27) [16–48] |

Pooled gate on the E2-KPM source (`summary_e2kpm.md`), for comparison: pre-fix none 54 % accuracy,
precision 40 %, recall 44 %; pre-fix load 71 % / 64 % / 70 %; fixed none 56 % / 38 % / 30 %; fixed load
62 % / 50 % / 38 %; fixed positions 63 % / 50 % / 50 %. The pre-fix load-calibrated batch looked best on
the E2 source; with the UE-side throughput it is the second worst, because the E2 KPIs (gNB-side) do not
see UEs that lose service (next section).

### What the experiment shows

1. **The gate does not yet separate good from bad policies reliably.** Pooled over 21–27 (pair,
   workflow) cases per batch, precision of "accept" is 40–50 % against a 30–43 % live accept rate
   (deploy-everything baseline), recall 38–44 %, and every CI spans ≥ 30 pp. What improves with sync is
   **specificity**: 65 % (none) → 67 % (load) → 84 % (load + positions) of the policies that fail live
   are also rejected on the twin, so the twin mostly errs on the safe side. Accuracy rises 56 % → 57 % →
   70 %, but part of the positions batch's gain comes from energy-saving cases that were no-ops on both
   sides (0 sleep decisions in that batch).
2. **Placement sync helps the KPIs that depend on which UEs move.** Traffic steering (the workflow that
   acted in 8–9 pairs in every fixed batch): throughput sign agreement 67 % → 57 % → **89 %**, error
   8.5 → 7.4 → **5.0 pp**; PRB error 32.0 → 16.3 → 12.5 pp; energy error 15.8 → 7.4 → 6.5 pp, and the mean
   predicted vs measured PRB change becomes +17.1 % vs +18.4 % (none: +27.9 % vs −4.1 %). QoE-driven
   steering improves in throughput (75 % → 43 % → 88 % sign agreement on acted pairs) but not in PRB or
   energy: its source cells are chosen from MOS forecasts that flip with small KPM differences, so twin
   and live often shed from different cells.
3. **Load sync alone is not monotone.** With matched UE count but random positions, QoE steering got
   worse in throughput (43 %) and two of nine twin pairs crashed ns-3 (excluded). Matching load without
   matching placement changes *which* cells are hot, which the cell-level policy depends on.
4. **Energy saving is executed with harm the E2 view does not show.** The policy (hand over, switch the
   cell off 0.3 s later) cut 1–3 UEs off the downlink entirely (PDCP RxBytes = 0 for the rest of the run,
   while the same UEs were served in the no-op run of the same seed) in 14 of the 31 runs that switched a
   cell off (pre-fix and fixed, twin and live), including UEs that RC had just handed over. The gNB-side
   E2 KPIs simply lose these UEs; the UE-side throughput and PDCP delay expose them (pre-fix live energy
   saving: −15.5 % throughput, +337 % delay). Part of the "energy saved" in the pre-fix tables is traffic
   that was no longer served. (Independently of any policy, 47 UEs in 21 of the 53 fixed-simulator no-op
   runs receive no downlink in the window at all: the 500 m UE disc reaches beyond usable mmWave
   coverage. These UEs are the same in a workflow run and its no-op and cancel in the deltas.)
5. **After the simulator fixes, the energy-saving rApp rarely fires** (2/9 base, 1/7 load, 0/9 positions
   vs 7/8 pre-fix): with immediate reporting the decision snapshot at t_act sees the E2 PRB at a random
   report phase. The workflow still validates the twin's energy prediction where it acts (100 % sign,
   1.7 pp in base), but on too few cases for a claim.
6. **The pre-fix "energy is predicted well" result is not reproduced as a gate result.** Pre-fix energy
   predictions had the right sign in every acted pair, but the gate, which also checks the load moved to
   the remaining cells, accepted 3 of 4 (base) and 2 of 5 (load-calibrated) energy-saving policies that
   failed live (specificity 25 % and 60 %).

**For the paper.** Validate-2 on an ns-3 twin is a *conservative filter*, not a predictor: with load and
placement synced it rejected 84 % [62–94] of the policies that did not meet their objective live, but it
also rejected 5 of 8 policies that would have met it, and its precision (50 % [19–81]) is not
distinguishable from deploying everything (30 % [16–48]) at n = 27. Twin fidelity for UE-movement KPIs
improves monotonically only when UE placement is synced; load alone does not suffice. Report the KPIs
from UE-side measurements; gNB-side E2 KPM hides UEs that lose service.

## Limitations (stated in the paper)

- Both twin and live are ns-3; live differs from the twin in seed, load and placement, not in the radio
  model. The experiment bounds the error from not knowing the live users; it does not measure ns-3's
  fidelity against a physical network.
- Only RC-actuated workflows (handover, cell switch-off) are validated on this substrate.
- 8-s simulations (≈ 30–40× slower than real time on this host) give a 5.4-s KPI window; short-term
  KPIs only. n = 7–9 pairs per workflow: every gate CI is wide.
- Placement sync sets initial positions only (no walk direction/speed, no serving cell, no channel
  state); twin and live random walks diverge after t = 0.
- "Cell off" in ns-O-RAN = TX power 0 dBm + noise figure 100 dB; UEs of a switched-off cell are not
  always re-attached by the simulator (finding 4), so energy-saving outcomes include stranded UEs. Some
  UEs are out of coverage in every run of a seed (finding 4); they cancel in the deltas but lower the
  throughput levels.
- The rApps are emulated decision models; the experiment validates the twin's prediction of the deployed
  policy's effect, not the quality of the rApps' decisions. Their inputs are the E2 KPM, whose PRB/
  throughput depend on the report phase (KPI sources); twin and live decisions inherit that noise.

## Reproduce

```bash
source ~/anaconda3/etc/profile.d/conda.sh && conda activate flexric-py310
cd ~/flexric/examples/xApp/python3/evaluation/twin
make OUT=$HOME/flexric/build/examples/xApp/python3/evaluation/twin/build    # actuator
python -m pytest -q test_twin_validation.py
R=$HOME/flexric/build/examples/xApp/python3/evaluation/twin/build/runs/<ts>_T6v2
nice -n 10 python run_twin_validation.py --pairs 1-9 --parallel 2 --twin-ues 8  --out ${R}_twin_vs_live --host-context "..."
nice -n 10 python run_twin_validation.py --pairs 1-9 --parallel 2 --twin-ues 10 --out ${R}_twin_vs_live_loadcal --reuse-live-noop ${R}_twin_vs_live
nice -n 10 python run_twin_validation.py --pairs 1-9 --parallel 2 --twin-ues 10 --sync positions --out ${R}_twin_vs_live_positions --reuse-live-noop ${R}_twin_vs_live
nice -n 10 python run_twin_validation.py --pairs 1-4 --parallel 2 --twin-ues 8 --aa-of ${R}_twin_vs_live --out ${R}_twin_vs_live/aa_noop_repeat
python run_twin_validation.py --out <batch dir> --report-only        # re-analyse (adds trace KPIs to old results)
python prefix_gate.py <pre-fix batch dir with kpm.csv/ns3_out> <out dir> [--live-noop-from <dir>]
```

## Appendix: pre-fix batches (2026-10-27)

`20261027T171217Z_T6_twin_vs_live{,_loadcal}`: wall-clock KPM stamps, reporting gated ≥ 1 s, t_act =
1.5 s after the first report, KPIs from the E2 KPM stream, 8 pairs (load-calibrated: pairs 1, 2, 4–9; twin
`RngRun=3` with 10 UEs aborted). Their `summary.md` files hold the original tables (energy saving:
predicted −21.4 % vs measured −25.7 % gNB energy in the base batch, −11.9 % vs −13.9 % load-calibrated, sign
agreement 88 % / 100 %; PRB sign agreement 25–88 %; throughput 38–62 %). Their A/A repeat
(`aa_noop_repeat/noise.md`, PRB ≤ 0.27 %) predates the phase problem: the gated start fixed the report
phase. They are superseded by T6v2 for three reasons: the simulator fixes change the indication clock and
the window; the E2 KPIs they used miss UEs left without service (finding 4); and the gate had not been
declared. The re-analysis of those runs with the T6v2 KPI sources and gate is in
`20261028T085338Z_T6v2_twin_vs_live/prefix_reanalysis/{base,loadcal}/` (archived runs unchanged; the
gate thresholds were fixed before T6v2 ran but applied to these runs afterwards).
