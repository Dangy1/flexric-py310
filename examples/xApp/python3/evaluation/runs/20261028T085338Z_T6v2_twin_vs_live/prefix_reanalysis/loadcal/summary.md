# Twin-vs-live results - `loadcal`

Runs: 72 (4 failed). Pairs analysed: [1, 2, 4, 5, 6, 7, 8, 9]; excluded: [3].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +0.19 | -15.54 | +0.2% | -7.7% | 10.0 | 98% (n=8) | 38% | 20% (n=5) |
| energy_saving | dl_throughput_mbps | 8 | +0.00 | -2.02 | +0.0% | -6.1% | 6.1 | 100% (n=5) | 38% | 0% (n=5) |
| energy_saving | dl_delay_ms | 8 | +0.00 | +7.93 | +0.0% | +171.0% | 194.3 | 100% (n=5) | 38% | 0% (n=5) |
| energy_saving | dl_buffer_kbytes | 8 | +0.00 | +719.34 | +0.0% | +71224.8% | 71224.8 | 100% (n=5) | 38% | 0% (n=5) |
| energy_saving | energy_j_per_s | 8 | -582.52 | -1005.49 | -11.9% | -13.9% | 4.1 | 37% (n=5) | 100% | 100% (n=5) |
| traffic_steering | prb_used_dl | 8 | +35.96 | +20.78 | +35.2% | +10.9% | 34.0 | 560% (n=8) | 75% | 75% (n=8) |
| traffic_steering | dl_throughput_mbps | 8 | -1.60 | -2.63 | -5.2% | -8.0% | 13.3 | 410% (n=8) | 62% | 62% (n=8) |
| traffic_steering | dl_delay_ms | 8 | +47.90 | +10.08 | +1162.6% | +222.0% | 1073.4 | 1076% (n=8) | 88% | 88% (n=8) |
| traffic_steering | dl_buffer_kbytes | 8 | +282.99 | +521.79 | +35195.6% | +158790.9% | 193945.1 | 444911% (n=8) | 50% | 50% (n=8) |
| traffic_steering | energy_j_per_s | 8 | +810.66 | +481.41 | +15.2% | +6.7% | 14.5 | 394% (n=8) | 88% | 88% (n=8) |
| qoe_steering | prb_used_dl | 8 | +24.56 | +3.81 | +21.5% | +3.1% | 29.0 | 215% (n=8) | 50% | 75% (n=4) |
| qoe_steering | dl_throughput_mbps | 8 | -1.64 | -2.34 | -4.3% | -6.8% | 14.1 | 240% (n=7) | 38% | 75% (n=4) |
| qoe_steering | dl_delay_ms | 8 | +13.23 | +0.04 | +668.1% | +1.7% | 668.0 | 1639% (n=7) | 38% | 75% (n=4) |
| qoe_steering | dl_buffer_kbytes | 8 | -132.19 | +774.26 | +29562.7% | +177526.6% | 206677.9 | 5015% (n=7) | 12% | 25% (n=4) |
| qoe_steering | energy_j_per_s | 8 | +611.47 | +67.00 | +11.1% | +1.4% | 15.6 | 652% (n=7) | 25% | 50% (n=4) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 3 | 2 | 0 | 3 | 75% (6/8) [41, 93] | 60% (3/5) [23, 88] | 100% (3/3) [44, 100] | 60% (3/5) [23, 88] | 38% (3/8) [14, 69] |
| traffic_steering | 8 | 0 | 4 | 2 | 2 | 25% (2/8) [7, 59] | 0% (0/4) [0, 49] | 0% (0/2) [0, 66] | 33% (2/6) [10, 70] | 25% (2/8) [7, 59] |
| qoe_steering | 8 | 0 | 1 | 4 | 3 | 38% (3/8) [14, 69] | 0% (0/1) [0, 79] | 0% (0/4) [0, 49] | 75% (3/4) [30, 95] | 50% (4/8) [22, 78] |
| pooled | 24 | 3 | 7 | 6 | 8 | 46% (11/24) [28, 65] | 30% (3/10) [11, 60] | 33% (3/9) [12, 65] | 53% (8/15) [30, 75] | 38% (9/24) [21, 57] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +1.8%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.5%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +19.0% cut, thp +17.4% lost, 2 cmd | reject | hot PRB +14.6% cut, thp -0.9% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->4,5->4 | hot PRB +44.0% cut, thp +20.7% lost, 3 cmd | reject | hot PRB +31.2% cut, thp +1.6% lost, 2 cmd | accept |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.5%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +52.8% cut, thp +18.7% lost, 2 cmd | reject | hot PRB +41.6% cut, thp +8.7% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->5,3->5 | hot PRB +69.7% cut, thp +21.7% lost, 2 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 4 | energy_saving | sleep [4] | E +11.6% saved, PRB(rem) -0.1%, 1 cmd | accept | E +7.1% saved, PRB(rem) +33.2%, 3 cmd | reject |
| 4 | traffic_steering | shed 2->4 | hot PRB +7.1% cut, thp -7.6% lost, 2 cmd | accept | hot PRB +13.8% cut, thp +6.6% lost, 1 cmd | reject |
| 4 | qoe_steering | shed 4->None,2->None | hot PRB +17.5% cut, thp +7.4% lost, 2 cmd | reject | hot PRB +35.9% cut, thp +2.5% lost, 2 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.7%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.7%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +19.0% cut, thp +2.3% lost, 1 cmd | accept | hot PRB +23.7% cut, thp +8.2% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 2->4,3->4 | hot PRB +27.2% cut, thp +3.4% lost, 2 cmd | accept | hot PRB +39.6% cut, thp +22.2% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [5, 4] | E +25.7% saved, PRB(rem) +0.5%, 2 cmd | accept | E +44.8% saved, PRB(rem) +10.0%, 5 cmd | accept |
| 6 | traffic_steering | shed 2->5 | hot PRB +26.8% cut, thp +15.6% lost, 2 cmd | reject | hot PRB +7.7% cut, thp +1.7% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 4->None,5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +83.5% cut, thp +6.7% lost, 2 cmd | reject |
| 7 | energy_saving | sleep [5, 3, 2] | E +34.5% saved, PRB(rem) +0.0%, 2 cmd | accept | E +30.7% saved, PRB(rem) +26.9%, 5 cmd | accept |
| 7 | traffic_steering | shed 4->5 | hot PRB +100.0% cut, thp +5.0% lost, 1 cmd | reject | hot PRB +35.5% cut, thp +11.3% lost, 1 cmd | reject |
| 7 | qoe_steering | shed 3->None,5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +52.1% cut, thp -0.7% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [5] | E +9.5% saved, PRB(rem) -1.0%, 1 cmd | accept | E +13.1% saved, PRB(rem) +42.7%, 3 cmd | reject |
| 8 | traffic_steering | shed 2->5 | hot PRB +13.6% cut, thp -10.8% lost, 2 cmd | accept | hot PRB +29.8% cut, thp +9.8% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +52.3% cut, thp +2.5% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [4] | E +13.5% saved, PRB(rem) +0.0%, 1 cmd | accept | E +15.2% saved, PRB(rem) +15.6%, 3 cmd | accept |
| 9 | traffic_steering | shed 3->4 | hot PRB +100.0% cut, thp +1.1% lost, 1 cmd | accept | hot PRB +22.9% cut, thp +18.6% lost, 1 cmd | reject |
| 9 | qoe_steering | shed 4->None,2->None | hot PRB -1.7% cut, thp -18.7% lost, 2 cmd | reject | hot PRB +43.1% cut, thp +19.2% lost, 2 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 6
- live qoe_steering: 8
- live traffic_steering: 9
- twin energy_saving: 5
- twin qoe_steering: 5
- twin traffic_steering: 8

Failed runs:

- twin s3 energy_saving: None
- twin s3 noop: None
- twin s3 qoe_steering: None
- twin s3 traffic_steering: None
