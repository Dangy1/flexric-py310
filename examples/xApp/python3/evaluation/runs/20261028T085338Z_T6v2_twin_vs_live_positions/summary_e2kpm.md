# Twin-vs-live results - `20261028T085338Z_T6v2_twin_vs_live_positions`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | -0.25 | -0.06 | -0.1% | -0.0% | 0.3 | 372% (n=8) | 44% | -- |
| energy_saving | dl_throughput_mbps | 9 | +0.00 | -0.00 | +0.0% | -0.0% | 0.0 | 340% (n=8) | 33% | -- |
| energy_saving | dl_buffer_kbytes | 9 | +0.69 | -0.63 | +38.1% | +105.6% | 158.1 | 1767% (n=8) | 44% | -- |
| energy_saving | energy_j_per_s | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 9 | +29.91 | +27.07 | +17.6% | +18.4% | 12.9 | 630% (n=9) | 67% | 75% (n=8) |
| traffic_steering | dl_throughput_mbps | 9 | -0.48 | -0.96 | -2.5% | -5.5% | 4.5 | 131% (n=9) | 78% | 75% (n=8) |
| traffic_steering | dl_buffer_kbytes | 9 | +443.13 | +448.94 | +21598.3% | +19599.6% | 34600.6 | 451% (n=9) | 56% | 62% (n=8) |
| traffic_steering | energy_j_per_s | 9 | +690.33 | +640.64 | +10.0% | +10.0% | 6.5 | 345% (n=8) | 78% | 75% (n=8) |
| qoe_steering | prb_used_dl | 9 | +8.45 | +1.98 | +7.9% | +1.7% | 24.8 | 3574% (n=9) | 56% | 50% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -1.14 | -0.84 | -6.2% | -4.6% | 9.1 | 29785% (n=9) | 67% | 62% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +853.26 | +637.60 | +14104.8% | +17310.1% | 25072.5 | 32870% (n=9) | 78% | 88% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +193.16 | +48.14 | +3.9% | +0.9% | 15.3 | 289% (n=8) | 44% | 50% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 4 | 2 | 1 | 2 | 67% (6/9) [35, 88] | 67% (4/6) [30, 90] | 80% (4/5) [38, 96] | 50% (2/4) [15, 85] | 56% (5/9) [27, 81] |
| qoe_steering | 9 | 1 | 3 | 4 | 1 | 22% (2/9) [6, 55] | 25% (1/4) [5, 70] | 20% (1/5) [4, 62] | 25% (1/4) [5, 70] | 56% (5/9) [27, 81] |
| pooled | 27 | 5 | 5 | 5 | 12 | 63% (17/27) [44, 78] | 50% (5/10) [24, 76] | 50% (5/10) [24, 76] | 71% (12/17) [47, 87] | 37% (10/27) [22, 56] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +31.6% cut, thp +7.0% lost, 2 cmd | reject | hot PRB +14.0% cut, thp +3.0% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->4 | hot PRB +17.5% cut, thp +4.7% lost, 2 cmd | accept | hot PRB +13.1% cut, thp +8.5% lost, 1 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +24.7% cut, thp +9.7% lost, 2 cmd | reject | hot PRB +27.3% cut, thp +11.7% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 3->5,4->5 | hot PRB +100.0% cut, thp +12.7% lost, 2 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->4 | hot PRB +7.0% cut, thp -5.5% lost, 2 cmd | accept | hot PRB +6.8% cut, thp +3.6% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 5->4,2->4 | hot PRB -0.7% cut, thp +8.2% lost, 3 cmd | reject | hot PRB +44.7% cut, thp +1.3% lost, 3 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.2%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 5->4 | hot PRB +23.7% cut, thp +4.0% lost, 1 cmd | accept | hot PRB +40.1% cut, thp +15.0% lost, 1 cmd | reject |
| 4 | qoe_steering | shed 5->4,2->4 | hot PRB +20.0% cut, thp -0.1% lost, 2 cmd | accept | hot PRB +34.8% cut, thp +9.1% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->5 | hot PRB +10.8% cut, thp -0.9% lost, 1 cmd | accept | hot PRB +24.2% cut, thp +7.5% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 4->5,2->5 | hot PRB +35.6% cut, thp -0.9% lost, 2 cmd | accept | hot PRB +45.6% cut, thp +19.9% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.3%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->5 | hot PRB +17.2% cut, thp +2.9% lost, 1 cmd | accept | hot PRB +21.2% cut, thp +4.1% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 3->5 | hot PRB +17.9% cut, thp +10.1% lost, 1 cmd | reject | hot PRB +51.0% cut, thp +2.2% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.1%, 0 cmd | reject |
| 7 | traffic_steering | shed 4->5 | hot PRB +26.9% cut, thp +3.1% lost, 1 cmd | accept | hot PRB +32.2% cut, thp +0.5% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 3->5,2->5 | hot PRB +63.3% cut, thp +6.1% lost, 2 cmd | reject | hot PRB +48.2% cut, thp +0.1% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.1%, 0 cmd | reject | E +0.0% saved, PRB(rem) -0.3%, 0 cmd | reject |
| 8 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 8 | qoe_steering | shed 5->2 | hot PRB +30.3% cut, thp +5.0% lost, 1 cmd | accept | hot PRB +37.1% cut, thp -1.2% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) -0.5%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.2%, 0 cmd | reject |
| 9 | traffic_steering | shed 3->4 | hot PRB +17.3% cut, thp +1.9% lost, 1 cmd | accept | hot PRB +22.5% cut, thp +3.9% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->4 | hot PRB +20.3% cut, thp +9.8% lost, 1 cmd | reject | hot PRB +23.8% cut, thp +1.3% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 8
- live traffic_steering: 8
- twin qoe_steering: 9
- twin traffic_steering: 8
