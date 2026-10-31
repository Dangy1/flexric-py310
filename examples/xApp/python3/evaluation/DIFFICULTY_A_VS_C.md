# Difficulty: Batch A vs Batch C

A run `20261028T190000Z_A_final_gptoss120b_spark1_seededfix`, C run `20261031T051600Z_C_final_merged_gptoss120b_spark1` (1980 records).

| Batch / split | Intents | Words | Label chain len | Required apps | No control app needed | Control apps named in sentence | Template-solvable |
|---|---|---|---|---|---|---|---|
| A known | 11 | 9.5 | 2.91 | 2.18 | 0 | 8/16 (50.0%) | 11 |
| A open_world | 39 | 11.2 | 2.82 | 1.82 | 9 | 28/37 (75.7%) | 12 |
| A all | 50 | 10.8 | 2.84 | 1.9 | 9 | 36/53 (67.9%) | 23 |
| C known | 30 | 25.3 | 2.67 | 2.0 | 0 | 31/40 (77.5%) | 30 |
| C open_world | 30 | 24.4 | 2.23 | 1.4 | 11 | 19/20 (95.0%) | 8 |
| C all | 60 | 24.9 | 2.45 | 1.7 | 11 | 50/60 (83.3%) | 38 |

C's own `template-solvable-under-rule` tag: 8 intents.

Rule accuracy (%) per chain shape (required apps), same shape in A and C:

| Shape | Batch | Intents | manual_rule | single_xapp | llm_blind | llm_only | agentcard_no_repair | langgraph_agentcard | appweaver_tpl | appweaver_mem | appweaver_guided | appweaver_v2 | appweaver_mem2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KPM+SLICE | A | 11 | 18.2 | 0.0 | 0.0 | 14.5 | 87.3 | 85.5 | -- | -- | -- | -- | -- |
| KPM+SLICE | C | 15 | 0.0 | 0.0 | 0.0 | 48.9 | 100.0 | 100.0 | 100.0 | 100.0 | 53.3 | 60.0 | 100.0 |
| KPM+SLICE+TC | A | 12 | 83.3 | 0.0 | 0.0 | 91.7 | 50.0 | 50.0 | -- | -- | -- | -- | -- |
| KPM+SLICE+TC | C | 10 | 80.0 | 0.0 | 0.0 | 100.0 | 76.7 | 76.7 | 90.0 | 90.0 | 70.0 | 73.3 | 90.0 |
| TC | A | 8 | 75.0 | 75.0 | 0.0 | 60.0 | 92.5 | 100.0 | -- | -- | -- | -- | -- |
| TC | C | 13 | 23.1 | 23.1 | 0.0 | 74.4 | 100.0 | 100.0 | 100.0 | 100.0 | 92.3 | 92.3 | 100.0 |
| KPM | A | 9 | 0.0 | 66.7 | 0.0 | 0.0 | 46.7 | 51.1 | -- | -- | -- | -- | -- |
| KPM | C | 11 | 0.0 | 90.9 | 0.0 | 0.0 | 87.9 | 87.9 | 87.9 | 87.9 | 93.9 | 97.0 | 87.9 |
| KPM+TC | A | 10 | 0.0 | 0.0 | 0.0 | 0.0 | 80.0 | 72.0 | -- | -- | -- | -- | -- |
| KPM+TC | C | 6 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| SLICE | C | 4 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 66.7 | 100.0 | 100.0 |
| SLICE+TC | C | 1 | 100.0 | 0.0 | 33.3 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
