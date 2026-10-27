# Seeded cross-application conflicts

Six intents in `intents_50.json` carry a `conflict_seed`. Before the method under test runs,
the harness (`seed_conflict_if_needed`) starts the seed so that an exclusive control resource is
already held:

| Intent id | Seed started first | Lease it holds | Expected chain | What a correct detection looks like |
|---|---|---|---|---|
| `tc_conflict_recovery` | `transport-qos` workflow (TC `apply-codel`) | `tc_control` | TC | The TC step is refused/queued (`blocked_by_conflict` or workflow `queued`) **before** a second CoDel profile is applied |
| `latency_under_busy_tc` | `transport-qos` | `tc_control` | KPM → SLICE → TC → RC | KPM and SLICE may proceed; the TC step must be flagged |
| `backhaul_queue_conflict_recovery` | `transport-qos` | `tc_control` | KPM → TC → RC | TC step flagged |
| `enterprise_tunnel_busy_tc` | `transport-qos` | `tc_control` | KPM → TC → RC | TC step flagged |
| `slice_policy_race_recovery` | `slice-assurance` workflow (SLICE `monitor`, RC) | `slice_control`, `rc_control` | KPM → SLICE → RC | SLICE (and RC) steps flagged |
| `unknown_busy_runtime_recovery` | `transport-qos` | `tc_control` | KPM → TC → RC | TC step flagged |

Mechanics: for LangGraph-based methods the seed is an *enforced* workflow run, so the scheduler
grants it the exclusive lease; for direct-launch methods the seed is the first action of the seed
workflow, so the agent is busy (`AgentBusyError`). Either way the method under test meets a busy
resource.

Scoring (`METRICS.md`): detection = the method reports the conflict before issuing the conflicting
control (queue/lease refusal, `blocked_reason`, or twin rejection). Recovery (re-planning after the
refusal, with or without a runtime reset) is reported separately as *seeded recovered* and is never
counted as detection. Non-seeded intents flagged as conflicts count as false positives.

Known limitation: all six seeds exercise lease contention on TC/slice control. Seeds for data
dependency conflicts (consuming a KPI nobody produces) and policy-scope conflicts (two rApps writing
the same A1 policy type) are added with the Agent-Card v2 checks and the rApp Directory (plan T2/T3).
