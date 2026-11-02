# Twin-vs-live results - `20261102T081207Z_D2S_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +27.06 | +35.12 | +30.0% | +40.4% | 13.5 | 33% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.16 | +0.78 | +0.9% | +3.9% | 3.0 | 57% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1368.56 | -1751.13 | -10.4% | -12.3% | 2.0 | 128929% (n=5) | 100% | 100% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +640.90 | +836.34 | +12.8% | +17.0% | 5.4 | 33% (n=5) | 100% | 100% (n=5) |
| qoe_steering | prb_used_dl | 5 | +46.13 | +35.99 | +52.1% | +41.3% | 24.8 | 95% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | -0.50 | -0.77 | -2.2% | -3.9% | 3.5 | 90% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1200.07 | -934.76 | -8.7% | -6.6% | 3.4 | 115% (n=5) | 80% | 80% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +1084.30 | +843.76 | +21.8% | +17.1% | 10.4 | 101% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 4 | 0 | 1 | 0 | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 80% (4/5) [38, 96] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 2 | 0 | 0 | 3 | 100% (5/5) [57, 100] | 100% (2/2) [34, 100] | 100% (2/2) [34, 100] | 100% (3/3) [44, 100] | 40% (2/5) [12, 77] |
| pooled | 10 | 6 | 0 | 1 | 3 | 90% (9/10) [60, 98] | 100% (6/6) [61, 100] | 86% (6/7) [49, 97] | 100% (3/3) [44, 100] | 70% (7/10) [40, 89] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +23.8% cut, thp -1.1% lost, 2 cmd | accept | hot PRB +14.4% cut, thp -1.1% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +17.6% cut, thp -6.3% lost, 2 cmd | accept | hot PRB +17.2% cut, thp -1.6% lost, 2 cmd | accept |
| 2 | traffic_steering | shed 2->3 | hot PRB +15.4% cut, thp -5.8% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +19.9% cut, thp -6.3% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +19.9% cut, thp -6.9% lost, 2 cmd | accept | hot PRB +18.5% cut, thp -8.1% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,4->3 | hot PRB +36.9% cut, thp +6.3% lost, 3 cmd | reject | hot PRB +26.5% cut, thp +14.6% lost, 3 cmd | reject |
| 4 | traffic_steering | shed 2->3 | hot PRB +14.3% cut, thp +1.6% lost, 2 cmd | accept | hot PRB +14.0% cut, thp -6.6% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3,5->3 | hot PRB +25.6% cut, thp +9.3% lost, 3 cmd | reject | hot PRB +25.8% cut, thp +6.0% lost, 3 cmd | reject |
| 5 | traffic_steering | shed 2->3 | hot PRB +54.3% cut, thp +7.8% lost, 2 cmd | reject | hot PRB +57.1% cut, thp +3.6% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3,4->3 | hot PRB +59.7% cut, thp +7.8% lost, 3 cmd | reject | hot PRB +56.8% cut, thp +7.7% lost, 3 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
