# Twin-vs-live KPI validation (T6)

Answers R1.2, R2.2 and R3.1: *how well does the digital twin predict what a composed workflow does to
the network?* The first submission's twin was not a network model; it is replaced by the experiment
below. Code: `evaluation/twin/` (`run_twin_validation.py`, `xapp_appweaver_actuator.c`, `Makefile`).
Results: `evaluation/runs/20261027T171217Z_T6_twin_vs_live{,_loadcal}/` (`manifest.json`, `summary.json`, `summary.md`, one
`result.json` per simulation with the policy, the RC commands and the KPI window).

## Substrate

- **RAN:** ns-3.42 with the mmWave/5G-LENA modules and the O-RAN E2 interface of Orange's
  ns-O-RAN-flexric (`scenario-zero-with_parallel_loging`): 1 LTE anchor eNB + 4 mmWave gNBs at 3.5 GHz,
  20 MHz, 600 m inter-site distance, UEs dropped uniformly in a 500 m disc with random-walk mobility
  (2–4 m/s), each with a 3.2 Mb/s downlink CBR flow. Setup and build: `~/ns-oran-flexric/APPWEAVER_SETUP.md`.
- **RIC:** the pinned FlexRIC of that project (E2AP v1.01, E2SM-KPM v3.00, E2SM-RC v1.03), one nearRT-RIC
  per simulation on its own ports.
- **xApp:** `xapp_appweaver_actuator` subscribes to KPM on every node (100 ms reports) and executes RC
  commands: handover control (E2SM-RC style 3, action 1) and cell switch-off (ns-O-RAN energy-state
  style 300). Its KPM capture and RC encoders are copied unchanged from the project's own xApps.
- **Decisions:** the AppWeaver emulated rApps (`rapps/runtime.py: decide()`), fed with the ns-3 KPM
  aggregated per cell exactly as on the portal (PRB normalised by the cluster maximum, per-UE throughput
  in Mbit/s).

ns-3's RAN functions accept only these two RC actions, so the workflows below are the composed chains
from the benchmark that end in an RC action the simulator can execute. Transport-QoS (TC) and slice
(SLICE) control have no service model in ns-O-RAN; those workflows run against the FlexRIC emulator in
batches A/B, whose random KPM gives no KPI fidelity, so they are **not** part of the twin experiment.

## Workflows

| Workflow | Chain (from `intents_v2.json`) | Policy (decided by the rApps) | RC execution |
|---|---|---|---|
| Energy saving | KPM → RAPP.ENERGY_SAVING → RC | cells whose normalised PRB load < 0.15 sleep | hand over each served UE to its best awake neighbour (L3 SINR from KPM), switch the cell off 0.3 s later; at least half the gNBs stay on; a cell is not switched off if a UE has no awake neighbour |
| Traffic steering | KPM → RAPP.TRAFFIC_STEERING → RC | hottest → coldest cell, 20 % of the hot cell's UEs if the PRB gap > 0.3 | hand over the hot cell's UEs with the best SINR towards the cold cell |
| QoE-driven steering | KPM → RAPP.QOE_PREDICTION → RAPP.TRAFFIC_STEERING → RC | at-risk cells (forecast MOS < 3) below the median forecast MOS shed 20 % of their UEs, preferably to the steering rApp's coldest cell | hand over the weakest-SINR UEs of each source cell to their best neighbour outside the source set |

## Twin, live and the protocol

- **Twin** = ns-3 instance A: `RngRun = p` (p = 1…8), 8 UEs (base) or 10 UEs (load-calibrated batch).
- **Live** = ns-3 instance B: `RngRun = p + 100` (independent UE drop, mobility and fading) and 10 UEs
  (+25 % offered load). The twin therefore knows the topology and configuration of the live network but
  neither its users' positions nor its load, which is the fidelity gap a deployed twin faces. The per-UE
  traffic model is fixed in the scenario source, so load is perturbed through the UE count.
- At t_act = 1.5 s after the first KPM report, AppWeaver runs the chain **on the twin** and obtains a
  cell-level policy (validate-before-deploy). The same policy is then deployed **unchanged on live** at the
  same point in its own run; UE-level handovers are resolved on the instance that executes them, from its
  own KPM, as an RC executor would.
- Every instance also runs a **no-op** (KPM only) with the same seed. A KPI delta is the workflow run minus
  the no-op run of the same instance over the window [t_act + 0.5 s, end of run], so seed-level
  variation cancels.
- **Predicted** delta = twin delta; **actual** delta = live delta. Reported per workflow and KPI over the
  8 pairs: mean relative change (delta / no-op level) predicted vs measured, the absolute error of the
  relative change in percentage points, MAPE of the deltas (only where the measured delta is non-zero),
  and sign agreement.

KPIs (all gNBs, mean over 100 ms reports in the window): DL PRBs used (Σ `RRU.PrbUsedDl` over UEs), DL
throughput (Σ `DRB.UEThpDl`), DL buffer occupancy (Σ `DRB.BufferSize.Qos`, the RLC queue; the scenario's
KPM carries no gNB-side delay measurement, so queue size stands in for RLC delay), and gNB energy (J per
simulated second, from ns-3's radio energy model).

## Results

Two batches, both with 8 seed pairs × 4 runs (no-op + 3 workflows) on twin and on live:

- `runs/20261027T171217Z_T6_twin_vs_live/` — **base**: twin 8 UEs, live 10 UEs (load unknown to the twin).
- `runs/20261027T171217Z_T6_twin_vs_live_loadcal/` — **load-calibrated**: twin 10 UEs (= live), so twin
  and live differ only in UE positions, mobility and fading. The live no-op runs are reused from the
  base batch (same inputs). Twin RngRun 3 with 10 UEs aborts inside ns-3 every time
  (`malloc(): invalid size`, also when run alone), so pair 3 is excluded and pair 9 (RngRun 9/109) was
  added before the results were looked at; the manifest records this.

**Simulator noise (A/A).** Every no-op of pairs 1–4 (twin and live) was re-run with the same seed
(`runs/20261027T171217Z_T6_twin_vs_live/aa_noop_repeat/noise.md`): energy and throughput repeat to
≤0.01 %, PRB to ≤0.27 %, buffer to ≤2.1 kB. Twin–live differences below are therefore not noise, but
the same bound applies to pairs where no RC command was issued: their deltas are noise, and their sign
agreement is a coin flip.

### Base batch (twin 8 UEs, live 10 UEs)

| Workflow | KPI | Pairs | Mean predicted change | Mean measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement |
|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +34.7% | -17.1% | 60.6 | 38712% (n=8) | 25% |
| energy_saving | dl_throughput_mbps | 8 | -2.2% | -15.7% | 13.5 | 112691% (n=8) | 50% |
| energy_saving | dl_buffer_kbytes | 8 | +73.5% | +258574.2% | 258500.8 | 95% (n=8) | 50% |
| energy_saving | energy_j_per_s | 8 | -21.4% | -25.7% | 10.5 | 40% (n=7) | 88% |
| traffic_steering | prb_used_dl | 8 | +95.1% | +10.7% | 84.4 | 349% (n=8) | 88% |
| traffic_steering | dl_throughput_mbps | 8 | -4.5% | -3.2% | 8.5 | 253% (n=8) | 62% |
| traffic_steering | dl_buffer_kbytes | 8 | +15376.7% | +3215.3% | 18278.1 | 67404% (n=8) | 75% |
| traffic_steering | energy_j_per_s | 8 | +16.6% | +7.5% | 15.5 | 672% (n=8) | 88% |
| qoe_steering | prb_used_dl | 8 | +34.4% | -14.0% | 49.3 | 144% (n=8) | 38% |
| qoe_steering | dl_throughput_mbps | 8 | +0.4% | -8.3% | 10.4 | 94% (n=8) | 62% |
| qoe_steering | dl_buffer_kbytes | 8 | +558505.8% | +51838.7% | 583644.0 | 104% (n=8) | 25% |
| qoe_steering | energy_j_per_s | 8 | +3.2% | -8.7% | 13.5 | 134% (n=8) | 12% |

### Load-calibrated batch (twin 10 UEs, live 10 UEs)

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement |
|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | -0.02 | -17.76 | -0.0% | -9.0% | 9.6 | 123% (n=8) | 62% |
| energy_saving | dl_throughput_mbps | 8 | -0.00 | -1.45 | -0.0% | -7.8% | 7.8 | 116% (n=8) | 38% |
| energy_saving | dl_buffer_kbytes | 8 | +1.10 | +712.15 | +73.2% | +53542.1% | 53629.5 | 106% (n=8) | 50% |
| energy_saving | energy_j_per_s | 8 | -582.52 | -1005.49 | -11.9% | -13.9% | 4.1 | 37% (n=5) | 100% |
| traffic_steering | prb_used_dl | 8 | +17.75 | +20.38 | +19.5% | +11.2% | 31.7 | 262% (n=8) | 75% |
| traffic_steering | dl_throughput_mbps | 8 | -1.03 | -0.86 | -6.3% | -4.9% | 8.4 | 189% (n=8) | 62% |
| traffic_steering | dl_buffer_kbytes | 8 | +236.10 | +515.30 | +24752.9% | +62029.6% | 86642.5 | 10532% (n=8) | 50% |
| traffic_steering | energy_j_per_s | 8 | +810.66 | +481.41 | +15.2% | +6.7% | 14.5 | 394% (n=8) | 88% |
| qoe_steering | prb_used_dl | 8 | +24.11 | +3.35 | +26.1% | +3.2% | 33.1 | 879% (n=8) | 62% |
| qoe_steering | dl_throughput_mbps | 8 | -0.82 | -1.37 | -3.9% | -7.4% | 11.5 | 63512% (n=8) | 50% |
| qoe_steering | dl_buffer_kbytes | 8 | -126.96 | +766.11 | +20723.3% | +26498.7% | 46925.5 | 44985% (n=8) | 12% |
| qoe_steering | energy_j_per_s | 8 | +611.47 | +67.00 | +11.1% | +1.4% | 15.6 | 652% (n=7) | 25% |

Relative changes are delta / no-op level. Buffer occupancy is near zero in several no-op runs
(0.02–2 kB), so its relative change and MAPE are not meaningful; read the absolute deltas (kB).
MAPE of deltas is dominated by pairs whose measured delta is close to zero and is reported for
completeness only.

### What the experiment shows

1. **Energy is predicted well.** Energy saving: the twin predicts −11.9 % gNB energy and live measures
   −13.9 % (4.1 pp error, same sign in 8/8 pairs) with calibrated load; −21.4 % vs −25.7 % (88 %) in the
   base batch. Cell switch-off is a cell-level decision whose effect barely depends on where the users are.
2. **Load KPIs need the twin's load to match live.** With the twin under-loaded (base), PRB changes
   had the wrong sign in most energy-saving and QoE-steering pairs (25 % and 38 % sign agreement): an
   8-UE twin has spare capacity, the 10-UE live network does not. With matched load, sign agreement for
   PRB rises to 62 % / 75 % / 62 % (energy saving / traffic steering / QoE steering).
3. **User-level state is what the twin lacks.** In the calibrated batch the twin switched off cells that
   were *empty in the twin* (predicted PRB and throughput change ≈ 0), while in live the same cells
   served 1–3 UEs that had to be handed over first (`rc_commands.txt`: e.g. pair 6, twin `OFF 5, OFF 4`,
   live `HO 10 2, HO 9 2, OFF 5, HO 2 2, OFF 4`). Live lost 9.0 % PRB and 7.8 % throughput that the twin
   did not predict. Handover-based steering moves different UEs in twin and live for the same reason.
4. **Throughput and queue changes are not predicted reliably** (sign agreement 38–62 % for throughput,
   12–50 % for buffer): these are small changes (a few %) driven by which UEs move, of the same order as
   the twin–live difference in UE placement.

**For the paper.** A twin that matches the live network's configuration and load predicts the energy
effect of a cell-level policy within a few percentage points, and the direction of the PRB change in
most cases; it does not predict UE-level throughput or queueing effects without the live UE state
(positions, channel), which a deployed twin would have to ingest from O1/E2 measurements. This bounds
the claim of §III-C: validation on the twin is a guard against the wrong policy class (e.g. sleeping a
loaded cell), not a forecast of per-user QoS.


## Limitations (stated in the paper)

- Both twin and live are simulations; live differs from the twin in seed and load, not in the radio
  model. The experiment bounds the error from not knowing the live users and load; it does not
  measure ns-3's fidelity against a physical network.
- Only RC-actuated workflows (handover, cell switch-off) can be validated on this substrate.
- 8 s simulations (25–50× slower than real time) give a 5–6 s post-action window; short-term KPIs only.
- The rApps are emulated decision models; the experiment validates the twin's prediction of the
  *deployed policy's* effect, not the quality of the rApps' decisions.
