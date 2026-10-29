# Twin-vs-live results - `base`

Runs: 64 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | -23.15 | -28.84 | -16.1% | -15.7% | 32.2 | 3479% (n=8) | 38% | 43% (n=7) |
| energy_saving | dl_throughput_mbps | 8 | -0.34 | -5.17 | -1.4% | -15.5% | 14.1 | 91% (n=7) | 25% | 14% (n=7) |
| energy_saving | dl_delay_ms | 8 | -0.25 | +14.21 | -6.8% | +337.4% | 364.8 | 103% (n=7) | 25% | 14% (n=7) |
| energy_saving | dl_buffer_kbytes | 8 | +114.87 | +1945.11 | +45.4% | +267653.6% | 267608.2 | 90% (n=7) | 38% | 43% (n=7) |
| energy_saving | energy_j_per_s | 8 | -1160.47 | -1833.16 | -21.4% | -25.7% | 10.5 | 40% (n=7) | 88% | 100% (n=7) |
| traffic_steering | prb_used_dl | 8 | +39.69 | +22.18 | +36.0% | +16.3% | 34.6 | 2602% (n=8) | 88% | 100% (n=7) |
| traffic_steering | dl_throughput_mbps | 8 | -1.17 | -1.05 | -4.3% | -2.7% | 9.5 | 189% (n=8) | 75% | 86% (n=7) |
| traffic_steering | dl_delay_ms | 8 | +12.42 | +33.22 | +401.2% | +932.1% | 1276.0 | 2153% (n=8) | 88% | 100% (n=7) |
| traffic_steering | dl_buffer_kbytes | 8 | +209.57 | +126.90 | +18052.9% | +5850.6% | 23895.6 | 224111% (n=8) | 62% | 71% (n=7) |
| traffic_steering | energy_j_per_s | 8 | +892.72 | +446.81 | +16.6% | +7.5% | 15.5 | 672% (n=8) | 88% | 100% (n=7) |
| qoe_steering | prb_used_dl | 8 | +7.78 | -25.13 | +7.6% | -13.1% | 23.6 | 138% (n=8) | 12% | 20% (n=5) |
| qoe_steering | dl_throughput_mbps | 8 | -0.28 | -1.98 | -0.6% | -5.4% | 9.6 | 96% (n=8) | 25% | 40% (n=5) |
| qoe_steering | dl_delay_ms | 8 | +0.36 | +3.80 | +34.7% | +81.2% | 154.2 | 542% (n=8) | 25% | 40% (n=5) |
| qoe_steering | dl_buffer_kbytes | 8 | -114.62 | +610.12 | +428894.7% | +77435.6% | 482922.9 | 103% (n=8) | 25% | 40% (n=5) |
| qoe_steering | energy_j_per_s | 8 | +163.08 | -631.73 | +3.2% | -8.7% | 13.5 | 134% (n=8) | 12% | 20% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 4 | 3 | 0 | 1 | 62% (5/8) [31, 86] | 57% (4/7) [25, 84] | 100% (4/4) [51, 100] | 25% (1/4) [5, 70] | 50% (4/8) [22, 78] |
| traffic_steering | 8 | 0 | 4 | 4 | 0 | 0% (0/8) [0, 32] | 0% (0/4) [0, 49] | 0% (0/4) [0, 49] | 0% (0/4) [0, 49] | 50% (4/8) [22, 78] |
| qoe_steering | 8 | 0 | 2 | 3 | 3 | 38% (3/8) [14, 69] | 0% (0/2) [0, 66] | 0% (0/3) [0, 56] | 60% (3/5) [23, 88] | 38% (3/8) [14, 69] |
| pooled | 24 | 4 | 9 | 7 | 4 | 33% (8/24) [18, 53] | 31% (4/13) [13, 58] | 36% (4/11) [15, 65] | 31% (4/13) [13, 58] | 46% (11/24) [28, 65] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [3] | E +14.0% saved, PRB(rem) +13.3%, 2 cmd | accept | E +31.5% saved, PRB(rem) +5.3%, 4 cmd | accept |
| 1 | traffic_steering | shed 2->3 | hot PRB +15.5% cut, thp +2.1% lost, 1 cmd | accept | hot PRB +14.6% cut, thp +13.0% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 4->3,5->3 | hot PRB +100.0% cut, thp +15.0% lost, 2 cmd | reject | hot PRB +61.5% cut, thp +14.1% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E -0.2% saved, PRB(rem) -100.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.6%, 0 cmd | reject |
| 2 | traffic_steering | shed 5->3 | hot PRB +47.6% cut, thp +3.2% lost, 1 cmd | accept | hot PRB +0.4% cut, thp -18.5% lost, 1 cmd | reject |
| 2 | qoe_steering | shed 4->2,5->2 | hot PRB +35.2% cut, thp +0.4% lost, 2 cmd | accept | hot PRB +1.8% cut, thp -14.8% lost, 1 cmd | reject |
| 3 | energy_saving | sleep [4, 3] | E +21.8% saved, PRB(rem) +0.0%, 2 cmd | accept | E +30.5% saved, PRB(rem) -4.4%, 3 cmd | accept |
| 3 | traffic_steering | shed 5->4 | hot PRB +0.0% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +74.7% cut, thp -2.2% lost, 1 cmd | accept |
| 3 | qoe_steering | shed 4->None,3->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +100.0% cut, thp -1.1% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [4, 3, 5] | E +30.1% saved, PRB(rem) -0.4%, 2 cmd | accept | E +24.7% saved, PRB(rem) +58.9%, 6 cmd | reject |
| 4 | traffic_steering | shed 2->4 | hot PRB +27.5% cut, thp +6.4% lost, 2 cmd | reject | hot PRB +13.5% cut, thp +1.8% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 4->5,3->5 | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +44.4% cut, thp +18.6% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [4, 2] | E +42.1% saved, PRB(rem) -3.6%, 6 cmd | accept | E +22.5% saved, PRB(rem) +121.3%, 9 cmd | reject |
| 5 | traffic_steering | shed 3->4 | hot PRB +43.5% cut, thp +2.2% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +10.4% lost, 1 cmd | reject |
| 5 | qoe_steering | shed 4->None | hot PRB --% cut, thp -15.2% lost, 1 cmd | reject | hot PRB +100.0% cut, thp +9.5% lost, 1 cmd | reject |
| 6 | energy_saving | sleep [5, 4] | E +23.7% saved, PRB(rem) +2.2%, 2 cmd | accept | E +43.8% saved, PRB(rem) +10.9%, 5 cmd | accept |
| 6 | traffic_steering | shed 2->5 | hot PRB +41.8% cut, thp +11.4% lost, 2 cmd | reject | hot PRB +13.5% cut, thp +1.4% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 4->None,5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +83.7% cut, thp +2.1% lost, 2 cmd | accept |
| 7 | energy_saving | sleep [5, 4, 3] | E +28.6% saved, PRB(rem) +9.6%, 3 cmd | accept | E +39.9% saved, PRB(rem) +17.4%, 7 cmd | accept |
| 7 | traffic_steering | shed 2->5 | hot PRB +21.9% cut, thp +7.7% lost, 2 cmd | reject | hot PRB +51.8% cut, thp +1.3% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 5->None,2->None | hot PRB +38.1% cut, thp +6.6% lost, 2 cmd | reject | hot PRB +68.5% cut, thp +4.4% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [5] | E +11.1% saved, PRB(rem) +0.0%, 1 cmd | accept | E +12.6% saved, PRB(rem) +43.3%, 3 cmd | reject |
| 8 | traffic_steering | shed 2->5 | hot PRB +11.7% cut, thp +1.6% lost, 1 cmd | accept | hot PRB +29.1% cut, thp +13.9% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 5->None,3->None | hot PRB +55.1% cut, thp -1.7% lost, 1 cmd | accept | hot PRB +71.0% cut, thp +10.2% lost, 2 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 7
- live qoe_steering: 8
- live traffic_steering: 8
- twin energy_saving: 7
- twin qoe_steering: 5
- twin traffic_steering: 7
