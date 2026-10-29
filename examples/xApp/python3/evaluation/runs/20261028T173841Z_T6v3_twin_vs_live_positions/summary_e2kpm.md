# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live_positions`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_throughput_mbps | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 9 | +16.22 | +22.44 | +9.1% | +15.5% | 14.7 | 251% (n=8) | 67% | 62% (n=8) |
| traffic_steering | dl_throughput_mbps | 9 | -0.67 | -0.68 | -3.5% | -4.0% | 4.0 | 249% (n=8) | 56% | 50% (n=8) |
| traffic_steering | dl_buffer_kbytes | 9 | +597.96 | +307.19 | +18370.0% | +27932.6% | 44511.1 | 199% (n=8) | 100% | 100% (n=8) |
| traffic_steering | energy_j_per_s | 9 | +376.23 | +528.46 | +5.3% | +8.4% | 8.0 | 252% (n=8) | 67% | 62% (n=8) |
| qoe_steering | prb_used_dl | 9 | -5.01 | +13.53 | +0.5% | +7.8% | 17.1 | 99% (n=8) | 56% | 62% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -1.44 | -0.78 | -7.9% | -4.3% | 5.6 | 189% (n=8) | 78% | 88% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +871.57 | +461.32 | +28491.1% | +101816.5% | 106382.7 | 8397% (n=8) | 56% | 62% (n=8) |
| qoe_steering | energy_j_per_s | 9 | -132.50 | +314.07 | -0.7% | +4.5% | 10.2 | 99% (n=8) | 56% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 2 | 1 | 2 | 4 | 67% (6/9) [35, 88] | 67% (2/3) [21, 94] | 50% (2/4) [15, 85] | 80% (4/5) [38, 96] | 44% (4/9) [19, 73] |
| qoe_steering | 9 | 2 | 0 | 2 | 5 | 78% (7/9) [45, 94] | 100% (2/2) [34, 100] | 50% (2/4) [15, 85] | 100% (5/5) [57, 100] | 44% (4/9) [19, 73] |
| pooled | 27 | 4 | 1 | 4 | 18 | 81% (22/27) [63, 92] | 80% (4/5) [38, 96] | 50% (4/8) [22, 78] | 95% (18/19) [75, 99] | 30% (8/27) [16, 48] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +23.0% cut, thp +5.6% lost, 2 cmd | reject | hot PRB +15.3% cut, thp +6.3% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 2->4 | hot PRB +25.5% cut, thp +9.1% lost, 2 cmd | reject | hot PRB +12.8% cut, thp +2.5% lost, 1 cmd | accept |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +23.2% cut, thp +14.0% lost, 2 cmd | reject | hot PRB +33.3% cut, thp +16.8% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->5,3->5 | hot PRB +100.0% cut, thp +16.1% lost, 2 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->4 | hot PRB +0.2% cut, thp -8.4% lost, 2 cmd | reject | hot PRB +4.9% cut, thp +2.8% lost, 2 cmd | reject |
| 3 | qoe_steering | shed 2->4,5->4 | hot PRB +1.9% cut, thp +11.2% lost, 3 cmd | reject | hot PRB +41.7% cut, thp +5.6% lost, 3 cmd | reject |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 5->4 | hot PRB +21.2% cut, thp -0.1% lost, 1 cmd | accept | hot PRB +44.0% cut, thp +5.5% lost, 1 cmd | reject |
| 4 | qoe_steering | shed 2->4,5->4 | hot PRB +22.6% cut, thp +13.9% lost, 2 cmd | reject | hot PRB +21.4% cut, thp +8.8% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->5 | hot PRB +10.4% cut, thp +4.7% lost, 1 cmd | accept | hot PRB +30.5% cut, thp +4.3% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->5,4->5 | hot PRB +40.8% cut, thp +9.4% lost, 2 cmd | reject | hot PRB +39.0% cut, thp +11.0% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->5 | hot PRB +19.2% cut, thp +8.5% lost, 1 cmd | reject | hot PRB +15.0% cut, thp +2.4% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 3->5 | hot PRB +14.6% cut, thp +9.4% lost, 1 cmd | reject | hot PRB +44.9% cut, thp +1.6% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 4->5 | hot PRB +31.2% cut, thp +1.9% lost, 1 cmd | accept | hot PRB +31.1% cut, thp -0.3% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 2->5,3->5 | hot PRB +37.8% cut, thp -5.0% lost, 2 cmd | accept | hot PRB +47.8% cut, thp +0.9% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 8 | qoe_steering | shed 5->2 | hot PRB +28.8% cut, thp +1.2% lost, 1 cmd | accept | hot PRB +41.2% cut, thp +1.2% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 3->4 | hot PRB +15.2% cut, thp +5.4% lost, 1 cmd | reject | hot PRB +25.7% cut, thp -1.5% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->4 | hot PRB +15.2% cut, thp +5.4% lost, 1 cmd | reject | hot PRB +25.5% cut, thp +7.4% lost, 1 cmd | reject |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 8
- live traffic_steering: 8
- twin qoe_steering: 9
- twin traffic_steering: 8
