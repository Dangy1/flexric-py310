# Twin-vs-live results - `20261101T103300Z_D2_night`

Runs: 20 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 5 | -20.59 | -6.49 | -25.3% | -8.4% | 18.1 | 33% (n=5) | 80% | 80% (n=5) |
| energy_saving | dl_throughput_mbps | 5 | -4.52 | -4.06 | -23.4% | -20.9% | 4.6 | 28% (n=5) | 100% | 100% (n=5) |
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
| 1 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -10.4%, 4 cmd | accept | E +41.0% saved, PRB(rem) -6.1%, 4 cmd | accept |
| 2 | energy_saving | sleep [4, 5] | E +41.1% saved, PRB(rem) -7.3%, 4 cmd | accept | E +42.1% saved, PRB(rem) -12.3%, 4 cmd | accept |
| 3 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -11.2%, 4 cmd | accept | E +40.7% saved, PRB(rem) -5.2%, 4 cmd | accept |
| 4 | energy_saving | sleep [4, 5] | E +41.6% saved, PRB(rem) -9.7%, 4 cmd | accept | E +41.2% saved, PRB(rem) -7.2%, 4 cmd | accept |
| 5 | energy_saving | sleep [5, 4] | E +32.4% saved, PRB(rem) +18.8%, 4 cmd | accept | E +41.4% saved, PRB(rem) -9.5%, 4 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 5
- twin energy_saving: 5
