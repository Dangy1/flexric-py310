# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live_positions`

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
| traffic_steering | prb_used_dl | 9 | +15.95 | +22.40 | +8.7% | +15.1% | 14.4 | 252% (n=8) | 67% | 62% (n=8) |
| traffic_steering | dl_throughput_mbps | 9 | -1.91 | -1.75 | -5.7% | -5.6% | 3.8 | 122% (n=8) | 100% | 100% (n=8) |
| traffic_steering | dl_delay_ms | 9 | +0.63 | +20.12 | +278.9% | +531.6% | 270.6 | 795% (n=8) | 67% | 62% (n=8) |
| traffic_steering | dl_buffer_kbytes | 9 | +597.96 | +307.19 | +18370.0% | +27932.6% | 44511.1 | 199% (n=8) | 100% | 100% (n=8) |
| traffic_steering | energy_j_per_s | 9 | +376.23 | +528.46 | +5.3% | +8.4% | 8.0 | 252% (n=8) | 67% | 62% (n=8) |
| qoe_steering | prb_used_dl | 9 | -5.35 | +13.40 | +0.2% | +7.5% | 16.7 | 100% (n=8) | 56% | 62% (n=8) |
| qoe_steering | dl_throughput_mbps | 9 | -2.49 | -1.61 | -7.4% | -4.6% | 6.7 | 342% (n=8) | 56% | 62% (n=8) |
| qoe_steering | dl_delay_ms | 9 | -13.75 | +31.34 | -1.3% | +888.5% | 898.5 | 220% (n=8) | 44% | 50% (n=8) |
| qoe_steering | dl_buffer_kbytes | 9 | +871.57 | +461.32 | +28491.1% | +101816.5% | 106382.7 | 8397% (n=8) | 56% | 62% (n=8) |
| qoe_steering | energy_j_per_s | 9 | -132.50 | +314.07 | -0.7% | +4.5% | 10.2 | 99% (n=8) | 56% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 9 | 0 | 0 | 0 | 9 | 100% (9/9) [70, 100] | -- (0/0) | -- (0/0) | 100% (9/9) [70, 100] | 0% (0/9) [0, 30] |
| traffic_steering | 9 | 1 | 1 | 3 | 4 | 56% (5/9) [27, 81] | 50% (1/2) [9, 91] | 25% (1/4) [5, 70] | 80% (4/5) [38, 96] | 44% (4/9) [19, 73] |
| qoe_steering | 9 | 2 | 0 | 3 | 4 | 67% (6/9) [35, 88] | 100% (2/2) [34, 100] | 40% (2/5) [12, 77] | 100% (4/4) [51, 100] | 56% (5/9) [27, 81] |
| pooled | 27 | 3 | 1 | 6 | 17 | 74% (20/27) [55, 87] | 75% (3/4) [30, 95] | 33% (3/9) [12, 65] | 94% (17/18) [74, 99] | 33% (9/27) [19, 52] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->4 | hot PRB +23.4% cut, thp +9.0% lost, 2 cmd | reject | hot PRB +15.7% cut, thp +4.2% lost, 1 cmd | accept |
| 1 | qoe_steering | shed 2->4 | hot PRB +25.7% cut, thp +9.7% lost, 2 cmd | reject | hot PRB +13.1% cut, thp -0.9% lost, 1 cmd | accept |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->5 | hot PRB +23.8% cut, thp +10.2% lost, 2 cmd | reject | hot PRB +33.2% cut, thp +18.5% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->5,3->5 | hot PRB +100.0% cut, thp +6.4% lost, 2 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 3 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 3 | traffic_steering | shed 2->4 | hot PRB +0.7% cut, thp -5.1% lost, 2 cmd | reject | hot PRB +5.3% cut, thp -0.9% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->4,5->4 | hot PRB +2.6% cut, thp +11.2% lost, 3 cmd | reject | hot PRB +41.5% cut, thp +2.9% lost, 3 cmd | accept |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 5->4 | hot PRB +21.5% cut, thp +2.1% lost, 1 cmd | accept | hot PRB +44.1% cut, thp +6.0% lost, 1 cmd | reject |
| 4 | qoe_steering | shed 2->4,5->4 | hot PRB +22.9% cut, thp +16.0% lost, 2 cmd | reject | hot PRB +21.6% cut, thp +9.9% lost, 2 cmd | reject |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->5 | hot PRB +11.0% cut, thp +11.9% lost, 1 cmd | reject | hot PRB +30.5% cut, thp +9.3% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 2->5,4->5 | hot PRB +40.7% cut, thp +10.2% lost, 2 cmd | reject | hot PRB +39.3% cut, thp +12.6% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | shed 2->5 | hot PRB +19.5% cut, thp +11.0% lost, 1 cmd | reject | hot PRB +15.1% cut, thp +4.5% lost, 1 cmd | accept |
| 6 | qoe_steering | shed 3->5 | hot PRB +15.0% cut, thp +11.4% lost, 1 cmd | reject | hot PRB +44.6% cut, thp +2.0% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 4->5 | hot PRB +31.2% cut, thp +3.3% lost, 1 cmd | accept | hot PRB +30.9% cut, thp +3.4% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 2->5,3->5 | hot PRB +37.5% cut, thp -7.9% lost, 2 cmd | accept | hot PRB +47.8% cut, thp +2.4% lost, 2 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 8 | qoe_steering | shed 5->2 | hot PRB +29.0% cut, thp +1.0% lost, 1 cmd | accept | hot PRB +41.5% cut, thp -1.1% lost, 1 cmd | accept |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 3->4 | hot PRB +15.2% cut, thp +8.9% lost, 1 cmd | reject | hot PRB +25.3% cut, thp +5.1% lost, 1 cmd | reject |
| 9 | qoe_steering | shed 3->4 | hot PRB +15.2% cut, thp +8.9% lost, 1 cmd | reject | hot PRB +25.3% cut, thp +13.8% lost, 1 cmd | reject |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -2.5 (min -3.3, max -1.6, n=72); dl_throughput_mbps mean -44.7 (min -50.2, max -39.6, n=72); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=72); prb_used_dl_per_cell mean -2.5 (min -4.1, max -0.6, n=248).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 96%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 81%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 96%, live 81% of 27 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 8
- live traffic_steering: 8
- twin qoe_steering: 9
- twin traffic_steering: 8
