# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live_loadcal`

Runs: 68 (5 failed). Pairs analysed: [1, 2, 4, 5, 6, 8, 9]; excluded: [3, 7].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 7 | +5.08 | -6.28 | +10.6% | -3.6% | 14.4 | 135% (n=7) | 29% | 0% (n=1) |
| energy_saving | dl_throughput_mbps | 7 | +0.13 | -0.05 | +1.0% | -0.3% | 1.3 | 172% (n=7) | 43% | 0% (n=1) |
| energy_saving | dl_buffer_kbytes | 7 | -669.47 | +206.49 | -8.5% | +8776.7% | 8822.4 | 270% (n=7) | 86% | 0% (n=1) |
| energy_saving | energy_j_per_s | 7 | +46.77 | -250.44 | +1.0% | -3.6% | 4.6 | 119% (n=1) | 86% | 0% (n=1) |
| traffic_steering | prb_used_dl | 7 | +24.24 | +13.22 | +14.5% | +9.4% | 19.1 | 11073% (n=7) | 57% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 7 | -0.18 | -0.70 | -0.9% | -4.2% | 4.4 | 4295% (n=7) | 86% | 80% (n=5) |
| traffic_steering | dl_buffer_kbytes | 7 | -80.18 | +368.89 | +25402.3% | +9349.6% | 16061.5 | 7075% (n=7) | 43% | 40% (n=5) |
| traffic_steering | energy_j_per_s | 7 | +565.41 | +316.33 | +8.9% | +5.0% | 7.4 | 129% (n=5) | 71% | 80% (n=5) |
| qoe_steering | prb_used_dl | 7 | +21.20 | -13.33 | +34.8% | -8.1% | 44.8 | 922% (n=7) | 86% | 86% (n=7) |
| qoe_steering | dl_throughput_mbps | 7 | -0.49 | -1.29 | -1.5% | -7.7% | 11.0 | 157% (n=7) | 86% | 86% (n=7) |
| qoe_steering | dl_buffer_kbytes | 7 | -754.93 | +912.14 | +22015.2% | +12094.2% | 21068.2 | 101015% (n=7) | 57% | 57% (n=7) |
| qoe_steering | energy_j_per_s | 7 | +474.18 | -326.44 | +10.2% | -4.8% | 16.4 | 720% (n=7) | 86% | 86% (n=7) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 7 | 0 | 0 | 1 | 6 | 86% (6/7) [49, 97] | -- (0/0) | 0% (0/1) [0, 79] | 100% (6/6) [61, 100] | 14% (1/7) [3, 51] |
| traffic_steering | 7 | 1 | 2 | 1 | 3 | 57% (4/7) [25, 84] | 33% (1/3) [6, 79] | 50% (1/2) [9, 91] | 60% (3/5) [23, 88] | 29% (2/7) [8, 64] |
| qoe_steering | 7 | 2 | 1 | 3 | 1 | 43% (3/7) [16, 75] | 67% (2/3) [21, 94] | 40% (2/5) [12, 77] | 50% (1/2) [9, 91] | 71% (5/7) [36, 92] |
| pooled | 21 | 3 | 3 | 5 | 10 | 62% (13/21) [41, 79] | 50% (3/6) [19, 81] | 38% (3/8) [14, 69] | 77% (10/13) [50, 92] | 38% (8/21) [21, 59] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->5 | hot PRB +6.3% cut, thp +0.9% lost, 2 cmd | accept | hot PRB +5.6% cut, thp +2.7% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->5,3->5 | hot PRB +25.2% cut, thp +11.4% lost, 3 cmd | reject | hot PRB +33.3% cut, thp +4.7% lost, 2 cmd | accept |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +18.9% cut, thp +6.5% lost, 2 cmd | reject | hot PRB +6.0% cut, thp +6.6% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +74.6% cut, thp +9.3% lost, 2 cmd | reject | hot PRB +62.9% cut, thp +3.9% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.6%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +34.1% cut, thp +5.8% lost, 2 cmd | reject | hot PRB +16.7% cut, thp +2.0% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +37.7% cut, thp +4.3% lost, 2 cmd | accept | hot PRB +16.7% cut, thp +2.2% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +5.7% cut, thp -3.7% lost, 1 cmd | accept | hot PRB +25.5% cut, thp +7.4% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 3->None,4->None | hot PRB +66.8% cut, thp +12.5% lost, 2 cmd | reject | hot PRB +100.0% cut, thp +19.3% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject |
| 6 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 6 | qoe_steering | shed 2->3 | hot PRB +12.6% cut, thp +4.4% lost, 2 cmd | accept | hot PRB +21.2% cut, thp +1.9% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject |
| 8 | traffic_steering | shed 2->4 | hot PRB -1.1% cut, thp +0.5% lost, 2 cmd | reject | hot PRB +15.8% cut, thp +10.8% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +53.2% cut, thp -3.7% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +25.6% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [2] | E -6.7% saved, PRB(rem) +87.9%, 9 cmd | reject | E +25.2% saved, PRB(rem) +20.9%, 5 cmd | accept |
| 9 | traffic_steering | shed 5->2 | hot PRB +100.0% cut, thp -3.6% lost, 1 cmd | accept | hot PRB --% cut, thp -0.0% lost, 0 cmd | reject |
| 9 | qoe_steering | shed 2->None | hot PRB -10.3% cut, thp -28.0% lost, 2 cmd | reject | hot PRB +30.8% cut, thp -3.6% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 1
- live qoe_steering: 8
- live traffic_steering: 5
- twin energy_saving: 1
- twin qoe_steering: 8
- twin traffic_steering: 6

Failed runs:

- twin s3 energy_saving: ns-3 rc=-6; no KPM report at or after t_act; KPI window has reports in 0/54 periods
- twin s3 noop: ns-3 rc=-6; no KPM report at or after t_act; KPI window has reports in 0/54 periods
- twin s3 qoe_steering: ns-3 rc=-6; no KPM report at or after t_act; KPI window has reports in 0/54 periods
- twin s3 traffic_steering: ns-3 rc=-6; no KPM report at or after t_act; KPI window has reports in 0/54 periods
- twin s7 traffic_steering: ns-3 rc=-6; KPI window has reports in 0/54 periods
