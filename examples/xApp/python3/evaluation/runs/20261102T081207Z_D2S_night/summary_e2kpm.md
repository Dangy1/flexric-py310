# Twin-vs-live results - `20261102T081207Z_D2S_night`

Runs: 20 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 5 | -19.12 | -18.95 | -23.6% | -23.5% | 2.0 | 12% (n=4) | 100% | 100% (n=4) |
| energy_saving | dl_throughput_mbps | 5 | -3.33 | -3.43 | -17.3% | -17.6% | 1.2 | 9% (n=4) | 100% | 100% (n=4) |
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
| 2 | energy_saving | sleep [4, 5] | E +41.1% saved, PRB(rem) -7.3%, 4 cmd | accept | E +42.1% saved, PRB(rem) -12.4%, 4 cmd | accept |
| 3 | energy_saving | sleep [4, 5] | E +41.8% saved, PRB(rem) -11.2%, 4 cmd | accept | E +40.7% saved, PRB(rem) -5.2%, 4 cmd | accept |
| 4 | energy_saving | sleep [4, 5] | E +41.6% saved, PRB(rem) -9.7%, 4 cmd | accept | E +41.1% saved, PRB(rem) -7.1%, 4 cmd | accept |
| 5 | energy_saving | sleep [4, 5] | E +41.4% saved, PRB(rem) -8.8%, 4 cmd | accept | E +41.8% saved, PRB(rem) -11.0%, 4 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 4
- twin energy_saving: 4
