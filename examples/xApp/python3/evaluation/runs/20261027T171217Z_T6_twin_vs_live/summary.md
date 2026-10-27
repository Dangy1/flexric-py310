# Twin-vs-live results - `20261027T171217Z_T6_twin_vs_live`

Runs: 64 (0 failed). Pairs analysed per workflow/KPI in the table.

| Workflow | KPI | Pairs | Mean predicted change | Mean measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement |
|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | +34.7% | -17.1% | 60.6 | 38712% (n=8) | 25% |
| energy_saving | dl_throughput_mbps | 8 | -2.2% | -15.7% | 13.5 | 112691% (n=8) | 50% |
| energy_saving | dl_buffer_kbytes | 8 | +73.5% | +258574.2% | 258500.8 | 95% (n=8) | 50% |
| energy_saving | energy_j_per_s | 8 | -21.4% | -25.7% | 10.5 | 40% (n=7) | 88% |
| traffic_steering | prb_used_dl | 8 | +95.1% | +10.7% | 84.4 | 349% (n=8) | 88% |
| traffic_steering | dl_throughput_mbps | 8 | -4.5% | -3.2% | 8.5 | 253% (n=8) | 62% |
| traffic_steering | dl_buffer_kbytes | 8 | +15376.7% | +3215.3% | 18278.1 | 67404% (n=8) | 75% |
| traffic_steering | energy_j_per_s | 8 | +16.6% | +7.5% | 15.5 | 672% (n=8) | 88% |
| qoe_steering | prb_used_dl | 8 | +34.4% | -14.0% | 49.3 | 144% (n=8) | 38% |
| qoe_steering | dl_throughput_mbps | 8 | +0.4% | -8.3% | 10.4 | 94% (n=8) | 62% |
| qoe_steering | dl_buffer_kbytes | 8 | +558505.8% | +51838.7% | 583644.0 | 104% (n=8) | 25% |
| qoe_steering | energy_j_per_s | 8 | +3.2% | -8.7% | 13.5 | 134% (n=8) | 12% |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 7
- live qoe_steering: 8
- live traffic_steering: 8
- twin energy_saving: 7
- twin qoe_steering: 5
- twin traffic_steering: 7
