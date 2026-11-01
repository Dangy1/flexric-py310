# Twin-vs-live results - `20261101T103300Z_D2_night`

Runs: 20 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 5 | -22.24 | -8.25 | -25.6% | -9.9% | 16.9 | 32% (n=5) | 80% | 80% (n=5) |
| energy_saving | dl_throughput_mbps | 5 | -6.60 | -6.68 | -22.4% | -22.7% | 0.3 | 2% (n=5) | 100% | 100% (n=5) |
| energy_saving | dl_delay_ms | 5 | -0.06 | +2.83 | -5.6% | +264.4% | 270.9 | 201% (n=5) | 100% | 100% (n=5) |
| energy_saving | dl_buffer_kbytes | 5 | +2687.76 | +2695.76 | +40364914.0% | +33587785.3% | 7758070.6 | 1% (n=5) | 100% | 100% (n=5) |
| energy_saving | energy_j_per_s | 5 | -1893.83 | -1957.55 | -39.7% | -41.3% | 2.5 | 7% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| pooled | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -10.3%, 4 cmd | accept | E +41.0% saved, PRB(rem) -6.1%, 4 cmd | accept |
| 2 | energy_saving | sleep [4, 5] | E +41.1% saved, PRB(rem) -6.9%, 4 cmd | accept | E +42.1% saved, PRB(rem) -11.7%, 4 cmd | accept |
| 3 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -10.3%, 4 cmd | accept | E +40.7% saved, PRB(rem) -4.7%, 4 cmd | accept |
| 4 | energy_saving | sleep [4, 5] | E +41.6% saved, PRB(rem) -9.0%, 4 cmd | accept | E +41.2% saved, PRB(rem) -6.7%, 4 cmd | accept |
| 5 | energy_saving | sleep [5, 4] | E +32.4% saved, PRB(rem) +19.1%, 4 cmd | accept | E +41.4% saved, PRB(rem) -8.8%, 4 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.9 (min -6.6, max -2.9, n=20); dl_throughput_mbps mean -33.9 (min -48.7, max -31.1, n=20); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=17); prb_used_dl_per_cell mean -7.3 (min -9.4, max -0.5, n=41).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 100%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 100%, live 100% of 5 cases.

Runs in which the deployed policy produced RC commands:

- live energy_saving: 5
- twin energy_saving: 5
