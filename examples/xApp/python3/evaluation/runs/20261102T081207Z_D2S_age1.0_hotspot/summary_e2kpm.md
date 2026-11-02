# Twin-vs-live results - `20261102T081207Z_D2S_age1.0_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.58 | +29.59 | +28.3% | +34.0% | 9.9 | 39% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.37 | +0.61 | +1.9% | +3.1% | 1.6 | 27% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1265.60 | -1417.77 | -8.9% | -10.0% | 1.1 | 309% (n=5) | 80% | 80% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +583.21 | +703.45 | +11.9% | +14.3% | 4.1 | 39% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +29.00 | +30.08 | +33.7% | +34.4% | 8.3 | 41% (n=4) | 80% | 75% (n=4) |
| qoe_steering | dl_throughput_mbps | 5 | +0.17 | +0.12 | +0.9% | +0.6% | 0.9 | 19% (n=4) | 100% | 100% (n=4) |
| qoe_steering | dl_buffer_kbytes | 5 | -938.82 | -940.02 | -6.6% | -6.6% | 0.0 | 135% (n=4) | 80% | 75% (n=4) |
| qoe_steering | energy_j_per_s | 5 | +684.42 | +710.90 | +14.0% | +14.4% | 3.5 | 42% (n=4) | 80% | 75% (n=4) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 3 | 0 | 0 | 2 | 100% (5/5) [57, 100] | 100% (3/3) [44, 100] | 100% (3/3) [44, 100] | 100% (2/2) [34, 100] | 60% (3/5) [23, 88] |
| pooled | 10 | 8 | 0 | 0 | 2 | 100% (10/10) [72, 100] | 100% (8/8) [68, 100] | 100% (8/8) [68, 100] | 100% (2/2) [34, 100] | 80% (8/10) [49, 94] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.5% cut, thp -1.0% lost, 2 cmd | accept | hot PRB +11.4% cut, thp -5.7% lost, 2 cmd | accept |
| 1 | qoe_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +17.8% cut, thp -6.7% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +17.8% cut, thp -6.7% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -6.3% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +19.7% cut, thp -7.0% lost, 2 cmd | accept | hot PRB +19.7% cut, thp -8.5% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3 | hot PRB +19.7% cut, thp -7.0% lost, 2 cmd | accept | hot PRB +19.7% cut, thp -8.5% lost, 2 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +48.4% cut, thp +2.8% lost, 2 cmd | accept | hot PRB +59.8% cut, thp +3.2% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3 | hot PRB +49.0% cut, thp +1.6% lost, 2 cmd | accept | hot PRB +58.4% cut, thp +3.1% lost, 2 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +60.2% cut, thp +3.1% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3,4->3 | hot PRB +58.5% cut, thp +7.7% lost, 3 cmd | reject | hot PRB +59.6% cut, thp +8.7% lost, 3 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 4
- live traffic_steering: 5
- twin qoe_steering: 4
- twin traffic_steering: 5
