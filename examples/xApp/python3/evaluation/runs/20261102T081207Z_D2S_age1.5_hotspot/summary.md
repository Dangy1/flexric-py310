# Twin-vs-live results - `20261102T081207Z_D2S_age1.5_hotspot`

Runs: 30 (0 failed). Pairs analysed: [1, 2, 3, 4, 5]; excluded: [].

KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).

## KPI fidelity

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | prb_used_dl | 5 | +24.57 | +35.19 | +26.6% | +37.9% | 15.2 | 36% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_throughput_mbps | 5 | +0.66 | +2.19 | +2.6% | +7.5% | 4.9 | 116% (n=5) | 80% | 80% (n=5) |
| traffic_steering | dl_delay_ms | 5 | +4.29 | +1.57 | +170.1% | +99.1% | 91.8 | 112% (n=5) | 100% | 100% (n=5) |
| traffic_steering | dl_buffer_kbytes | 5 | -1308.17 | -1876.98 | -9.4% | -13.2% | 3.9 | 59% (n=5) | 100% | 100% (n=5) |
| traffic_steering | energy_j_per_s | 5 | +579.79 | +830.20 | +11.8% | +16.8% | 6.8 | 36% (n=5) | 80% | 80% (n=5) |
| qoe_steering | prb_used_dl | 5 | +29.29 | +42.71 | +32.2% | +46.0% | 16.2 | 37% (n=5) | 80% | 80% (n=5) |
| qoe_steering | dl_throughput_mbps | 5 | -0.08 | +2.00 | +0.1% | +6.9% | 6.8 | 141% (n=5) | 60% | 60% (n=5) |
| qoe_steering | dl_delay_ms | 5 | +2.12 | +2.99 | +117.7% | +189.9% | 74.5 | 29% (n=5) | 100% | 100% (n=5) |
| qoe_steering | dl_buffer_kbytes | 5 | -1080.13 | -1866.26 | -7.5% | -13.2% | 5.6 | 131% (n=5) | 80% | 80% (n=5) |
| qoe_steering | energy_j_per_s | 5 | +690.97 | +1007.58 | +14.2% | +20.5% | 7.4 | 37% (n=5) | 80% | 80% (n=5) |

## Deploy gate (Validate-2)

Thresholds (declared in the manifest before the runs): energy_saving: energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30; traffic_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5; qoe_steering: hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5. Percentages are relative to the same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.

| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |
|---|---|---|---|---|---|---|---|---|---|---|
| traffic_steering | 5 | 4 | 0 | 1 | 0 | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 80% (4/5) [38, 96] | -- (0/0) | 100% (5/5) [57, 100] |
| qoe_steering | 5 | 4 | 0 | 1 | 0 | 80% (4/5) [38, 96] | 100% (4/4) [51, 100] | 80% (4/5) [38, 96] | -- (0/0) | 100% (5/5) [57, 100] |
| pooled | 10 | 8 | 0 | 2 | 0 | 80% (8/10) [49, 94] | 100% (8/8) [68, 100] | 80% (8/10) [49, 94] | -- (0/0) | 100% (10/10) [72, 100] |

Per pair (twin = predicted, live = measured):

| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |
|---|---|---|---|---|---|---|
| 1 | traffic_steering | shed 2->3 | hot PRB +21.6% cut, thp -0.8% lost, 2 cmd | accept | hot PRB +17.8% cut, thp -9.6% lost, 2 cmd | accept |
| 1 | qoe_steering | shed 2->3 | hot PRB +21.6% cut, thp -0.8% lost, 2 cmd | accept | hot PRB +12.7% cut, thp -9.5% lost, 2 cmd | accept |
| 2 | traffic_steering | shed 2->3 | hot PRB +18.9% cut, thp -10.0% lost, 2 cmd | accept | hot PRB +21.9% cut, thp -10.5% lost, 2 cmd | accept |
| 2 | qoe_steering | shed 2->3,5->3 | hot PRB +36.9% cut, thp +0.9% lost, 3 cmd | accept | hot PRB +36.9% cut, thp -7.3% lost, 3 cmd | accept |
| 3 | traffic_steering | shed 2->3 | hot PRB +20.4% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +20.6% cut, thp -10.1% lost, 2 cmd | accept |
| 3 | qoe_steering | shed 2->3 | hot PRB +20.4% cut, thp -10.1% lost, 2 cmd | accept | hot PRB +20.6% cut, thp -10.1% lost, 2 cmd | accept |
| 4 | traffic_steering | shed 2->3 | hot PRB +21.2% cut, thp +7.2% lost, 2 cmd | reject | hot PRB +20.3% cut, thp -7.5% lost, 2 cmd | accept |
| 4 | qoe_steering | shed 2->3 | hot PRB +18.8% cut, thp +8.8% lost, 2 cmd | reject | hot PRB +20.3% cut, thp -7.5% lost, 2 cmd | accept |
| 5 | traffic_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +61.0% cut, thp +0.2% lost, 2 cmd | accept |
| 5 | qoe_steering | shed 2->3 | hot PRB +63.3% cut, thp +0.8% lost, 2 cmd | accept | hot PRB +60.1% cut, thp +0.2% lost, 2 cmd | accept |

## E2 KPM vs ns-3 trace KPIs

Per-run difference E2 - trace (% of trace): prb_used_dl mean -5.2 (min -6.8, max -3.4, n=30); dl_throughput_mbps mean -32.8 (min -34.4, max -31.3, n=30); dl_buffer_kbytes mean +0.0 (min +0.0, max +0.0, n=30); prb_used_dl_per_cell mean -6.3 (min -9.4, max -1.8, n=120).
Delta sign agreement between sources: predicted_delta/prb_used_dl 100%; predicted_delta/dl_throughput_mbps 100%; predicted_delta/energy_j_per_s 100%; actual_delta/prb_used_dl 100%; actual_delta/dl_throughput_mbps 100%; actual_delta/energy_j_per_s 100%.
Gate verdicts identical under both sources: twin 80%, live 100% of 10 cases.

Runs in which the deployed policy produced RC commands:

- live qoe_steering: 5
- live traffic_steering: 5
- twin qoe_steering: 5
- twin traffic_steering: 5
