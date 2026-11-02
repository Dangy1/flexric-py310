# Twin-vs-live results - `20261102T081207Z_D2S_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +27.16 | +35.45 | +28.2% | +38.2% | 12.8 | 33% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.66 | +1.75 | +2.3% | +6.0% | 3.9 | 199% (n=5) | 60% | 60% (n=5) |
| traffic_steering | dl_delay_ms | 5 | +1.19 | +1.37 | +64.4% | +86.0% | 38.0 | 41% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1368.56 | -1751.13 | -10.4% | -12.3% | 2.0 | 128929% (n=5) | 100% | 100% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +640.90 | +836.34 | +12.8% | +17.0% | 5.4 | 33% (n=5) | 100% | 100% (n=5) |
| qoe_steering | prb_used_dl | 5 | +45.96 | +35.76 | +48.6% | +38.4% | 23.3 | 101% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | +0.23 | -0.61 | +1.0% | -2.1% | 5.0 | 147% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_delay_ms | 5 | +9.57 | +4.33 | +525.2% | +263.1% | 262.1 | 206% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1200.07 | -934.76 | -8.7% | -6.6% | 3.4 | 115% (n=5) | 80% | 80% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +1084.30 | +843.76 | +21.8% | +17.1% | 10.4 | 101% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 4 | 0 | 1 | 0 | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 80% (4/5) [38, 96] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 2 | 1 | 1 | 1 | 60% (3/5) [23, 88] | 67% (2/3) [21, 94] | 67% (2/3) [21, 94] | 50% (1/2) [9, 91] | 60% (3/5) [23, 88] |
| pooled | 10 | 6 | 1 | 2 | 1 | 70% (7/10) [40, 89] | 86% (6/7) [49, 97] | 75% (6/8) [41, 93] | 50% (1/2) [9, 91] | 80% (8/10) [49, 94] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +23.8% cut, thp +0.4% lost, 2 cmd | accept | hot PRB +15.5% cut, thp -0.7% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +18.2% cut, thp -9.2% lost, 2 cmd | accept | hot PRB +18.2% cut, thp -1.7% lost, 2 cmd | accept |
| 2 | traffic_steering | shed 2->3 | hot PRB +16.4% cut, thp -9.6% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +20.8% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +20.6% cut, thp -10.4% lost, 2 cmd | accept | hot PRB +19.4% cut, thp -9.8% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,4->3 | hot PRB +37.1% cut, thp +1.9% lost, 3 cmd | accept | hot PRB +27.5% cut, thp +14.6% lost, 3 cmd | reject |
| 4 | traffic_steering | shed 2->3 | hot PRB +14.6% cut, thp +0.9% lost, 2 cmd | accept | hot PRB +14.7% cut, thp -10.0% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3,5->3 | hot PRB +26.2% cut, thp +6.1% lost, 3 cmd | reject | hot PRB +26.5% cut, thp +2.7% lost, 3 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +54.6% cut, thp +7.2% lost, 2 cmd | reject | hot PRB +57.5% cut, thp +0.9% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3,4->3 | hot PRB +59.6% cut, thp +6.1% lost, 3 cmd | reject | hot PRB +56.9% cut, thp +5.1% lost, 3 cmd | reject |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.1 (min -6.8, max -3.2, n=30); dl_throughput_mbps mean -32.9 (min -36.1, max -31.2, n=30); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=30); prb_used_dl_per_cell mean -6.3 (min -9.4, max -1.7, n=120).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 90%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 90%, live 90% of 10 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
