# Twin-vs-live results - `20261102T081207Z_D2S_age0.5_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.78 | +32.01 | +28.7% | +36.8% | 10.1 | 39% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.37 | +0.49 | +1.9% | +2.5% | 1.8 | 36% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1265.49 | -1417.69 | -8.9% | -10.0% | 1.1 | 151% (n=5) | 80% | 80% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +588.46 | +760.30 | +12.0% | +15.4% | 4.2 | 39% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +43.90 | +47.68 | +48.4% | +54.8% | 19.9 | 30% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | +0.18 | +0.33 | +1.2% | +1.6% | 2.9 | 114% (n=5) | 80% | 80% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1551.76 | -1630.03 | -10.7% | -11.5% | 3.8 | 752% (n=5) | 100% | 100% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +1036.36 | +1126.87 | +20.6% | +22.9% | 8.1 | 31% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 2 | 0 | 1 | 2 | 80% (4/5) [38, 96] | 100% (2/2) [34, 100] | 67% (2/3) [21, 94] | 100% (2/2) [34, 100] | 60% (3/5) [23, 88] |
| pooled | 10 | 7 | 0 | 1 | 2 | 90% (9/10) [60, 98] | 100% (7/7) [65, 100] | 88% (7/8) [53, 98] | 100% (2/2) [34, 100] | 80% (8/10) [49, 94] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.5% cut, thp -1.0% lost, 2 cmd | accept | hot PRB +17.0% cut, thp -5.9% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB -11.9% cut, thp -16.1% lost, 2 cmd | reject | hot PRB -12.7% cut, thp -11.0% lost, 2 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +19.9% cut, thp -6.3% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +15.4% cut, thp -5.8% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +16.3% cut, thp -6.2% lost, 2 cmd | accept | hot PRB +5.2% cut, thp -5.3% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,5->3 | hot PRB +34.5% cut, thp +5.3% lost, 3 cmd | reject | hot PRB +29.9% cut, thp -1.4% lost, 3 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +49.0% cut, thp +1.6% lost, 2 cmd | accept | hot PRB +59.8% cut, thp +3.2% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 5->3,2->3 | hot PRB +49.1% cut, thp +8.2% lost, 3 cmd | reject | hot PRB +59.7% cut, thp +8.6% lost, 3 cmd | reject |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +59.8% cut, thp +3.0% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +59.8% cut, thp +3.0% lost, 2 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
