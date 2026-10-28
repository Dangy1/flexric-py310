# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | -2.64 | +0.59 | -2.3% | +0.3% | 2.7 | 2178% (n=9) | 22% | 50% (n=2) |
| energy_saving | dl_throughput_mbps | 9 | -0.41 | -0.61 | -1.4% | -1.8% | 0.4 | 33% (n=1) | 89% | 50% (n=2) |
| energy_saving | dl_delay_ms | 9 | +0.04 | +0.95 | +1.5% | +20.5% | 20.3 | 99% (n=1) | 89% | 50% (n=2) |
| energy_saving | dl_buffer_kbytes | 9 | +165.94 | +224.64 | +593789.6% | +449.5% | 593340.1 | 26% (n=1) | 89% | 50% (n=2) |
| energy_saving | energy_j_per_s | 9 | -289.22 | -216.37 | -5.2% | -3.5% | 1.7 | 31% (n=2) | 100% | 100% (n=2) |
| traffic_steering | prb_used_dl | 9 | +29.82 | -7.02 | +27.9% | -4.1% | 32.0 | 322% (n=9) | 56% | 56% (n=9) |
| traffic_steering | dl_throughput_mbps | 9 | -1.63 | -2.21 | -6.4% | -6.7% | 8.5 | 197% (n=9) | 67% | 67% (n=9) |
| traffic_steering | dl_delay_ms | 9 | +30.57 | +8.42 | +2256.9% | +195.5% | 2241.0 | 6191% (n=9) | 67% | 67% (n=9) |
| traffic_steering | dl_buffer_kbytes | 9 | +191.72 | +685.05 | +100053.6% | +51645.6% | 104850.0 | 8441% (n=9) | 67% | 67% (n=9) |
| traffic_steering | energy_j_per_s | 9 | +702.75 | -175.66 | +13.2% | -2.5% | 15.8 | 324% (n=9) | 56% | 56% (n=9) |
| qoe_steering | prb_used_dl | 9 | +12.55 | -9.09 | +11.2% | -6.6% | 26.1 | 1090% (n=9) | 56% | 62% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -1.90 | -0.92 | -6.6% | -3.2% | 7.7 | 823% (n=9) | 67% | 75% (n=8) |
| qoe_steering | dl_delay_ms | 9 | +9.14 | -0.44 | +551.5% | -11.5% | 575.8 | 1755% (n=9) | 67% | 75% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +483.71 | +429.48 | +766936.2% | +10065.8% | 776858.7 | 23791% (n=9) | 67% | 75% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +291.36 | -222.68 | +5.4% | -3.6% | 12.5 | 487% (n=9) | 56% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 1 | 1 | 0 | 7 | 89% (8/9) [57, 98] | 50% (1/2) [9, 91] | 100% (1/1) [21, 100] | 88% (7/8) [53, 98] | 11% (1/9) [2, 43] |
| traffic_steering | 9 | 2 | 3 | 1 | 3 | 56% (5/9) [27, 81] | 40% (2/5) [12, 77] | 67% (2/3) [21, 94] | 50% (3/6) [19, 81] | 33% (3/9) [12, 65] |
| qoe_steering | 9 | 1 | 2 | 5 | 1 | 22% (2/9) [6, 55] | 33% (1/3) [6, 79] | 17% (1/6) [3, 56] | 33% (1/3) [6, 79] | 67% (6/9) [35, 88] |
| pooled | 27 | 4 | 6 | 6 | 11 | 56% (15/27) [37, 72] | 40% (4/10) [17, 69] | 40% (4/10) [17, 69] | 65% (11/17) [41, 83] | 37% (10/27) [22, 56] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [5, 3] | E +34.1% saved, PRB(rem) +18.1%, 4 cmd | accept | E +18.6% saved, PRB(rem) +98.9%, 6 cmd | reject |
| 1 | traffic_steering | shed 2->3 | hot PRB +9.5% cut, thp +7.0% lost, 1 cmd | reject | hot PRB +16.2% cut, thp +10.1% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 2->5,3->5 | hot PRB +35.1% cut, thp +17.3% lost, 2 cmd | reject | hot PRB +31.6% cut, thp +0.3% lost, 2 cmd | accept |
| 2 | energy_saving | sleep [3] | E +13.1% saved, PRB(rem) +6.7%, 2 cmd | accept | E +13.3% saved, PRB(rem) -0.0%, 1 cmd | accept |
| 2 | traffic_steering | shed 5->3 | hot PRB +47.8% cut, thp +3.0% lost, 1 cmd | accept | hot PRB +64.1% cut, thp -1.5% lost, 1 cmd | accept |
| 2 | qoe_steering | shed 5->3,4->3 | hot PRB +51.0% cut, thp +10.2% lost, 2 cmd | reject | hot PRB +60.8% cut, thp +12.5% lost, 1 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->5 | hot PRB +16.3% cut, thp +21.3% lost, 2 cmd | reject | hot PRB +11.2% cut, thp +8.4% lost, 2 cmd | reject |
| 3 | qoe_steering | shed 5->None | hot PRB -0.0% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +72.6% cut, thp -1.8% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +39.7% cut, thp +14.1% lost, 2 cmd | reject | hot PRB +15.5% cut, thp +1.1% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +39.4% cut, thp +5.1% lost, 2 cmd | reject | hot PRB +16.6% cut, thp +0.9% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.4%, 0 cmd | reject |
| 5 | traffic_steering | shed 3->2 | hot PRB +48.4% cut, thp -1.6% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +12.2% lost, 1 cmd | reject |
| 5 | qoe_steering | shed 5->2,3->2 | hot PRB +47.0% cut, thp -3.0% lost, 2 cmd | accept | hot PRB +32.9% cut, thp +7.8% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->3 | hot PRB +44.5% cut, thp +0.9% lost, 2 cmd | accept | hot PRB +21.7% cut, thp +8.1% lost, 1 cmd | reject |
| 6 | qoe_steering | shed 3->None | hot PRB +52.4% cut, thp +13.0% lost, 1 cmd | reject | hot PRB +49.0% cut, thp -1.7% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->3 | hot PRB +29.7% cut, thp +15.0% lost, 2 cmd | reject | hot PRB +28.7% cut, thp +8.7% lost, 1 cmd | reject |
| 7 | qoe_steering | shed 2->3 | hot PRB +30.8% cut, thp +14.6% lost, 2 cmd | reject | hot PRB +27.9% cut, thp +2.3% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 8 | traffic_steering | shed 3->4 | hot PRB +56.8% cut, thp +3.8% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +11.3% lost, 1 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +57.5% cut, thp +4.3% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +9.4% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.5%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->3 | hot PRB +19.7% cut, thp -5.7% lost, 2 cmd | accept | hot PRB +19.7% cut, thp +2.0% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->None | hot PRB +100.0% cut, thp -1.9% lost, 1 cmd | accept | hot PRB +25.1% cut, thp -0.8% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 2
- live qoe_steering: 9
- live traffic_steering: 9
- twin energy_saving: 2
- twin qoe_steering: 8
- twin traffic_steering: 9
