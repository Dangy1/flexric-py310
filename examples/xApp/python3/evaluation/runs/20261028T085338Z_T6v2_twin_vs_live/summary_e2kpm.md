# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | +4.27 | +0.51 | +13.9% | +0.3% | 16.5 | 3107% (n=9) | 11% | 0% (n=2) |
| energy_saving | dl_throughput_mbps | 9 | -0.07 | -0.57 | -0.3% | -2.9% | 2.6 | 6912% (n=9) | 22% | 100% (n=2) |
| energy_saving | dl_buffer_kbytes | 9 | +161.96 | +222.84 | +895329.6% | +440.1% | 894896.8 | 167% (n=8) | 33% | 100% (n=2) |
| energy_saving | energy_j_per_s | 9 | -289.22 | -216.37 | -5.2% | -3.5% | 1.7 | 31% (n=2) | 100% | 100% (n=2) |
| traffic_steering | prb_used_dl | 9 | +32.81 | -7.50 | +79.9% | -4.4% | 88.1 | 399% (n=9) | 44% | 44% (n=9) |
| traffic_steering | dl_throughput_mbps | 9 | -0.86 | -1.03 | -6.2% | -5.8% | 8.8 | 893% (n=9) | 56% | 56% (n=9) |
| traffic_steering | dl_buffer_kbytes | 9 | +183.91 | +677.54 | +111218.3% | +55213.6% | 82657.8 | 3335% (n=9) | 44% | 44% (n=9) |
| traffic_steering | energy_j_per_s | 9 | +702.75 | -175.66 | +13.2% | -2.5% | 15.8 | 324% (n=9) | 56% | 56% (n=9) |
| qoe_steering | prb_used_dl | 9 | +6.06 | -9.71 | +22.9% | -6.9% | 41.6 | 1399% (n=9) | 78% | 75% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -0.83 | -0.53 | -5.3% | -3.3% | 7.3 | 187% (n=9) | 67% | 62% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +472.03 | +426.27 | +932980.8% | +4812.0% | 937506.4 | 284133% (n=9) | 56% | 62% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +291.36 | -222.68 | +5.4% | -3.6% | 12.5 | 487% (n=9) | 56% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 1 | 0 | 0 | 8 | 100% (9/9) [70, 100] | 100% (1/1) [21, 100] | 100% (1/1) [21, 100] | 100% (8/8) [68, 100] | 11% (1/9) [2, 43] |
| traffic_steering | 9 | 1 | 3 | 2 | 3 | 44% (4/9) [19, 73] | 25% (1/4) [5, 70] | 33% (1/3) [6, 79] | 50% (3/6) [19, 81] | 33% (3/9) [12, 65] |
| qoe_steering | 9 | 1 | 2 | 5 | 1 | 22% (2/9) [6, 55] | 33% (1/3) [6, 79] | 17% (1/6) [3, 56] | 33% (1/3) [6, 79] | 67% (6/9) [35, 88] |
| pooled | 27 | 3 | 5 | 7 | 12 | 56% (15/27) [37, 72] | 38% (3/8) [14, 69] | 30% (3/10) [11, 60] | 71% (12/17) [47, 87] | 37% (10/27) [22, 56] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [5, 3] | E +34.1% saved, PRB(rem) +37.2%, 4 cmd | reject | E +18.6% saved, PRB(rem) +99.0%, 6 cmd | reject |
| 1 | traffic_steering | shed 2->3 | hot PRB -22.8% cut, thp +6.4% lost, 1 cmd | reject | hot PRB +16.8% cut, thp +8.4% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 2->5,3->5 | hot PRB +62.7% cut, thp +13.0% lost, 2 cmd | reject | hot PRB +32.0% cut, thp +3.9% lost, 2 cmd | accept |
| 2 | energy_saving | sleep [3] | E +13.1% saved, PRB(rem) +2.3%, 2 cmd | accept | E +13.3% saved, PRB(rem) +0.1%, 1 cmd | accept |
| 2 | traffic_steering | shed 5->3 | hot PRB +34.0% cut, thp -1.9% lost, 1 cmd | accept | hot PRB +64.0% cut, thp +2.1% lost, 1 cmd | accept |
| 2 | qoe_steering | shed 5->3,4->3 | hot PRB +53.1% cut, thp +4.8% lost, 2 cmd | accept | hot PRB +60.3% cut, thp +6.7% lost, 1 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->5 | hot PRB +49.8% cut, thp +30.4% lost, 2 cmd | reject | hot PRB +10.8% cut, thp +7.2% lost, 2 cmd | reject |
| 3 | qoe_steering | shed 5->None | hot PRB +3.9% cut, thp +4.6% lost, 0 cmd | reject | hot PRB +72.8% cut, thp +1.6% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +38.9% cut, thp +12.4% lost, 2 cmd | reject | hot PRB +15.6% cut, thp +0.5% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +57.2% cut, thp +5.8% lost, 2 cmd | reject | hot PRB +16.9% cut, thp +2.1% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.7%, 0 cmd | reject |
| 5 | traffic_steering | shed 3->2 | hot PRB +59.2% cut, thp -3.3% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +10.5% lost, 1 cmd | reject |
| 5 | qoe_steering | shed 5->2,3->2 | hot PRB +65.4% cut, thp -5.3% lost, 2 cmd | accept | hot PRB +33.6% cut, thp +14.7% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->3 | hot PRB +44.7% cut, thp -0.5% lost, 2 cmd | accept | hot PRB +21.9% cut, thp +7.1% lost, 1 cmd | reject |
| 6 | qoe_steering | shed 3->None | hot PRB +53.0% cut, thp +10.3% lost, 1 cmd | reject | hot PRB +49.9% cut, thp -2.9% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->3 | hot PRB +54.7% cut, thp +11.5% lost, 2 cmd | reject | hot PRB +29.1% cut, thp +5.1% lost, 1 cmd | reject |
| 7 | qoe_steering | shed 2->3 | hot PRB +53.7% cut, thp +9.5% lost, 2 cmd | reject | hot PRB +28.6% cut, thp -1.4% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 8 | traffic_steering | shed 3->4 | hot PRB +36.9% cut, thp +4.8% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +11.2% lost, 1 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +74.1% cut, thp +6.3% lost, 1 cmd | reject | hot PRB +100.0% cut, thp +8.2% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +135.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->3 | hot PRB -1039.2% cut, thp -3.8% lost, 2 cmd | reject | hot PRB +19.7% cut, thp +0.1% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->None | hot PRB +100.0% cut, thp -1.4% lost, 1 cmd | accept | hot PRB +25.3% cut, thp -3.6% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 2
- live qoe_steering: 9
- live traffic_steering: 9
- twin energy_saving: 2
- twin qoe_steering: 8
- twin traffic_steering: 9
