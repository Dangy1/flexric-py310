# Twin-vs-live results - `base`

Runs: 64 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +11.53 | -31.14 | +34.7% | -17.1% | 60.6 | 38712% (n=8) | 25% | 14% (n=7) |
| energy_saving | dl_throughput_mbps | 8 | -0.33 | -2.95 | -2.2% | -15.7% | 13.5 | 112691% (n=8) | 50% | 57% (n=7) |
| energy_saving | dl_buffer_kbytes | 8 | +109.11 | +1927.60 | +73.5% | +258574.2% | 258500.8 | 95% (n=8) | 50% | 57% (n=7) |
| energy_saving | energy_j_per_s | 8 | -1160.47 | -1833.16 | -21.4% | -25.7% | 10.5 | 40% (n=7) | 88% | 100% (n=7) |
| traffic_steering | prb_used_dl | 8 | +41.22 | +14.49 | +95.1% | +10.7% | 84.4 | 349% (n=8) | 88% | 100% (n=7) |
| traffic_steering | dl_throughput_mbps | 8 | -0.68 | -0.59 | -4.5% | -3.2% | 8.5 | 253% (n=8) | 62% | 71% (n=7) |
| traffic_steering | dl_buffer_kbytes | 8 | +189.66 | +93.10 | +15376.7% | +3215.3% | 18278.1 | 67404% (n=8) | 75% | 86% (n=7) |
| traffic_steering | energy_j_per_s | 8 | +892.72 | +446.81 | +16.6% | +7.5% | 15.5 | 672% (n=8) | 88% | 100% (n=7) |
| qoe_steering | prb_used_dl | 8 | +13.56 | -26.36 | +34.4% | -14.0% | 49.3 | 144% (n=8) | 38% | 40% (n=5) |
| qoe_steering | dl_throughput_mbps | 8 | +0.00 | -1.56 | +0.4% | -8.3% | 10.4 | 94% (n=8) | 62% | 60% (n=5) |
| qoe_steering | dl_buffer_kbytes | 8 | -116.08 | +602.45 | +558505.8% | +51838.7% | 583644.0 | 104% (n=8) | 25% | 40% (n=5) |
| qoe_steering | energy_j_per_s | 8 | +163.08 | -631.73 | +3.2% | -8.7% | 13.5 | 134% (n=8) | 12% | 20% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 3 | 2 | 1 | 2 | 62% (5/8) [31, 86] | 60% (3/5) [23, 88] | 75% (3/4) [30, 95] | 50% (2/4) [15, 85] | 50% (4/8) [22, 78] |
| traffic_steering | 8 | 0 | 2 | 4 | 2 | 25% (2/8) [7, 59] | 0% (0/2) [0, 66] | 0% (0/4) [0, 49] | 50% (2/4) [15, 85] | 50% (4/8) [22, 78] |
| qoe_steering | 8 | 1 | 2 | 0 | 5 | 75% (6/8) [41, 93] | 33% (1/3) [6, 79] | 100% (1/1) [21, 100] | 71% (5/7) [36, 92] | 12% (1/8) [2, 47] |
| pooled | 24 | 4 | 6 | 5 | 9 | 54% (13/24) [35, 72] | 40% (4/10) [17, 69] | 44% (4/9) [19, 73] | 60% (9/15) [36, 80] | 38% (9/24) [21, 57] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [3] | E +14.0% saved, PRB(rem) +35.0%, 2 cmd | reject | E +31.5% saved, PRB(rem) +7.3%, 4 cmd | accept |
| 1 | traffic_steering | shed 2->3 | hot PRB -0.9% cut, thp +3.2% lost, 1 cmd | reject | hot PRB +14.3% cut, thp +13.0% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 4->3,5->3 | hot PRB +100.0% cut, thp +15.5% lost, 2 cmd | reject | hot PRB +59.4% cut, thp +15.6% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E -0.2% saved, PRB(rem) +78.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 5->3 | hot PRB +15.4% cut, thp -8.4% lost, 1 cmd | accept | hot PRB +1.6% cut, thp -10.7% lost, 1 cmd | reject |
| 2 | qoe_steering | shed 4->2,5->2 | hot PRB +14.5% cut, thp -5.3% lost, 2 cmd | accept | hot PRB +0.5% cut, thp -11.8% lost, 1 cmd | reject |
| 3 | energy_saving | sleep [4, 3] | E +21.8% saved, PRB(rem) +0.0%, 2 cmd | accept | E +30.5% saved, PRB(rem) -6.0%, 3 cmd | accept |
| 3 | traffic_steering | shed 5->4 | hot PRB +0.0% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +75.0% cut, thp +0.8% lost, 1 cmd | accept |
| 3 | qoe_steering | shed 4->None,3->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +100.0% cut, thp +10.4% lost, 1 cmd | reject |
| 4 | energy_saving | sleep [4, 3, 5] | E +30.1% saved, PRB(rem) +214.8%, 2 cmd | reject | E +24.7% saved, PRB(rem) +52.4%, 6 cmd | reject |
| 4 | traffic_steering | shed 2->4 | hot PRB -143.6% cut, thp +13.6% lost, 2 cmd | reject | hot PRB +13.8% cut, thp +1.4% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 4->5,3->5 | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +46.6% cut, thp +16.7% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [4, 2] | E +42.1% saved, PRB(rem) -31.7%, 6 cmd | accept | E +22.5% saved, PRB(rem) +107.3%, 9 cmd | reject |
| 5 | traffic_steering | shed 3->4 | hot PRB +53.1% cut, thp -1.4% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +6.7% lost, 1 cmd | reject |
| 5 | qoe_steering | shed 4->None | hot PRB --% cut, thp -14.6% lost, 1 cmd | reject | hot PRB +100.0% cut, thp +9.5% lost, 1 cmd | reject |
| 6 | energy_saving | sleep [5, 4] | E +23.7% saved, PRB(rem) -0.3%, 2 cmd | accept | E +43.8% saved, PRB(rem) +9.7%, 5 cmd | accept |
| 6 | traffic_steering | shed 2->5 | hot PRB +45.6% cut, thp +14.0% lost, 2 cmd | reject | hot PRB +13.3% cut, thp +1.4% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 4->None,5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +84.0% cut, thp +8.1% lost, 2 cmd | reject |
| 7 | energy_saving | sleep [5, 4, 3] | E +28.6% saved, PRB(rem) +22.5%, 3 cmd | accept | E +39.9% saved, PRB(rem) +14.4%, 7 cmd | accept |
| 7 | traffic_steering | shed 2->5 | hot PRB +26.2% cut, thp +9.5% lost, 2 cmd | reject | hot PRB +52.4% cut, thp -2.8% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 5->None,2->None | hot PRB +68.4% cut, thp +3.7% lost, 2 cmd | accept | hot PRB +68.5% cut, thp +4.8% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [5] | E +11.1% saved, PRB(rem) +0.0%, 1 cmd | accept | E +12.6% saved, PRB(rem) +43.6%, 3 cmd | reject |
| 8 | traffic_steering | shed 2->5 | hot PRB -22.6% cut, thp +5.7% lost, 1 cmd | reject | hot PRB +28.3% cut, thp +15.8% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 5->None,3->None | hot PRB +45.7% cut, thp -2.6% lost, 1 cmd | accept | hot PRB +70.4% cut, thp +13.3% lost, 2 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 7
- live qoe_steering: 8
- live traffic_steering: 8
- twin energy_saving: 7
- twin qoe_steering: 5
- twin traffic_steering: 7
