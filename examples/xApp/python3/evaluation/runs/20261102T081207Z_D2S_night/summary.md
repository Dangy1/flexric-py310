# Twin-vs-live results - `20261102T081207Z_D2S_night`

Runs: 20 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 5 | -20.48 | -20.35 | -23.7% | -23.6% | 1.7 | 11% (n=4) | 100% | 100% (n=4) |
| energy_saving | dl_throughput_mbps | 5 | -5.87 | -5.88 | -20.0% | -20.0% | 0.0 | 0% (n=4) | 100% | 100% (n=4) |
| energy_saving | dl_delay_ms | 5 | -0.05 | -0.03 | -5.0% | -3.2% | 2.9 | 236% (n=4) | 100% | 100% (n=4) |
| energy_saving | dl_buffer_kbytes | 5 | +2389.14 | +2389.21 | +33948971.2% | +24186643.1% | 7240772.5 | 0% (n=4) | 100% | 100% (n=4) |
| energy_saving | energy_j_per_s | 5 | -1578.48 | -1575.27 | -33.2% | -33.2% | 0.6 | 3% (n=4) | 100% | 100% (n=4) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 5 | 4 | 0 | 0 | 1 | 100% (5/5) [57, 100] | 100% (4/4) [51, 100] | 100% (4/4) [51, 100] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |
| pooled | 5 | 4 | 0 | 0 | 1 | 100% (5/5) [57, 100] | 100% (4/4) [51, 100] | 100% (4/4) [51, 100] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | energy_saving | sleep [4, 5] | E +41.1% saved, PRB(rem) -6.9%, 4 cmd | accept | E +42.1% saved, PRB(rem) -11.7%, 4 cmd | accept |
| 3 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -10.3%, 4 cmd | accept | E +40.7% saved, PRB(rem) -4.7%, 4 cmd | accept |
| 4 | energy_saving | sleep [4, 5] | E +41.6% saved, PRB(rem) -9.0%, 4 cmd | accept | E +41.1% saved, PRB(rem) -6.6%, 4 cmd | accept |
| 5 | energy_saving | sleep [4, 5] | E +41.4% saved, PRB(rem) -8.1%, 4 cmd | accept | E +41.8% saved, PRB(rem) -10.1%, 4 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -6.2 (min -6.6, max -5.7, n=20); dl_throughput_mbps mean -33.1 (min -35.6, max -31.0, n=20); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=17); prb_used_dl_per_cell mean -7.6 (min -9.4, max -5.0, n=44).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 100%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 100%, live 100% of 5 cases.

Runs in which the deployed policy produced RC commands:

- live energy_saving: 4
- twin energy_saving: 4
