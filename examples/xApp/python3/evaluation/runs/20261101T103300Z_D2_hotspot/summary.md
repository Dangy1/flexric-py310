# Twin-vs-live results - `20261101T103300Z_D2_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +22.35 | +42.19 | +22.2% | +45.5% | 24.7 | 39% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | -0.44 | +2.27 | -0.9% | +7.8% | 9.3 | 87% (n=5) | 60% | 60% (n=5) |
| traffic_steering | dl_delay_ms | 5 | +0.67 | +32.23 | +36.9% | +2065.4% | 2039.4 | 64% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -197.01 | -1964.93 | -0.4% | -13.9% | 13.4 | 78% (n=5) | 40% | 40% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +527.24 | +995.33 | +10.2% | +20.2% | 10.6 | 39% (n=5) | 100% | 100% (n=5) |
| qoe_steering | prb_used_dl | 5 | +34.25 | +63.01 | +36.3% | +67.9% | 33.3 | 43% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | -0.87 | +1.81 | -2.5% | +6.2% | 10.0 | 240% (n=5) | 60% | 60% (n=5) |
| qoe_steering | dl_delay_ms | 5 | +10.09 | +95.28 | +611.6% | +6099.8% | 5722.9 | 65% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -198.77 | -1975.80 | -0.8% | -13.9% | 13.6 | 86% (n=5) | 40% | 40% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +808.17 | +1482.75 | +16.3% | +30.1% | 14.6 | 43% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 4 | 0 | 0 | 1 | 100% (5/5) [57, 100] | 100% (4/4) [51, 100] | 100% (4/4) [51, 100] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |
| qoe_steering | 5 | 3 | 1 | 1 | 0 | 60% (3/5) [23, 88] | 75% (3/4) [30, 95] | 75% (3/4) [30, 95] | 0% (0/1) [0, 79] | 80% (4/5) [38, 96] |
| pooled | 10 | 7 | 1 | 1 | 1 | 80% (8/10) [49, 94] | 88% (7/8) [53, 98] | 88% (7/8) [53, 98] | 50% (1/2) [9, 91] | 80% (8/10) [49, 94] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +61.2% cut, thp +0.7% lost, 2 cmd | accept | hot PRB +15.5% cut, thp +2.4% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +61.2% cut, thp +0.7% lost, 2 cmd | accept | hot PRB -14.8% cut, thp -18.8% lost, 2 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +18.9% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3,5->3 | hot PRB +39.5% cut, thp -4.0% lost, 3 cmd | accept | hot PRB +38.6% cut, thp -0.7% lost, 3 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +60.5% cut, thp +0.2% lost, 2 cmd | accept | hot PRB +14.0% cut, thp -9.5% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,5->3 | hot PRB +60.7% cut, thp +4.2% lost, 3 cmd | accept | hot PRB +38.0% cut, thp +0.9% lost, 3 cmd | accept |
| 4 | traffic_steering | shed 2->5 | hot PRB +44.2% cut, thp +13.0% lost, 2 cmd | reject | hot PRB -5.4% cut, thp -21.8% lost, 2 cmd | reject |
| 4 | qoe_steering | shed 3->5,2->5 | hot PRB +66.1% cut, thp +10.9% lost, 3 cmd | reject | hot PRB +26.1% cut, thp -12.8% lost, 3 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +57.3% cut, thp +0.4% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +56.0% cut, thp +0.4% lost, 2 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.1 (min -6.8, max -3.3, n=30); dl_throughput_mbps mean -33.2 (min -38.3, max -31.2, n=30); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=30); prb_used_dl_per_cell mean -6.3 (min -9.4, max -1.8, n=119).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 100%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 90%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 90%, live 100% of 10 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
