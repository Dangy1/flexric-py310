# Seeded cross-application conflicts

Six intents in `intents_50.json` carry a `conflict_seed`. Before the method under test runs,
the harness (`seed_conflict_if_needed`) starts the seed so that an application the intent will
want is already held by "another operator's" workload:

| Intent id | Seed workflow | Seed action launched | Busy agent | Expected chain | What a correct handling looks like |
|---|---|---|---|---|---|
| `tc_conflict_recovery` | `transport-qos` | TC `apply-codel` | `tc` | TC | No second TC control while the seed runs: wait for the lease, then apply |
| `latency_under_busy_tc` | `transport-qos` | TC `apply-codel` | `tc` | KPM → SLICE → TC → RC | Busy TC noticed before any control; wait or re-plan |
| `backhaul_queue_conflict_recovery` | `transport-qos` | TC `apply-codel` | `tc` | KPM → TC → RC | same |
| `enterprise_tunnel_busy_tc` | `transport-qos` | TC `apply-codel` | `tc` | KPM → TC → RC | same |
| `slice_policy_race_recovery` | `slice-assurance` | SLICE `monitor` | `slice` | KPM → SLICE → RC | Busy SLICE noticed before control |
| `unknown_busy_runtime_recovery` | `transport-qos` | TC `apply-codel` | `tc` | KPM → TC → RC | same |

## Seeding (identical for every method, since 2026-10-28)

The seed is the seed workflow's lease-holding action -- its first action whose card has a write
(exclusive-lease) scope -- launched as a **plain portal action** for *every* method
(`conflict_seed.type == "action"` in every record). The agent is then busy for the action's 30 s
run: any launch of the same agent is refused by the portal's per-agent lease
(`AgentBusyError`, HTTP 409 "already has an active action"). Earlier batches seeded `langgraph*`
methods with an enforced *workflow* (scheduler lease) and the others with a bare action; that
asymmetry is gone (review P1-8).

## Recovery: wait or re-plan, never pre-empt (review P0-2)

No method may reset the runtime while a record runs. `reset_runtime()` (which terminates every
running action, i.e. would kill the seed) is only called between records and raises an
`AssertionError` if called during one; every record carries `preempted_other_workflow = false`.
The old "external recovery" (reset, then re-run the method without the seed) and AppWeaver's
forced reset before its retry are removed.

* **Shared bounded lease wait (all methods).** When a step is refused because the agent is busy,
  the harness keeps the refused attempt as a tool call (`status: "conflict"`, `lease_refusal: true`),
  polls the portal until no *other* workflow holds the agent for up to `--lease-wait-s`
  (default 45 s; the seed runs 30 s) and retries once (`retry_after_lease_wait: true`). If the
  agent is still busy the step stays refused (`lease_refusal_unresolved`).
* **AppWeaver (LangGraph `backend/appweaver/`).** Validate queries the leases of every agent of
  the composed chain *before issuing any control*. If one is busy, Recover asks the LLM recovery
  planner (prompt gets `busy_resources`) to either **wait** (same 45 s budget, then deploy the
  same chain) or **re-plan** a chain without the busy application when the intent can be met
  without it (the busy id is removed from the plan and excluded from repair insertions).
  Recover runs at most once; an unavailable/unparseable recovery planner defaults to wait.
  A refusal that survives the Deploy-time shared wait can only be re-planned around (the wait
  budget is spent). `agentcard_no_repair` has no Recover node: Validate still detects the busy
  app, then Deploy meets the shared lease wait like every baseline.

## Per-record fields

| Field | Meaning |
|---|---|
| `conflict_detected_before_control` | the busy application was noticed before a control to it was issued: AppWeaver's lease pre-check, or a portal lease refusal (409) |
| `partial_deployment` | a control (write-scope) step had already been launched when the first refusal happened (per-action scopes count: SLICE `monitor` is read-only) |
| `lease_wait_s` | seconds spent waiting for busy applications in the record (counted in orchestration latency) |
| `completed_after_wait` | every step launched after a bounded wait, status `completed` |
| `replanned_around_resource` | AppWeaver's Recover re-planned without the busy application |
| `lease_refusal_unresolved` | a refusal remained after the wait (or AppWeaver's wait timed out) |
| `preempted_other_workflow` | a runtime reset ran during the record -- always `false` (asserted) |
| `conflict_detected` (legacy) | `detect_conflict(...)` OR `conflict_detected_before_control` |
| `recovery_attempted` / `recovered_from_failure` (legacy) | a lease wait or re-plan happened / and the record then completed; no longer computed from a reset-and-rerun |

`execution_artifacts.internal_recovery_*` and `execution_artifacts.recovery` hold AppWeaver's Recover
decision, the recovery planner task and the wait outcome; `recovery_reset_runtime` is always `false`.

Scoring (`METRICS.md`): detection = the conflict is noticed before the conflicting control is issued.
Non-seeded intents flagged as conflicts count as false positives. Waiting and re-planning are
reported separately and are never counted as detection.

Known limitation: all six seeds exercise lease contention on TC/SLICE. Seeds for data
dependency conflicts (consuming a KPI nobody produces) and policy-scope conflicts (two rApps writing
the same A1 policy type) are exercised by the Agent-Card compatibility checks in Compose/Validate,
not by a running seed.
