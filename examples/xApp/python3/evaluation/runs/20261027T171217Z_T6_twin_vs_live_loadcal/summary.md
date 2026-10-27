# Twin-vs-live results - `20261027T171217Z_T6_twin_vs_live_loadcal`

Runs: 72 (4 failed). Pairs analysed per workflow/KPI in the table.

| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement |
|---|---|---|---|---|---|---|---|---|---|
| energy_saving | prb_used_dl | 8 | -0.02 | -17.76 | -0.0% | -9.0% | 9.6 | 123% (n=8) | 62% |
| energy_saving | dl_throughput_mbps | 8 | -0.00 | -1.45 | -0.0% | -7.8% | 7.8 | 116% (n=8) | 38% |
| energy_saving | dl_buffer_kbytes | 8 | +1.10 | +712.15 | +73.2% | +53542.1% | 53629.5 | 106% (n=8) | 50% |
| energy_saving | energy_j_per_s | 8 | -582.52 | -1005.49 | -11.9% | -13.9% | 4.1 | 37% (n=5) | 100% |
| traffic_steering | prb_used_dl | 8 | +17.75 | +20.38 | +19.5% | +11.2% | 31.7 | 262% (n=8) | 75% |
| traffic_steering | dl_throughput_mbps | 8 | -1.03 | -0.86 | -6.3% | -4.9% | 8.4 | 189% (n=8) | 62% |
| traffic_steering | dl_buffer_kbytes | 8 | +236.10 | +515.30 | +24752.9% | +62029.6% | 86642.5 | 10532% (n=8) | 50% |
| traffic_steering | energy_j_per_s | 8 | +810.66 | +481.41 | +15.2% | +6.7% | 14.5 | 394% (n=8) | 88% |
| qoe_steering | prb_used_dl | 8 | +24.11 | +3.35 | +26.1% | +3.2% | 33.1 | 879% (n=8) | 62% |
| qoe_steering | dl_throughput_mbps | 8 | -0.82 | -1.37 | -3.9% | -7.4% | 11.5 | 63512% (n=8) | 50% |
| qoe_steering | dl_buffer_kbytes | 8 | -126.96 | +766.11 | +20723.3% | +26498.7% | 46925.5 | 44985% (n=8) | 12% |
| qoe_steering | energy_j_per_s | 8 | +611.47 | +67.00 | +11.1% | +1.4% | 15.6 | 652% (n=7) | 25% |

Runs in which the deployed policy produced RC commands:

- live energy_saving: 6
- live qoe_steering: 8
- live traffic_steering: 9
- twin energy_saving: 5
- twin qoe_steering: 5
- twin traffic_steering: 8

Failed runs:

- twin s3 noop: None
- twin s3 traffic_steering: None
- twin s3 energy_saving: None
- twin s3 qoe_steering: None
