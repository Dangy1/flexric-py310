# Twin-vs-live results - `20261102T081207Z_D2S_age0.5_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.94 | +32.23 | +27.0% | +34.7% | 9.4 | 39% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +1.22 | +1.65 | +4.2% | +5.6% | 2.4 | 115% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_delay_ms | 5 | +0.98 | +1.18 | +56.7% | +73.5% | 26.9 | 42% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1265.49 | -1417.69 | -8.9% | -10.0% | 1.1 | 151% (n=5) | 80% | 80% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +588.46 | +760.30 | +12.0% | +15.4% | 4.2 | 39% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +43.93 | +47.76 | +45.5% | +51.4% | 18.9 | 31% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | +1.47 | +1.35 | +5.2% | +4.6% | 4.6 | 107% (n=5) | 80% | 80% (n=5) |
| qoe_steering | dl_delay_ms | 5 | +10.72 | +8.56 | +519.4% | +526.1% | 552.6 | 206% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1551.76 | -1630.03 | -10.7% | -11.5% | 3.8 | 752% (n=5) | 100% | 100% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +1036.36 | +1126.87 | +20.6% | +22.9% | 8.1 | 31% (n=5) | 100% | 100% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 4 | 0 | 0 | 1 | 100% (5/5) [57, 100] | 100% (4/4) [51, 100] | 100% (4/4) [51, 100] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |
| pooled | 10 | 9 | 0 | 0 | 1 | 100% (10/10) [72, 100] | 100% (9/9) [70, 100] | 100% (9/9) [70, 100] | 100% (1/1) [21, 100] | 90% (9/10) [60, 98] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.6% cut, thp -0.8% lost, 2 cmd | accept | hot PRB +17.8% cut, thp -9.6% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB -11.7% cut, thp -23.6% lost, 2 cmd | reject | hot PRB -11.6% cut, thp -10.9% lost, 2 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +20.8% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +16.4% cut, thp -9.6% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +17.2% cut, thp -10.2% lost, 2 cmd | accept | hot PRB +6.5% cut, thp -9.0% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3,5->3 | hot PRB +35.0% cut, thp +2.5% lost, 3 cmd | accept | hot PRB +30.6% cut, thp -6.4% lost, 3 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +49.1% cut, thp -0.5% lost, 2 cmd | accept | hot PRB +60.1% cut, thp +0.6% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 5->3,2->3 | hot PRB +49.4% cut, thp +4.0% lost, 3 cmd | accept | hot PRB +59.4% cut, thp +4.3% lost, 3 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +60.1% cut, thp +0.2% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +60.1% cut, thp +0.2% lost, 2 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.2 (min -6.8, max -3.2, n=30); dl_throughput_mbps mean -33.3 (min -36.7, max -31.3, n=30); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=30); prb_used_dl_per_cell mean -6.3 (min -9.4, max -1.8, n=120).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 90%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 80%, live 90% of 10 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
