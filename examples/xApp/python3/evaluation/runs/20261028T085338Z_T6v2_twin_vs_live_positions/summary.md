# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live_positions`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | -0.05 | +0.23 | -0.0% | +0.1% | 0.3 | 261% (n=8) | 22% | -- |
| energy_saving | dl_throughput_mbps | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_delay_ms | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 9 | +29.42 | +27.47 | +17.1% | +18.4% | 12.5 | 575% (n=9) | 67% | 75% (n=8) |
| traffic_steering | dl_throughput_mbps | 9 | -1.93 | -2.24 | -5.7% | -6.7% | 5.0 | 163% (n=8) | 89% | 88% (n=8) |
| traffic_steering | dl_delay_ms | 9 | +25.67 | +22.40 | +437.5% | +626.2% | 567.2 | 2452% (n=8) | 100% | 100% (n=8) |
| traffic_steering | dl_buffer_kbytes | 9 | +448.44 | +456.19 | +23361.5% | +92840.2% | 110847.8 | 483% (n=8) | 78% | 75% (n=8) |
| traffic_steering | energy_j_per_s | 9 | +690.33 | +640.64 | +10.0% | +10.0% | 6.5 | 345% (n=8) | 78% | 75% (n=8) |
| qoe_steering | prb_used_dl | 9 | +8.49 | +2.48 | +7.8% | +1.9% | 24.6 | 10570% (n=9) | 44% | 50% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -2.75 | -2.24 | -8.2% | -6.5% | 8.8 | 491% (n=8) | 78% | 88% (n=8) |
| qoe_steering | dl_delay_ms | 9 | +15.60 | +22.43 | +682.2% | +650.4% | 503.3 | 3665% (n=8) | 67% | 75% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +863.50 | +644.00 | +14704.6% | +53084.7% | 60075.6 | 133293% (n=8) | 78% | 88% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +193.16 | +48.14 | +3.9% | +0.9% | 15.3 | 289% (n=8) | 44% | 50% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 2 | 2 | 1 | 4 | 67% (6/9) [35, 88] | 50% (2/4) [15, 85] | 67% (2/3) [21, 94] | 67% (4/6) [30, 90] | 33% (3/9) [12, 65] |
| qoe_steering | 9 | 1 | 1 | 4 | 3 | 44% (4/9) [19, 73] | 50% (1/2) [9, 91] | 20% (1/5) [4, 62] | 75% (3/4) [30, 95] | 56% (5/9) [27, 81] |
| pooled | 27 | 3 | 3 | 5 | 16 | 70% (19/27) [52, 84] | 50% (3/6) [19, 81] | 38% (3/8) [14, 69] | 84% (16/19) [62, 94] | 30% (8/27) [16, 48] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +32.1% cut, thp +11.0% lost, 2 cmd | reject | hot PRB +13.7% cut, thp -1.3% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->4 | hot PRB +18.2% cut, thp +5.2% lost, 2 cmd | reject | hot PRB +13.0% cut, thp +7.3% lost, 1 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +24.8% cut, thp +13.1% lost, 2 cmd | reject | hot PRB +27.4% cut, thp +9.1% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 3->5,4->5 | hot PRB +100.0% cut, thp +5.7% lost, 2 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->4 | hot PRB +7.5% cut, thp +1.7% lost, 2 cmd | accept | hot PRB +6.8% cut, thp +2.1% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 5->4,2->4 | hot PRB -0.8% cut, thp +11.2% lost, 3 cmd | reject | hot PRB +44.5% cut, thp +5.0% lost, 3 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 5->4 | hot PRB +24.0% cut, thp +7.0% lost, 1 cmd | reject | hot PRB +40.6% cut, thp +20.5% lost, 1 cmd | reject |
| 4 | qoe_steering | shed 5->4,2->4 | hot PRB +20.3% cut, thp +6.7% lost, 2 cmd | reject | hot PRB +34.6% cut, thp +10.1% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.3%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->5 | hot PRB +10.8% cut, thp +4.1% lost, 1 cmd | accept | hot PRB +24.2% cut, thp +10.8% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 4->5,2->5 | hot PRB +35.7% cut, thp +3.9% lost, 2 cmd | accept | hot PRB +45.6% cut, thp +30.2% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.4%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->5 | hot PRB +16.8% cut, thp +2.8% lost, 1 cmd | accept | hot PRB +20.9% cut, thp +8.5% lost, 1 cmd | reject |
| 6 | qoe_steering | shed 3->5 | hot PRB +18.1% cut, thp +11.6% lost, 1 cmd | reject | hot PRB +49.8% cut, thp +1.5% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.3%, 0 cmd | reject |
| 7 | traffic_steering | shed 4->5 | hot PRB +26.6% cut, thp +3.1% lost, 1 cmd | accept | hot PRB +32.4% cut, thp +3.9% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 3->5,2->5 | hot PRB +63.4% cut, thp +4.7% lost, 2 cmd | accept | hot PRB +48.1% cut, thp +1.9% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 8 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 8 | qoe_steering | shed 5->2 | hot PRB +30.3% cut, thp +9.6% lost, 1 cmd | reject | hot PRB +37.4% cut, thp -0.5% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject |
| 9 | traffic_steering | shed 3->4 | hot PRB +17.3% cut, thp +8.2% lost, 1 cmd | reject | hot PRB +22.2% cut, thp +6.9% lost, 1 cmd | reject |
| 9 | qoe_steering | shed 3->4 | hot PRB +21.1% cut, thp +15.5% lost, 1 cmd | reject | hot PRB +23.2% cut, thp +3.1% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 8
- live traffic_steering: 8
- twin qoe_steering: 9
- twin traffic_steering: 8
