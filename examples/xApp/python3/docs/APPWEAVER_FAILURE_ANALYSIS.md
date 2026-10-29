# AppWeaver failure analysis and fixes (2026-10-29)

Scope: AppWeaver (`langgraph_agentcard`, gpt-oss-120b on spark1) failures under the pre-registered
label rule in the **development** batches only:

* Batch A final `20261028T190000Z_A_final_gptoss120b_spark1_seededfix` (50 intents x 5 repeats, 9 cards): 176/250 pass (70.4 %).
* Batch B k=8 final `20261028T185959_399193Z_B_k8_final_gptoss120b_spark1` (109 intents x 3, 81 cards): 224/327 pass (68.5 %).

Batch C (`intents_c.json`, 60 held-out intents) had not been run, and its intents were not read,
when the fixes below were written. C is the test of the fixes; A and B numbers of a fixed variant
are in-sample (development) numbers and are labelled so.

## Failure classes

| # | Class | What the planner does | A records | B k=8 examples |
|---|---|---|---|---|
| F1 | Busy app avoided | The intent says an app is busy ("while TC is already busy"); the planner leaves the app out or swaps in another controller, although the orchestrator's lease wait/Recover is what handles contention | 20 | `latency_under_busy_tc`, `enterprise_tunnel_busy_tc`, `unknown_busy_runtime_recovery` |
| F2 | Writer on an observe-only intent | "Detect", "investigate", "screen" intents get a control writer (TC, or a write-scope rApp) | 21 | `rlc_queue_anomaly_detection`, `drb_delay_hotspot`, `handover_ping_pong_detection`, `handover_route_risk_screening` |
| F3 | Two writers on one control resource | An rApp and the xApp writing the same resource in one chain (RAPP.TRANSPORT_QOS + TC on `tc_control`, RAPP.SLICE_SLA + SLICE on `slice_control`); compat only warned ("Second writer ... scheduler will serialise them") | 0 (9-card registry) | 18 x RAPP.TRANSPORT_QOS, 13 x RAPP.SLICE_SLA |
| F4 | One control domain missing | A congestion / mixed-service intent touching both slice resources and transport queues gets only SLICE or only TC | 25 | `congestion_relief`, `radio_capacity_headroom`, `stadium_congestion_surge`, `emergency_traffic_preemption` |
| F5 | rApp substituted for the template xApps (B) | With 81 cards, a domain rApp (mobility optimisation, traffic steering) replaces the KPM-SLICE-TC chain the label expects | -- | known split: 11 of 18 failures |
| F6 | Analytics rApp missing (B, unseen capability) | e.g. no RAPP.ANOMALY_DETECTION in a KPI anomaly sweep | -- | 9 x ANOMALY_DETECTION, 4 x ROOT_CAUSE |

Batch A's 74 failed records: F1 20, F2 21, F4 25, and 8 with an extra writer on an intent that does need one
(over-composition, partly F3-like). None of the failures is an infrastructure fault: every one is a planned chain that the label rule
rejects. (RIC degradation in B k=8 affects acknowledgements, not chains.)

## Fixes (learning from the failures)

All are general orchestration principles over card fields or operator feedback; none names an
intent id, label or chain (asserted in `evaluation/tests/test_appweaver_v2.py`). AppWeaver's own
Compose prompt (`prompts.compose_prompt`) is unchanged byte for byte; the fixes are new variants.

1. **Planning guidance** (`learning_prompts.GUIDANCE_SECTION`), against F1-F4:
   select by need, never drop a busy app (contention is the orchestrator's job); least privilege
   (writers only when the intent asks to change something; detect/investigate/screen/assess/report
   use observation and analytics only); no two writers on one control resource; cover every control
   domain the intent affects.
2. **Feedback re-plan** (`nodes/compose.py`), against F3 and empty plans: when the repaired chain is
   empty or still has compat findings (errors or a second writer on one resource), the planner gets
   one bounded re-plan with its previous plan and the findings. The revision is adopted only if it is
   non-empty and has strictly fewer findings. Findings come from the Agent Cards only.
3. **Operator workflow templates** (`appweaver_tpl`, already built) and **experience memory**
   (`appweaver_mem`), against F4/F5: the memory is rebuilt from the *final* Batch A run - for each A
   intent the accepted workflow and up to two of AppWeaver's own rejected proposals with the label
   rule's reasons (operator feedback). Retrieval never returns an entry whose sentence equals the
   query, so on A every intent is scored leave-one-out.

Variants: `appweaver_guided` = 1 + 2; `appweaver_v2` = 1 + 2 + 3.

## Evaluation protocol

* Held-out test: Batch C with `langgraph_agentcard` (frozen AppWeaver), `appweaver_tpl`,
  `appweaver_mem`, `appweaver_guided`, `appweaver_v2`, same harness, seeds and health hooks as A/B.
* Development numbers: A and B k=8 re-run with `appweaver_guided` and `appweaver_v2`; reported as
  in-sample, never as the headline.
* Labels are not changed (pre-registered 2026-10-28).

## Development check (planner only, Batch A intents, 1 run each) - 2026-10-29

`evaluation/devcheck/devcheck.py`: the AppWeaver graph with the real planner (gpt-oss-120b, spark1,
same temperature/seed) and registry, but fake deploy and no busy leases; scored with the label rule.
In-sample for the fixes (they were written from these intents). Frozen AppWeaver measured the same way
gives 33/50, consistent with its 70.4 % in the real Batch A (5 repeats).

| Variant | Rule pass (50) | Median planner+graph time |
|---|---|---|
| AppWeaver (frozen) | 33 (66 %) | 32.9 s |
| + guidance + feedback (`appweaver_guided`) | 38 (76 %) | 35.3 s |
| + templates + memory (`appweaver_v2`) | 36 (72 %) | 36.0 s |

* Fixed by guidance: least privilege (`drb_delay_hotspot`, `gtp_tunnel_health_validation`,
  `pdcp_reorder_investigation` -> KPM only) and domain coverage (`congestion_relief`,
  `edge_gaming_jitter_protection` -> KPM, SLICE, TC).
* Broken by guidance: `slice_fairness_assurance` (domain-coverage rule adds TC).
* Not fixed: the busy-TC intents (F1). The planner reads the rule and still avoids the busy TC, choosing
  RC radio-bearer QoS control "because the TC service model is already occupied". A stronger wording
  was tried on the three busy intents and changed nothing; it was reverted, so the guidance is the one
  measured above. F1 is reported as a planner limitation.
* The feedback re-plan never triggers on the 9-card registry (no two writers share a resource); it is
  aimed at the 81-card registry (F3).
* Guidance frozen at this point (`guidance_section_sha256` in each batch manifest).
