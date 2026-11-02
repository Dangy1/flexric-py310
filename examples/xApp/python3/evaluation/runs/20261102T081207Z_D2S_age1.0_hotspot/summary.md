# Twin-vs-live results - `20261102T081207Z_D2S_age1.0_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.72 | +29.82 | +26.7% | +32.1% | 9.2 | 39% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +1.21 | +1.71 | +4.1% | +5.9% | 2.2 | 139% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_delay_ms | 5 | +0.99 | +1.06 | +57.3% | +65.9% | 22.9 | 45% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1265.60 | -1417.77 | -8.9% | -10.0% | 1.1 | 309% (n=5) | 80% | 80% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +583.21 | +703.45 | +11.9% | +14.3% | 4.1 | 39% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +29.01 | +30.13 | +31.5% | +32.3% | 7.8 | 42% (n=4) | 80% | 75% (n=4) |
| qoe_steering | dl_throughput_mbps | 5 | +0.90 | +0.90 | +3.1% | +3.1% | 0.6 | 49% (n=4) | 80% | 75% (n=4) |
| qoe_steering | dl_delay_ms | 5 | +1.75 | +1.65 | +104.3% | +100.9% | 23.2 | 32% (n=4) | 100% | 100% (n=4) |
| qoe_steering | dl_buffer_kbytes | 5 | -938.82 | -940.02 | -6.6% | -6.6% | 0.0 | 135% (n=4) | 80% | 75% (n=4) |
| qoe_steering | energy_j_per_s | 5 | +684.42 | +710.90 | +14.0% | +14.4% | 3.5 | 42% (n=4) | 80% | 75% (n=4) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 5 | 0 | 0 | 0 | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | 100% (5/5) [57, 100] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 3 | 0 | 1 | 1 | 80% (4/5) [38, 96] | 100% (3/3) [44, 100] | 75% (3/4) [30, 95] | 100% (1/1) [21, 100] | 80% (4/5) [38, 96] |
| pooled | 10 | 8 | 0 | 1 | 1 | 90% (9/10) [60, 98] | 100% (8/8) [68, 100] | 89% (8/9) [57, 98] | 100% (1/1) [21, 100] | 90% (9/10) [60, 98] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.6% cut, thp -0.8% lost, 2 cmd | accept | hot PRB +12.7% cut, thp -9.5% lost, 2 cmd | accept |
| 1 | qoe_steering | none | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject | hot PRB --% cut, thp +0.0% lost, 0 cmd | reject |
| 2 | traffic_steering | shed 2->3 | hot PRB +18.9% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +21.3% cut, thp -10.4% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3 | hot PRB +18.9% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +21.9% cut, thp -10.5% lost, 2 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +20.4% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +20.6% cut, thp -10.1% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3 | hot PRB +20.4% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +20.6% cut, thp -10.1% lost, 2 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +48.7% cut, thp -0.5% lost, 2 cmd | accept | hot PRB +60.1% cut, thp +0.6% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3 | hot PRB +49.1% cut, thp -0.5% lost, 2 cmd | accept | hot PRB +58.7% cut, thp +0.9% lost, 2 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +60.2% cut, thp +0.2% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3,4->3 | hot PRB +58.6% cut, thp +5.3% lost, 3 cmd | reject | hot PRB +59.7% cut, thp +4.3% lost, 3 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.3 (min -6.8, max -3.5, n=30); dl_throughput_mbps mean -33.0 (min -35.9, max -31.3, n=30); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=30); prb_used_dl_per_cell mean -6.4 (min -9.4, max -2.2, n=120).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 80%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 100%, live 90% of 10 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 4
- live traffic_steering: 5
- twin qoe_steering: 4
- twin traffic_steering: 5
