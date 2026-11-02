# Twin-vs-live results - `20261102T081207Z_D2S_age1.5_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.51 | +34.94 | +28.3% | +40.2% | 16.1 | 36% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.27 | +0.92 | +1.5% | +4.6% | 3.8 | 67% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1308.17 | -1876.98 | -9.4% | -13.2% | 3.9 | 59% (n=5) | 100% | 100% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +579.79 | +830.20 | +11.8% | +16.8% | 6.8 | 36% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +29.41 | +42.53 | +34.5% | +48.9% | 16.8 | 37% (n=5) | 80% | 80% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | -0.34 | +0.86 | -1.4% | +4.3% | 6.0 | 117% (n=5) | 60% | 60% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1080.13 | -1866.26 | -7.5% | -13.2% | 5.6 | 131% (n=5) | 80% | 80% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +690.97 | +1007.58 | +14.2% | +20.5% | 7.4 | 37% (n=5) | 80% | 80% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 3 | 0 | 2 | 0 | 60% (3/5) [23, 88] | 100% (3/3) [44, 100] | 60% (3/5) [23, 88] | -- (0/0) | 100% (5/5) [57, 100] |
| pooled | 10 | 8 | 0 | 2 | 0 | 80% (8/10) [49, 94] | 100% (8/8) [68, 100] | 80% (8/10) [49, 94] | -- (0/0) | 100% (10/10) [72, 100] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.5% cut, thp -1.0% lost, 2 cmd | accept | hot PRB +17.0% cut, thp -5.9% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +21.5% cut, thp -1.0% lost, 2 cmd | accept | hot PRB +11.4% cut, thp -5.7% lost, 2 cmd | accept |
| 2 | traffic_steering | shed 2->3 | hot PRB +17.8% cut, thp -6.7% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -6.3% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3,5->3 | hot PRB +36.3% cut, thp +5.3% lost, 3 cmd | reject | hot PRB +36.8% cut, thp -4.4% lost, 3 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +19.7% cut, thp -7.0% lost, 2 cmd | accept | hot PRB +19.7% cut, thp -8.5% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3 | hot PRB +19.7% cut, thp -7.0% lost, 2 cmd | accept | hot PRB +19.7% cut, thp -8.5% lost, 2 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +21.0% cut, thp +4.8% lost, 2 cmd | accept | hot PRB +19.9% cut, thp -6.1% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3 | hot PRB +18.5% cut, thp +7.4% lost, 2 cmd | reject | hot PRB +19.9% cut, thp -6.1% lost, 2 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +60.7% cut, thp +3.7% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +59.8% cut, thp +3.0% lost, 2 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
