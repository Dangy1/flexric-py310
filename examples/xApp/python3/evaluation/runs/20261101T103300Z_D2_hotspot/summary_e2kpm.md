# Twin-vs-live results - `20261101T103300Z_D2_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +22.43 | +41.93 | +23.7% | +48.3% | 26.2 | 39% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | -0.66 | +1.00 | -2.9% | +5.0% | 8.1 | 100% (n=5) | 60% | 60% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -197.01 | -1964.93 | -0.4% | -13.9% | 13.4 | 78% (n=5) | 40% | 40% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +527.24 | +995.33 | +10.2% | +20.2% | 10.6 | 39% (n=5) | 100% | 100% (n=5) |
| qoe_steering | prb_used_dl | 5 | +34.46 | +62.90 | +39.0% | +72.4% | 35.4 | 43% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | -1.03 | +0.23 | -4.8% | +1.2% | 8.2 | 257% (n=5) | 40% | 40% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -198.77 | -1975.80 | -0.8% | -13.9% | 13.6 | 86% (n=5) | 40% | 40% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +808.17 | +1482.75 | +16.3% | +30.1% | 14.6 | 43% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 4 | 0 | 0 | 1 | 100% (5/5) [57, 100] | 100% (4/4) [51, 100] | 100% (4/4) [51, 100] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |
| qoe_steering | 5 | 2 | 1 | 2 | 0 | 40% (2/5) [12, 77] | 67% (2/3) [21, 94] | 50% (2/4) [15, 85] | 0% (0/1) [0, 79] | 80% (4/5) [38, 96] |
| pooled | 10 | 6 | 1 | 2 | 1 | 70% (7/10) [40, 89] | 86% (6/7) [49, 97] | 75% (6/8) [41, 93] | 50% (1/2) [9, 91] | 80% (8/10) [49, 94] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +61.2% cut, thp +3.3% lost, 2 cmd | accept | hot PRB +14.4% cut, thp +1.4% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +61.2% cut, thp +3.3% lost, 2 cmd | accept | hot PRB -15.9% cut, thp -15.2% lost, 2 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +17.8% cut, thp -6.7% lost, 2 cmd | accept | hot PRB +21.2% cut, thp -7.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3,5->3 | hot PRB +39.2% cut, thp -1.1% lost, 3 cmd | accept | hot PRB +38.4% cut, thp +3.5% lost, 3 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +60.2% cut, thp +2.1% lost, 2 cmd | accept | hot PRB +12.8% cut, thp -6.1% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,5->3 | hot PRB +60.9% cut, thp +7.7% lost, 3 cmd | reject | hot PRB +37.8% cut, thp +4.3% lost, 3 cmd | accept |
| 4 | traffic_steering | shed 2->5 | hot PRB +44.0% cut, thp +13.3% lost, 2 cmd | reject | hot PRB -5.6% cut, thp -15.9% lost, 2 cmd | reject |
| 4 | qoe_steering | shed 3->5,2->5 | hot PRB +66.8% cut, thp +11.7% lost, 3 cmd | reject | hot PRB +25.3% cut, thp -1.7% lost, 3 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +56.9% cut, thp +2.9% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +2.3% lost, 2 cmd | accept | hot PRB +55.7% cut, thp +3.3% lost, 2 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
