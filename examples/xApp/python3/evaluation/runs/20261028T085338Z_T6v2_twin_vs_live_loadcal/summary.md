# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live_loadcal`

Runs: 68 (5 failed). Pairs analysed: [1, 2, 4, 5, 6, 8, 9]; excluded: [3, 7].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 7 | +6.14 | -6.31 | +6.6% | -3.6% | 10.4 | 166% (n=7) | 43% | 0% (n=1) |
| energy_saving | dl_throughput_mbps | 7 | +0.72 | -0.38 | +3.4% | -1.1% | 4.4 | 293% (n=1) | 86% | 0% (n=1) |
| energy_saving | dl_delay_ms | 7 | +10.19 | -0.33 | +476.8% | -6.6% | 483.4 | 3194% (n=1) | 86% | 0% (n=1) |
| energy_saving | dl_buffer_kbytes | 7 | -678.32 | +208.36 | -7.2% | +93510.6% | 93517.8 | 426% (n=1) | 86% | 0% (n=1) |
| energy_saving | energy_j_per_s | 7 | +46.77 | -250.44 | +1.0% | -3.6% | 4.6 | 119% (n=1) | 86% | 0% (n=1) |
| traffic_steering | prb_used_dl | 7 | +24.38 | +13.58 | +16.7% | +9.6% | 16.3 | 1570% (n=7) | 71% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 7 | -0.71 | -1.50 | -1.8% | -4.7% | 7.4 | 585% (n=5) | 57% | 60% (n=5) |
| traffic_steering | dl_delay_ms | 7 | +31.05 | +12.67 | +314.4% | +336.2% | 271.4 | 7102% (n=5) | 86% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 7 | -79.53 | +371.35 | +35929.4% | +19999.2% | 23010.3 | 1023% (n=5) | 43% | 40% (n=5) |
| traffic_steering | energy_j_per_s | 7 | +565.41 | +316.33 | +8.9% | +5.0% | 7.4 | 129% (n=5) | 71% | 80% (n=5) |
| qoe_steering | prb_used_dl | 7 | +20.55 | -13.21 | +23.6% | -8.0% | 33.5 | 708% (n=7) | 86% | 86% (n=7) |
| qoe_steering | dl_throughput_mbps | 7 | +0.49 | -2.40 | +3.4% | -7.7% | 15.8 | 1407% (n=7) | 43% | 43% (n=7) |
| qoe_steering | dl_delay_ms | 7 | +34.34 | -0.18 | +1840.1% | -6.6% | 1871.3 | 23517% (n=7) | 86% | 86% (n=7) |
| qoe_steering | dl_buffer_kbytes | 7 | -769.83 | +917.43 | +31191.0% | +26542.6% | 38508.5 | 265150% (n=7) | 43% | 43% (n=7) |
| qoe_steering | energy_j_per_s | 7 | +474.18 | -326.44 | +10.2% | -4.8% | 16.4 | 720% (n=7) | 86% | 86% (n=7) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 7 | 0 | 0 | 1 | 6 | 86% (6/7) [49, 97] | -- (0/0) | 0% (0/1) [0, 79] | 100% (6/6) [61, 100] | 14% (1/7) [3, 51] |
| traffic_steering | 7 | 2 | 2 | 1 | 2 | 57% (4/7) [25, 84] | 50% (2/4) [15, 85] | 67% (2/3) [21, 94] | 50% (2/4) [15, 85] | 43% (3/7) [16, 75] |
| qoe_steering | 7 | 2 | 2 | 3 | 0 | 29% (2/7) [8, 64] | 50% (2/4) [15, 85] | 40% (2/5) [12, 77] | 0% (0/2) [0, 66] | 71% (5/7) [36, 92] |
| pooled | 21 | 4 | 4 | 5 | 8 | 57% (12/21) [37, 76] | 50% (4/8) [22, 78] | 44% (4/9) [19, 73] | 67% (8/12) [39, 86] | 43% (9/21) [24, 63] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->5 | hot PRB +6.8% cut, thp -4.6% lost, 2 cmd | accept | hot PRB +5.7% cut, thp +0.5% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->5,3->5 | hot PRB +25.5% cut, thp +5.4% lost, 3 cmd | reject | hot PRB +33.3% cut, thp +3.4% lost, 2 cmd | accept |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +18.9% cut, thp +14.6% lost, 2 cmd | reject | hot PRB +5.9% cut, thp +1.2% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +74.8% cut, thp +10.0% lost, 2 cmd | reject | hot PRB +63.2% cut, thp -1.7% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +34.6% cut, thp +3.1% lost, 2 cmd | accept | hot PRB +16.7% cut, thp +0.7% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +37.9% cut, thp +3.8% lost, 2 cmd | accept | hot PRB +16.9% cut, thp +0.7% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.3%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +5.8% cut, thp +3.8% lost, 1 cmd | accept | hot PRB +25.2% cut, thp +17.3% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 3->None,4->None | hot PRB +67.1% cut, thp +2.1% lost, 2 cmd | accept | hot PRB +100.0% cut, thp +19.4% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 6 | qoe_steering | shed 2->3 | hot PRB +12.5% cut, thp -2.1% lost, 2 cmd | accept | hot PRB +21.1% cut, thp +0.5% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject |
| 8 | traffic_steering | shed 2->4 | hot PRB -0.7% cut, thp -2.7% lost, 2 cmd | reject | hot PRB +16.1% cut, thp +13.1% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +53.3% cut, thp -8.0% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +31.0% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [2] | E -6.7% saved, PRB(rem) +158.7%, 9 cmd | reject | E +25.2% saved, PRB(rem) +21.0%, 5 cmd | accept |
| 9 | traffic_steering | shed 5->2 | hot PRB +100.0% cut, thp -1.5% lost, 1 cmd | accept | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 9 | qoe_steering | shed 2->None | hot PRB -4.5% cut, thp -34.8% lost, 2 cmd | reject | hot PRB +30.9% cut, thp +0.3% lost, 1 cmd | accept |

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
