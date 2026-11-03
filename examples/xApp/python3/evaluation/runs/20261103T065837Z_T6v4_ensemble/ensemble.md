# Ensemble twin and uncertainty-aware gate (T6v4)

Decisions: 23 distinct; K = 3 twin seeds each.

| Group | n | live accepts | rule | agreement | 95% CI | accepted | false accepts | missed accepts |
|---|---|---|---|---|---|---|---|---|
| steering | 19 | 16 | single | 14/19 | [51.2, 88.2] | 13 | 1 | 4 |
| steering | 19 | 16 | mean | 15/19 | [56.7, 91.5] | 14 | 1 | 3 |
| steering | 19 | 16 | margin | 12/19 | [41.0, 80.9] | 9 | 0 | 7 |
| energy | 4 | 4 | single | 4/4 | [51.0, 100.0] | 4 | 0 | 0 |
| energy | 4 | 4 | mean | 4/4 | [51.0, 100.0] | 4 | 0 | 0 |
| energy | 4 | 4 | margin | 4/4 | [51.0, 100.0] | 4 | 0 | 0 |
| all | 23 | 20 | single | 18/23 | [58.1, 90.3] | 17 | 1 | 4 |
| all | 23 | 20 | mean | 19/23 | [62.9, 93.0] | 18 | 1 | 3 |
| all | 23 | 20 | margin | 16/23 | [49.1, 84.4] | 13 | 0 | 7 |

| id | layout | pair | workflow | commands | twin members (gate quantities) | live | live | single | mean | margin |
|---|---|---|---|---|---|---|---|---|---|---|
| d00 | hotspot | 1 | qoe_steering | HO 1 3 HO 4 3 | hot_prb_reduction_pct: 18.2, 20.9, 24.8; throughput_loss_pct: -9.2, 1.0, -0.4 | hot_prb_reduction_pct: 18.2; throughput_loss_pct: -1.7 | accept | True | True | True |
| d01 | hotspot | 2 | qoe_steering | HO 1 3 HO 9 3 | hot_prb_reduction_pct: 20.8, 15.1, 24.1; throughput_loss_pct: -10.1, 5.7, -9.9 | hot_prb_reduction_pct: 21.3; throughput_loss_pct: -10.4 | accept | True | True | True |
| d02 | hotspot | 3 | qoe_steering | HO 11 3 HO 2 3 HO 9 3 | hot_prb_reduction_pct: 37.1, 39.9, 33.0; throughput_loss_pct: 1.9, -4.1, 10.4 | hot_prb_reduction_pct: 27.5; throughput_loss_pct: 14.6 | reject | True | True | False |
| d03 | hotspot | 4 | qoe_steering | HO 13 3 HO 2 3 HO 9 3 | hot_prb_reduction_pct: 26.2, 34.6, 33.6; throughput_loss_pct: 6.1, 3.7, -6.5 | hot_prb_reduction_pct: 26.5; throughput_loss_pct: 2.7 | accept | False | True | False |
| d04 | hotspot | 5 | qoe_steering | HO 1 3 HO 12 3 HO 3 3 | hot_prb_reduction_pct: 59.6, 58.8, 40.7; throughput_loss_pct: 6.1, 14.7, 26.8 | hot_prb_reduction_pct: 56.9; throughput_loss_pct: 5.1 | reject | False | False | False |
| d05 | hotspot | 3 | traffic_steering | HO 2 3 HO 9 3 | hot_prb_reduction_pct: 20.6, 16.7, 17.0; throughput_loss_pct: -10.4, -6.2, -10.3 | hot_prb_reduction_pct: 19.4; throughput_loss_pct: -9.8 | accept | True | True | True |
| d06 | hotspot | 4 | traffic_steering | HO 2 3 HO 9 3 | hot_prb_reduction_pct: 14.6, 23.8, 18.6; throughput_loss_pct: 0.9, -10.1, -9.6 | hot_prb_reduction_pct: 14.7; throughput_loss_pct: -10.0 | accept | True | True | True |
| d07 | hotspot | 5 | traffic_steering | HO 1 3 HO 3 3 | hot_prb_reduction_pct: 54.6, 63.4, 29.3; throughput_loss_pct: 7.2, 0.8, 8.9 | hot_prb_reduction_pct: 57.5; throughput_loss_pct: 0.9 | accept | False | False | False |
| d08 | hotspot | 1 | qoe_steering | HO 7 3 HO 9 3 | hot_prb_reduction_pct: -11.7, 21.2, -17.6; throughput_loss_pct: -23.6, -10.3, -22.4 | hot_prb_reduction_pct: -11.6; throughput_loss_pct: -10.9 | reject | False | False | False |
| d09 | hotspot | 3 | qoe_steering | HO 13 3 HO 3 3 HO 9 3 | hot_prb_reduction_pct: 35.0, 29.8, 30.6; throughput_loss_pct: 2.5, -4.1, -5.8 | hot_prb_reduction_pct: 30.6; throughput_loss_pct: -6.4 | accept | True | True | True |
| d10 | hotspot | 4 | qoe_steering | HO 1 3 HO 13 3 HO 2 3 | hot_prb_reduction_pct: 49.4, 61.8, 59.6; throughput_loss_pct: 4.0, 5.4, 4.9 | hot_prb_reduction_pct: 59.4; throughput_loss_pct: 4.3 | accept | True | True | False |
| d11 | hotspot | 5 | qoe_steering | HO 1 3 HO 2 3 | hot_prb_reduction_pct: 63.3, 60.2, 42.2; throughput_loss_pct: 0.8, 3.6, 17.1 | hot_prb_reduction_pct: 60.1; throughput_loss_pct: 0.2 | accept | True | False | False |
| d12 | hotspot | 1 | traffic_steering | HO 1 3 HO 9 3 | hot_prb_reduction_pct: 21.6, 17.3, 24.2; throughput_loss_pct: -0.8, -10.2, -10.0 | hot_prb_reduction_pct: 17.8; throughput_loss_pct: -9.6 | accept | True | True | True |
| d13 | hotspot | 3 | traffic_steering | HO 3 3 HO 9 3 | hot_prb_reduction_pct: 17.2, 16.6, 9.5; throughput_loss_pct: -10.2, -9.4, -9.4 | hot_prb_reduction_pct: 6.5; throughput_loss_pct: -9.0 | accept | True | True | True |
| d14 | hotspot | 4 | traffic_steering | HO 1 3 HO 2 3 | hot_prb_reduction_pct: 49.1, 63.2, 57.1; throughput_loss_pct: -0.5, 0.5, 0.9 | hot_prb_reduction_pct: 60.1; throughput_loss_pct: 0.6 | accept | True | True | True |
| d15 | hotspot | 3 | qoe_steering | HO 1 3 HO 9 3 | hot_prb_reduction_pct: 20.4, 23.8, 18.2; throughput_loss_pct: -10.1, -9.7, -10.1 | hot_prb_reduction_pct: 20.6; throughput_loss_pct: -10.1 | accept | True | True | True |
| d16 | hotspot | 5 | qoe_steering | HO 1 3 HO 11 3 HO 2 3 | hot_prb_reduction_pct: 58.6, 61.1, 44.9; throughput_loss_pct: 5.3, 5.1, 25.4 | hot_prb_reduction_pct: 59.7; throughput_loss_pct: 4.3 | accept | False | False | False |
| d17 | hotspot | 2 | qoe_steering | HO 1 3 HO 13 3 HO 9 3 | hot_prb_reduction_pct: 36.9, 26.3, 38.9; throughput_loss_pct: 0.9, 16.3, -8.0 | hot_prb_reduction_pct: 36.9; throughput_loss_pct: -7.3 | accept | True | True | False |
| d18 | hotspot | 4 | qoe_steering | HO 2 3 HO 6 3 | hot_prb_reduction_pct: 18.8, 27.5, 20.2; throughput_loss_pct: 8.8, -9.7, -8.7 | hot_prb_reduction_pct: 20.3; throughput_loss_pct: -7.5 | accept | False | True | False |
| d19 | night_energy | 2 | energy_saving | HO 7 2 HO 8 2 OFF 4 OFF 5 | energy_saving_pct: 41.1, 41.6, 41.7; remaining_prb_increase_pct: -6.9, -9.3, -9.5 | energy_saving_pct: 42.1; remaining_prb_increase_pct: -11.7 | accept | True | True | True |
| d20 | night_energy | 3 | energy_saving | HO 7 2 HO 8 2 OFF 4 OFF 5 | energy_saving_pct: 41.8, 41.2, 42.1; remaining_prb_increase_pct: -10.3, -7.4, -11.6 | energy_saving_pct: 40.7; remaining_prb_increase_pct: -4.7 | accept | True | True | True |
| d21 | night_energy | 4 | energy_saving | HO 7 2 HO 8 2 OFF 4 OFF 5 | energy_saving_pct: 41.6, 40.7, 41.2; remaining_prb_increase_pct: -9.0, -4.9, -7.2 | energy_saving_pct: 41.1; remaining_prb_increase_pct: -6.6 | accept | True | True | True |
| d22 | night_energy | 5 | energy_saving | HO 7 2 HO 8 2 OFF 4 OFF 5 | energy_saving_pct: 41.4, 41.9, 41.9; remaining_prb_increase_pct: -8.1, -10.6, -10.6 | energy_saving_pct: 41.8; remaining_prb_increase_pct: -10.1 | accept | True | True | True |
