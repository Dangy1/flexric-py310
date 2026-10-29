# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live_loadcal`

Runs: 69 (4 failed). Pairs analysed: [1, 2, 4, 5, 6, 7, 8, 9]; excluded: [3].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_throughput_mbps | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_delay_ms | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 8 | +35.03 | +10.00 | +40.5% | +7.1% | 37.7 | 253% (n=7) | 100% | 100% (n=7) |
| traffic_steering | dl_throughput_mbps | 8 | +0.14 | -1.61 | +1.8% | -4.7% | 10.3 | 425% (n=7) | 62% | 57% (n=7) |
| traffic_steering | dl_delay_ms | 8 | +16.76 | +13.50 | +1789.4% | +355.4% | 1739.2 | 4868% (n=7) | 100% | 100% (n=7) |
| traffic_steering | dl_buffer_kbytes | 8 | -704.80 | +309.33 | +27443.8% | +43552.6% | 48885.1 | 28764% (n=7) | 38% | 29% (n=7) |
| traffic_steering | energy_j_per_s | 8 | +826.45 | +233.69 | +16.5% | +3.8% | 14.0 | 253% (n=7) | 100% | 100% (n=7) |
| qoe_steering | prb_used_dl | 8 | +37.88 | -14.95 | +44.8% | -9.7% | 54.6 | 636% (n=8) | 62% | 62% (n=8) |
| qoe_steering | dl_throughput_mbps | 8 | -0.03 | -3.08 | +1.7% | -9.4% | 12.4 | 352% (n=8) | 62% | 62% (n=8) |
| qoe_steering | dl_delay_ms | 8 | +32.17 | +1.26 | +2381.1% | +34.8% | 2366.1 | 31077% (n=8) | 62% | 62% (n=8) |
| qoe_steering | dl_buffer_kbytes | 8 | -668.77 | +1101.03 | +88246.8% | +63782.5% | 85192.0 | 5303% (n=8) | 50% | 50% (n=8) |
| qoe_steering | energy_j_per_s | 8 | +888.89 | -357.40 | +18.2% | -5.5% | 23.6 | 635% (n=8) | 62% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 0 | 0 | 0 | 8 | 100% (8/8) [68, 100] | -- (0/0) | -- (0/0) | 100% (8/8) [68, 100] | 0% (0/8) [0, 32] |
| traffic_steering | 8 | 3 | 3 | 1 | 1 | 50% (4/8) [22, 78] | 50% (3/6) [19, 81] | 75% (3/4) [30, 95] | 25% (1/4) [5, 70] | 50% (4/8) [22, 78] |
| qoe_steering | 8 | 3 | 3 | 0 | 2 | 62% (5/8) [31, 86] | 50% (3/6) [19, 81] | 100% (3/3) [44, 100] | 40% (2/5) [12, 77] | 38% (3/8) [14, 69] |
| pooled | 24 | 6 | 6 | 1 | 11 | 71% (17/24) [51, 85] | 50% (6/12) [25, 75] | 86% (6/7) [49, 97] | 65% (11/17) [41, 83] | 29% (7/24) [15, 49] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->5 | hot PRB +7.5% cut, thp -8.5% lost, 2 cmd | accept | hot PRB +5.9% cut, thp +6.3% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 3->5,2->5 | hot PRB +27.9% cut, thp +1.0% lost, 3 cmd | accept | hot PRB +34.0% cut, thp +13.9% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +22.1% cut, thp +14.1% lost, 2 cmd | reject | hot PRB +9.9% cut, thp +2.1% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +75.3% cut, thp +10.3% lost, 2 cmd | reject | hot PRB +63.2% cut, thp +12.4% lost, 1 cmd | reject |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +35.9% cut, thp +4.0% lost, 2 cmd | accept | hot PRB +11.6% cut, thp +0.8% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +35.6% cut, thp +4.1% lost, 2 cmd | accept | hot PRB +11.6% cut, thp +0.8% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +7.5% cut, thp +2.9% lost, 1 cmd | accept | hot PRB +37.4% cut, thp +20.1% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 3->4,2->4 | hot PRB +17.5% cut, thp +13.3% lost, 2 cmd | reject | hot PRB +44.9% cut, thp +30.0% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 6 | qoe_steering | shed 2->3 | hot PRB +13.2% cut, thp +1.6% lost, 2 cmd | accept | hot PRB +19.7% cut, thp +0.1% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->4 | hot PRB +27.4% cut, thp -8.6% lost, 2 cmd | accept | hot PRB +20.8% cut, thp +2.2% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 2->4 | hot PRB +27.4% cut, thp -14.1% lost, 2 cmd | accept | hot PRB +24.3% cut, thp +4.4% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | shed 3->4 | hot PRB +52.7% cut, thp -8.5% lost, 1 cmd | accept | hot PRB +100.0% cut, thp -0.8% lost, 1 cmd | accept |
| 8 | qoe_steering | shed 3->4 | hot PRB +50.8% cut, thp -20.1% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +7.3% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->5 | hot PRB +24.2% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +18.0% cut, thp +6.6% lost, 1 cmd | reject |
| 9 | qoe_steering | shed 2->5 | hot PRB +24.2% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +18.0% cut, thp +6.6% lost, 1 cmd | reject |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -2.9 (min -4.5, max -1.7, n=65); dl_throughput_mbps mean -43.0 (min -50.2, max -35.3, n=65); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=65); prb_used_dl_per_cell mean -2.8 (min -7.9, max -0.8, n=210).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 92%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 92%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 92%, live 83% of 24 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 8
- live traffic_steering: 7
- twin qoe_steering: 8
- twin traffic_steering: 7

Failed runs:

- twin s3 energy_saving: DU logger span 100 ms != 7800 ms
- twin s3 noop: DU logger span 100 ms != 7800 ms
- twin s3 qoe_steering: DU logger span 100 ms != 7800 ms
- twin s3 traffic_steering: DU logger span 100 ms != 7800 ms
