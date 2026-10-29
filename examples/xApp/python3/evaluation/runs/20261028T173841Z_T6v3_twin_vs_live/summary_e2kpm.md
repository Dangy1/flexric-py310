# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_throughput_mbps | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 9 | +39.27 | +5.67 | +37.5% | +1.5% | 36.0 | 490% (n=9) | 78% | 78% (n=9) |
| traffic_steering | dl_throughput_mbps | 9 | -0.80 | -0.99 | -5.7% | -6.1% | 3.3 | 86% (n=9) | 67% | 67% (n=9) |
| traffic_steering | dl_buffer_kbytes | 9 | +180.62 | +715.84 | +84280.7% | +21100.0% | 85829.7 | 221% (n=9) | 67% | 67% (n=9) |
| traffic_steering | energy_j_per_s | 9 | +922.69 | +128.83 | +17.2% | +1.3% | 15.9 | 556% (n=9) | 78% | 78% (n=9) |
| qoe_steering | prb_used_dl | 9 | +27.29 | -3.00 | +25.0% | -2.3% | 36.4 | 615% (n=9) | 67% | 75% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -0.89 | -0.59 | -5.6% | -3.4% | 4.0 | 157% (n=9) | 78% | 88% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +333.34 | +592.31 | +151373.0% | +94186.2% | 225618.3 | 43143% (n=9) | 78% | 88% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +635.09 | -78.72 | +11.6% | -1.3% | 16.7 | 934% (n=9) | 67% | 75% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 5 | 1 | 1 | 2 | 78% (7/9) [45, 94] | 83% (5/6) [44, 97] | 83% (5/6) [44, 97] | 67% (2/3) [21, 94] | 67% (6/9) [35, 88] |
| qoe_steering | 9 | 2 | 1 | 4 | 2 | 44% (4/9) [19, 73] | 67% (2/3) [21, 94] | 33% (2/6) [10, 70] | 67% (2/3) [21, 94] | 67% (6/9) [35, 88] |
| pooled | 27 | 7 | 2 | 5 | 13 | 74% (20/27) [55, 87] | 78% (7/9) [45, 94] | 58% (7/12) [32, 81] | 87% (13/15) [62, 96] | 44% (12/27) [28, 63] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +12.5% cut, thp +4.5% lost, 1 cmd | accept | hot PRB +12.8% cut, thp +2.5% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 3->4,2->4 | hot PRB +26.8% cut, thp +6.4% lost, 2 cmd | reject | hot PRB +9.9% cut, thp +6.8% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 5->3 | hot PRB +47.8% cut, thp -0.1% lost, 1 cmd | accept | hot PRB +63.8% cut, thp +6.6% lost, 1 cmd | reject |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +55.3% cut, thp +1.2% lost, 2 cmd | accept | hot PRB +63.9% cut, thp +2.4% lost, 1 cmd | accept |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->5 | hot PRB +13.4% cut, thp +27.1% lost, 2 cmd | reject | hot PRB +29.4% cut, thp +25.4% lost, 2 cmd | reject |
| 3 | qoe_steering | shed 5->None | hot PRB +0.0% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +76.0% cut, thp +1.1% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +38.5% cut, thp +5.2% lost, 2 cmd | reject | hot PRB +11.3% cut, thp +2.7% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +38.1% cut, thp +6.1% lost, 2 cmd | reject | hot PRB +16.6% cut, thp +0.7% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 5->4 | hot PRB +54.8% cut, thp -0.5% lost, 1 cmd | accept | hot PRB +16.7% cut, thp +1.1% lost, 1 cmd | accept |
| 5 | qoe_steering | shed 3->4,5->4 | hot PRB +46.9% cut, thp +3.7% lost, 2 cmd | accept | hot PRB +33.7% cut, thp +7.4% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->3 | hot PRB +42.9% cut, thp +0.0% lost, 2 cmd | accept | hot PRB +19.7% cut, thp +1.3% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 3->None | hot PRB +55.4% cut, thp +15.1% lost, 1 cmd | reject | hot PRB +50.5% cut, thp -2.9% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->3 | hot PRB +32.6% cut, thp +3.6% lost, 2 cmd | accept | hot PRB +19.9% cut, thp +3.0% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 2->3 | hot PRB +32.6% cut, thp +7.6% lost, 2 cmd | reject | hot PRB +19.9% cut, thp +3.0% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | shed 2->4 | hot PRB +1.7% cut, thp +6.9% lost, 1 cmd | reject | hot PRB +37.8% cut, thp +14.0% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +56.9% cut, thp +6.3% lost, 1 cmd | reject | hot PRB +100.0% cut, thp +7.6% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->3 | hot PRB +20.6% cut, thp +4.3% lost, 2 cmd | accept | hot PRB +16.7% cut, thp -2.0% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->None | hot PRB +100.0% cut, thp +4.4% lost, 1 cmd | accept | hot PRB +27.6% cut, thp +4.4% lost, 1 cmd | accept |

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 9
- live traffic_steering: 9
- twin qoe_steering: 8
- twin traffic_steering: 9
