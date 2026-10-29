# Twin-vs-live results - `20261028T173841Z_T6v3_twin_vs_live_loadcal`

Runs: 69 (4 failed). Pairs analysed: [1, 2, 4, 5, 6, 7, 8, 9]; excluded: [3].

KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_throughput_mbps | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | dl_buffer_kbytes | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| energy_saving | energy_j_per_s | 8 | +0.00 | +0.00 | +0.0% | +0.0% | 0.0 | -- | 100% | -- |
| traffic_steering | prb_used_dl | 8 | +35.14 | +10.11 | +42.3% | +7.4% | 39.3 | 251% (n=7) | 100% | 100% (n=7) |
| traffic_steering | dl_throughput_mbps | 8 | +0.03 | -0.68 | +0.4% | -3.9% | 6.3 | 160% (n=7) | 38% | 29% (n=7) |
| traffic_steering | dl_buffer_kbytes | 8 | -704.80 | +309.33 | +27443.8% | +43552.6% | 48885.1 | 28764% (n=7) | 38% | 29% (n=7) |
| traffic_steering | energy_j_per_s | 8 | +826.45 | +233.69 | +16.5% | +3.8% | 14.0 | 253% (n=7) | 100% | 100% (n=7) |
| qoe_steering | prb_used_dl | 8 | +37.91 | -14.58 | +46.8% | -9.8% | 56.6 | 583% (n=8) | 62% | 62% (n=8) |
| qoe_steering | dl_throughput_mbps | 8 | -0.55 | -1.17 | -2.3% | -6.6% | 6.0 | 139% (n=8) | 62% | 62% (n=8) |
| qoe_steering | dl_buffer_kbytes | 8 | -668.77 | +1101.03 | +88246.8% | +63782.5% | 85192.0 | 5303% (n=8) | 50% | 50% (n=8) |
| qoe_steering | energy_j_per_s | 8 | +888.89 | -357.40 | +18.2% | -5.5% | 23.6 | 635% (n=8) | 62% | 62% (n=8) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_saving | 8 | 0 | 0 | 0 | 8 | 100% (8/8) [68, 100] | -- (0/0) | -- (0/0) | 100% (8/8) [68, 100] | 0% (0/8) [0, 32] |
| traffic_steering | 8 | 2 | 3 | 1 | 2 | 50% (4/8) [22, 78] | 40% (2/5) [12, 77] | 67% (2/3) [21, 94] | 40% (2/5) [12, 77] | 38% (3/8) [14, 69] |
| qoe_steering | 8 | 4 | 1 | 0 | 3 | 88% (7/8) [53, 98] | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 75% (3/4) [30, 95] | 50% (4/8) [22, 78] |
| pooled | 24 | 6 | 4 | 1 | 13 | 79% (19/24) [60, 91] | 60% (6/10) [31, 83] | 86% (6/7) [49, 97] | 76% (13/17) [53, 90] | 29% (7/24) [15, 49] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 1 | traffic_steering | shed 2->5 | hot PRB +6.8% cut, thp -2.9% lost, 2 cmd | accept | hot PRB +5.2% cut, thp +7.6% lost, 1 cmd | reject |
| 1 | qoe_steering | shed 3->5,2->5 | hot PRB +27.6% cut, thp +9.0% lost, 3 cmd | reject | hot PRB +34.2% cut, thp +12.9% lost, 2 cmd | reject |
| 2 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +21.5% cut, thp +8.6% lost, 2 cmd | reject | hot PRB +9.9% cut, thp +6.4% lost, 2 cmd | reject |
| 2 | qoe_steering | shed 4->3,5->3 | hot PRB +75.5% cut, thp +10.6% lost, 2 cmd | reject | hot PRB +63.8% cut, thp +6.6% lost, 1 cmd | reject |
| 4 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 4 | traffic_steering | shed 2->5 | hot PRB +35.6% cut, thp +6.8% lost, 2 cmd | reject | hot PRB +11.3% cut, thp +2.7% lost, 1 cmd | accept |
| 4 | qoe_steering | shed 2->5 | hot PRB +35.3% cut, thp +4.6% lost, 2 cmd | accept | hot PRB +11.3% cut, thp +2.7% lost, 1 cmd | accept |
| 5 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 5 | traffic_steering | shed 2->4 | hot PRB +6.5% cut, thp -3.5% lost, 1 cmd | accept | hot PRB +37.1% cut, thp +6.6% lost, 2 cmd | reject |
| 5 | qoe_steering | shed 3->4,2->4 | hot PRB +16.8% cut, thp +14.5% lost, 2 cmd | reject | hot PRB +45.0% cut, thp +17.6% lost, 3 cmd | reject |
| 6 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 6 | traffic_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 6 | qoe_steering | shed 2->3 | hot PRB +13.0% cut, thp +2.2% lost, 2 cmd | accept | hot PRB +19.7% cut, thp +1.3% lost, 1 cmd | accept |
| 7 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 7 | traffic_steering | shed 2->4 | hot PRB +26.8% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +20.3% cut, thp -0.9% lost, 1 cmd | accept |
| 7 | qoe_steering | shed 2->4 | hot PRB +26.3% cut, thp -4.1% lost, 2 cmd | accept | hot PRB +23.6% cut, thp +0.9% lost, 1 cmd | accept |
| 8 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 8 | traffic_steering | shed 3->4 | hot PRB +53.2% cut, thp -3.0% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +5.4% lost, 1 cmd | reject |
| 8 | qoe_steering | shed 3->4 | hot PRB +51.3% cut, thp -8.3% lost, 1 cmd | accept | hot PRB +100.0% cut, thp +7.6% lost, 1 cmd | reject |
| 9 | energy_saving | sleep [] | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject | E +0.0% saved, PRB(rem) +0.0%, 0 cmd | reject |
| 9 | traffic_steering | shed 2->5 | hot PRB +23.5% cut, thp -9.9% lost, 2 cmd | accept | hot PRB +18.0% cut, thp +3.4% lost, 1 cmd | accept |
| 9 | qoe_steering | shed 2->5 | hot PRB +23.5% cut, thp -9.9% lost, 2 cmd | accept | hot PRB +18.0% cut, thp +3.4% lost, 1 cmd | accept |

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
