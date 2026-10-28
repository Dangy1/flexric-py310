# Twin-vs-live results - `loadcal`

Runs: 72 (4 failed). Pairs analysed: [1, 2, 4, 5, 6, 7, 8, 9]; excluded: [3].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | -0.02 | -17.76 | -0.0% | -9.0% | 9.6 | 123% (n=8) | 62% | 60% (n=5) |
| energy_saving | dl_throughput_mbps | 8 | -0.00 | -1.45 | -0.0% | -7.8% | 7.8 | 116% (n=8) | 38% | 40% (n=5) |
| energy_saving | dl_buffer_kbytes | 8 | +1.10 | +712.15 | +73.2% | +53542.1% | 53629.5 | 106% (n=8) | 50% | 60% (n=5) |
| energy_saving | energy_j_per_s | 8 | -582.52 | -1005.49 | -11.9% | -13.9% | 4.1 | 37% (n=5) | 100% | 100% (n=5) |
| traffic_steering | prb_used_dl | 8 | +17.75 | +20.38 | +19.5% | +11.2% | 31.7 | 262% (n=8) | 75% | 75% (n=8) |
| traffic_steering | dl_throughput_mbps | 8 | -1.03 | -0.86 | -6.3% | -4.9% | 8.4 | 189% (n=8) | 62% | 62% (n=8) |
| traffic_steering | dl_buffer_kbytes | 8 | +236.10 | +515.30 | +24752.9% | +62029.6% | 86642.5 | 10532% (n=8) | 50% | 50% (n=8) |
| traffic_steering | energy_j_per_s | 8 | +810.66 | +481.41 | +15.2% | +6.7% | 14.5 | 394% (n=8) | 88% | 88% (n=8) |
| qoe_steering | prb_used_dl | 8 | +24.11 | +3.35 | +26.1% | +3.2% | 33.1 | 879% (n=8) | 62% | 50% (n=4) |
| qoe_steering | dl_throughput_mbps | 8 | -0.82 | -1.37 | -3.9% | -7.4% | 11.5 | 63512% (n=8) | 50% | 75% (n=4) |
| qoe_steering | dl_buffer_kbytes | 8 | -126.96 | +766.11 | +20723.3% | +26498.7% | 46925.5 | 44985% (n=8) | 12% | 25% (n=4) |
| qoe_steering | energy_j_per_s | 8 | +611.47 | +67.00 | +11.1% | +1.4% | 15.6 | 652% (n=7) | 25% | 50% (n=4) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 4 | 1 | 0 | 3 | 88% (7/8) [53, 98] | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 75% (3/4) [30, 95] | 50% (4/8) [22, 78] |
| traffic_steering | 8 | 2 | 2 | 2 | 2 | 50% (4/8) [22, 78] | 50% (2/4) [15, 85] | 50% (2/4) [15, 85] | 50% (2/4) [15, 85] | 50% (4/8) [22, 78] |
| qoe_steering | 8 | 1 | 1 | 1 | 5 | 75% (6/8) [41, 93] | 50% (1/2) [9, 91] | 50% (1/2) [9, 91] | 83% (5/6) [44, 97] | 25% (2/8) [7, 59] |
| pooled | 24 | 7 | 4 | 3 | 10 | 71% (17/24) [51, 85] | 64% (7/11) [35, 85] | 70% (7/10) [40, 89] | 71% (10/14) [45, 88] | 42% (10/24) [24, 61] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +22.4% cut, thp +14.5% lost, 2 cmd | reject | hot PRB +14.5% cut, thp +2.4% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->4,5->4 | hot PRB +41.9% cut, thp +21.8% lost, 3 cmd | reject | hot PRB +31.7% cut, thp +6.1% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +52.5% cut, thp +10.7% lost, 2 cmd | reject | hot PRB +40.6% cut, thp +8.2% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->5,3->5 | hot PRB +68.6% cut, thp +15.6% lost, 2 cmd | reject | hot PRB --% cut, thp -0.0% lost, 0 cmd | reject |
| 4 | energy_saving | sleep [4] | E +11.6% saved, PRB(rem) +0.1%, 1 cmd | accept | E +7.1% saved, PRB(rem) +27.2%, 3 cmd | accept |
| 4 | traffic_steering | shed 2->4 | hot PRB +5.9% cut, thp -1.7% lost, 2 cmd | accept | hot PRB +13.3% cut, thp +3.8% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 4->None,2->None | hot PRB +14.7% cut, thp +4.6% lost, 2 cmd | accept | hot PRB +36.5% cut, thp +4.1% lost, 2 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +19.1% cut, thp +1.7% lost, 1 cmd | accept | hot PRB +24.8% cut, thp -4.4% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->4,3->4 | hot PRB +27.6% cut, thp +7.4% lost, 2 cmd | reject | hot PRB +41.0% cut, thp +16.9% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [5, 4] | E +25.7% saved, PRB(rem) -0.2%, 2 cmd | accept | E +44.8% saved, PRB(rem) +6.1%, 5 cmd | accept |
| 6 | traffic_steering | shed 2->5 | hot PRB +28.1% cut, thp +18.1% lost, 2 cmd | reject | hot PRB +7.8% cut, thp +2.8% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 4->None,5->None | hot PRB --% cut, thp -0.0% lost, 0 cmd | reject | hot PRB +83.8% cut, thp +9.5% lost, 2 cmd | reject |
| 7 | energy_saving | sleep [5, 3, 2] | E +34.5% saved, PRB(rem) +0.0%, 2 cmd | accept | E +30.7% saved, PRB(rem) +26.6%, 5 cmd | accept |
| 7 | traffic_steering | shed 4->5 | hot PRB +100.0% cut, thp +8.8% lost, 1 cmd | reject | hot PRB +34.9% cut, thp +5.6% lost, 1 cmd | reject |
| 7 | qoe_steering | shed 3->None,5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +49.9% cut, thp +6.5% lost, 2 cmd | reject |
| 8 | energy_saving | sleep [5] | E +9.5% saved, PRB(rem) -0.0%, 1 cmd | accept | E +13.1% saved, PRB(rem) +42.2%, 3 cmd | reject |
| 8 | traffic_steering | shed 2->5 | hot PRB +13.7% cut, thp -2.8% lost, 2 cmd | accept | hot PRB +25.6% cut, thp +11.1% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 5->None | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +49.1% cut, thp +2.9% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [4] | E +13.5% saved, PRB(rem) +0.0%, 1 cmd | accept | E +15.2% saved, PRB(rem) +14.6%, 3 cmd | accept |
| 9 | traffic_steering | shed 3->4 | hot PRB +100.0% cut, thp +1.1% lost, 1 cmd | accept | hot PRB +23.6% cut, thp +10.0% lost, 1 cmd | reject |
| 9 | qoe_steering | shed 4->None,2->None | hot PRB +33.3% cut, thp -18.6% lost, 2 cmd | accept | hot PRB +43.0% cut, thp +13.2% lost, 2 cmd | reject |

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
