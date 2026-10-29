# Difficulty: Batch A vs Batch C

A run `20261028T190000Z_A_final_gptoss120b_spark1_seededfix`, C run `20261029T075856_628139Z_C_final_gptoss120b_spark1` (1197 records).

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

| Shape | Batch | Intents | manual_rule | single_xapp | llm_blind | llm_only | agentcard_no_repair | langgraph_agentcard | appweaver_tpl | appweaver_mem |
|---|---|---|---|---|---|---|---|---|---|---|
| KPM+SLICE | A | 11 | 18.2 | 0.0 | 0.0 | 14.5 | 87.3 | 85.5 | -- | -- |
| KPM+SLICE | C | 15 | 0.0 | 0.0 | 0.0 | 55.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| KPM+SLICE+TC | A | 12 | 83.3 | 0.0 | 0.0 | 91.7 | 50.0 | 50.0 | -- | -- |
| KPM+SLICE+TC | C | 10 | 80.0 | 0.0 | 0.0 | 100.0 | 76.7 | 76.7 | 90.0 | 90.0 |
| TC | A | 8 | 75.0 | 75.0 | 0.0 | 60.0 | 92.5 | 100.0 | -- | -- |
| TC | C | 13 | 25.0 | 25.0 | 0.0 | 80.6 | 100.0 | 100.0 | 100.0 | 100.0 |
| KPM | A | 9 | 0.0 | 66.7 | 0.0 | 0.0 | 46.7 | 51.1 | -- | -- |
| KPM | C | 11 | 0.0 | 90.9 | 0.0 | 0.0 | 90.9 | 86.4 | 86.4 | 90.9 |
| KPM+TC | A | 10 | 0.0 | 0.0 | 0.0 | 0.0 | 80.0 | 72.0 | -- | -- |
| KPM+TC | C | 6 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| SLICE | C | 4 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| SLICE+TC | C | 1 | 100.0 | 0.0 | 50.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## Reading (2026-10-29, C part 1 partial: 1196 of 1440 records)

**C is easier than A, for four measurable reasons, so C must not be presented as a held-out headline without this caveat.**

1. **The sentences say more.** C intents average 25 words vs 11 in A, and name the domain of 83 % of their required
   control apps (open-world 95 %) vs 68 % in A (open-world 76 %). The planner is told which controller to use more often.
2. **Shorter, simpler label chains.** Mean label chain 2.45 vs 2.84 apps; required apps 1.7 vs 1.9. C open-world needs
   only 1.4 required apps and 11 of its 30 intents need no control app at all (A open-world: 9 of 39).
3. **Template share.** C known: all 30 intents are template-solvable under the rule (A known: 11/11); C open-world: 8/30
   (A open-world 12/39). The C known split therefore tests paraphrase robustness of known procedures, not composition.
4. **Easier per shape, too.** For the same required-app shape AppWeaver is higher on C than on A in every shape (e.g.
   KPM+SLICE+TC 77 % vs 50 %, KPM-only 86 % vs 51 %), so the gap is not only a different shape mix but easier wording.
   The catalog LLM shows the same pattern on known shapes (KPM+SLICE 55 % vs 15 %, TC 81 % vs 60 %).

What C does show robustly: the *gap* between AppWeaver and the template/rule baselines on open-world intents
(rule router 3 %, catalog LLM 18 % vs AppWeaver 95-97 %) and the ranking of the AppWeaver variants, since all
methods see the same intents. Absolute accuracies should be quoted from A (and B) with C as a robustness check.
