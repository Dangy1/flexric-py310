# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live`

Runs: 72 (0 failed). Pairs analysed: [1, 2, 3, 4, 5, 6, 7, 8, 9]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_throughput_mbps | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_delay_ms | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 9 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 9 | +39.11 | +5.46 | +35.9% | +1.4% | 34.5 | 556% (n=9) | 78% | 78% (n=9) |
| traffic_steering | dl_throughput_mbps | 9 | -1.89 | -2.18 | -7.4% | -7.5% | 6.1 | 346% (n=9) | 89% | 89% (n=9) |
| traffic_steering | dl_delay_ms | 9 | +32.90 | +7.96 | +1726.9% | +181.6% | 1815.5 | 1164% (n=9) | 78% | 78% (n=9) |
| traffic_steering | dl_buffer_kbytes | 9 | +180.62 | +715.84 | +84280.7% | +21100.0% | 85829.7 | 221% (n=9) | 67% | 67% (n=9) |
| traffic_steering | energy_j_per_s | 9 | +922.69 | +128.83 | +17.2% | +1.3% | 15.9 | 556% (n=9) | 78% | 78% (n=9) |
| qoe_steering | prb_used_dl | 9 | +27.10 | -3.16 | +23.9% | -2.3% | 35.0 | 752% (n=9) | 67% | 75% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -1.79 | -1.51 | -6.3% | -4.4% | 8.0 | 240% (n=9) | 56% | 62% (n=8) |
| qoe_steering | dl_delay_ms | 9 | +3.77 | +17.90 | +251.6% | +411.1% | 399.3 | 490% (n=9) | 67% | 75% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +333.34 | +592.31 | +151373.0% | +94186.2% | 225618.3 | 43143% (n=9) | 78% | 88% (n=8) |
| qoe_steering | energy_j_per_s | 9 | +635.09 | -78.72 | +11.6% | -1.3% | 16.7 | 934% (n=9) | 67% | 75% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 2 | 2 | 2 | 3 | 56% (5/9) [27, 81] | 50% (2/4) [15, 85] | 50% (2/4) [15, 85] | 60% (3/5) [23, 88] | 44% (4/9) [19, 73] |
| qoe_steering | 9 | 1 | 3 | 3 | 2 | 33% (3/9) [12, 65] | 25% (1/4) [5, 70] | 25% (1/4) [5, 70] | 40% (2/5) [12, 77] | 44% (4/9) [19, 73] |
| pooled | 27 | 3 | 5 | 5 | 14 | 63% (17/27) [44, 78] | 38% (3/8) [14, 69] | 38% (3/8) [14, 69] | 74% (14/19) [51, 88] | 30% (8/27) [16, 48] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +12.9% cut, thp +7.3% lost, 1 cmd | reject | hot PRB +13.1% cut, thp -0.9% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 3->4,2->4 | hot PRB +27.1% cut, thp +10.7% lost, 2 cmd | reject | hot PRB +10.3% cut, thp +5.8% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 5->3 | hot PRB +47.8% cut, thp +3.0% lost, 1 cmd | accept | hot PRB +63.2% cut, thp +12.4% lost, 1 cmd | reject |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +55.3% cut, thp +3.1% lost, 2 cmd | accept | hot PRB +63.6% cut, thp -1.6% lost, 1 cmd | accept |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->5 | hot PRB +14.9% cut, thp +19.7% lost, 2 cmd | reject | hot PRB +29.7% cut, thp +26.5% lost, 2 cmd | reject |
| 3 | qoe_steering | shed 5->None | hot PRB +0.0% cut, thp +0.0% lost, 0 cmd | reject | hot PRB +75.6% cut, thp -2.0% lost, 1 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +38.7% cut, thp +5.4% lost, 2 cmd | reject | hot PRB +11.6% cut, thp +0.8% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +38.6% cut, thp +5.0% lost, 2 cmd | reject | hot PRB +16.8% cut, thp +0.6% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 5->4 | hot PRB +54.4% cut, thp +1.7% lost, 1 cmd | accept | hot PRB +17.1% cut, thp +5.5% lost, 1 cmd | reject |
| 5 | qoe_steering | shed 3->4,5->4 | hot PRB +46.8% cut, thp +2.8% lost, 2 cmd | accept | hot PRB +34.3% cut, thp +14.3% lost, 2 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->3 | hot PRB +42.3% cut, thp +1.7% lost, 2 cmd | accept | hot PRB +19.7% cut, thp +0.1% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 3->None | hot PRB +55.0% cut, thp +14.8% lost, 1 cmd | reject | hot PRB +50.2% cut, thp -1.6% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->3 | hot PRB +32.8% cut, thp +16.8% lost, 2 cmd | reject | hot PRB +20.6% cut, thp +6.5% lost, 1 cmd | reject |
| 7 | qoe_steering | shed 2->3 | hot PRB +32.9% cut, thp +19.0% lost, 2 cmd | reject | hot PRB +20.6% cut, thp +6.5% lost, 1 cmd | reject |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | shed 2->4 | hot PRB +2.3% cut, thp +6.7% lost, 1 cmd | reject | hot PRB +38.1% cut, thp +14.6% lost, 2 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +56.8% cut, thp +3.8% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +7.3% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->3 | hot PRB +20.4% cut, thp +4.0% lost, 2 cmd | accept | hot PRB +17.0% cut, thp +1.9% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 3->None | hot PRB +100.0% cut, thp -1.9% lost, 1 cmd | accept | hot PRB +27.3% cut, thp +10.0% lost, 1 cmd | reject |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -2.9 (min -6.3, max -1.6, n=72); dl_throughput_mbps mean -42.5 (min -50.2, max -34.0, n=72); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=72); prb_used_dl_per_cell mean -2.8 (min -7.8, max -0.5, n=222).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 89%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 85%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 89%, live 85% of 27 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 9
- live traffic_steering: 9
- twin qoe_steering: 8
- twin traffic_steering: 9
