# FlexRIC Workflow Concurrency Plan

## Purpose
This document is the design note, operator guide, and change log for the workflow-concurrency work in the FlexRIC Python 3 xApp portal.

The goal is to let multiple workflow runs exist at the same time without forcing a global reset whenever two workflows want overlapping control resources.

## Current Implementation Summary
Before this scheduler work, the portal already had:

- graph-backed workflow execution through LangGraph or a linear fallback
- shared KPM telemetry through the KPM bus
- persisted workflow payloads and saved workflow bookmarks in SQLite
- local action launching for `kpm`, `slice`, `tc`, and `rc`
- portal reset controls and runtime safety checks

The main gap was conflict handling:

- workflows could still collide on the same control plane
- conflict handling relied too much on global runtime reset or one-off launch failures
- queueing, lease ownership, and operator actions were not first-class runtime concepts

## Important Clarification
`Reset Runtime` and restarting services are not the same thing.

`Reset Runtime`:

- stops portal-managed local xApp runs
- clears portal-managed live state such as workflow runs, tasks, and messages
- does not restart the portal process itself
- does not restart `nearRT-RIC`, the emulator, RPC, MCP, or the KPM bus

Restarting services:

- restarts `nearRT-RIC`
- restarts the emulator
- restarts the portal process
- restarts the RPC server
- restarts the MCP server
- restarts the KPM bus service
- rebuilds process-local state from scratch

The normal operating model should be queueing and lease management, not reset.

## Known Conflict And Failure Modes In The Older Flow
- two workflows could ask for the same control action surface at nearly the same time
- a direct action launch could fail because another action for the same agent was still alive
- enforced workflows were blocked globally instead of being queued by resource
- reset cleared all workflows, which is too destructive for normal operations
- timeouts were used as a blunt safety tool instead of separating queue wait and action runtime

## Target Architecture
The new workflow scheduler lives inside the current RIC orchestrator backend in `flexric_agent_portal.py`.

### Core Model
- each workflow declares the resources it may need
- a workflow can hold shared or exclusive leases
- `kpm_subscription` is shared-read and backed by the existing shared KPM bus
- write-like control resources are exclusive
- if a requested exclusive resource is busy, the workflow is queued instead of failed

### Resource Classes In V1
- `kpm_subscription`
- `slice_control`
- `tc_control`
- `rc_control`
- `provider_task:<provider>` is reserved for future throttling if needed

### Default Workflow Resource Mapping
`observe-diagnose-optimize`
- shared: `kpm_subscription`
- exclusive: `slice_control`, `tc_control`, `rc_control`

`slice-assurance`
- shared: `kpm_subscription`
- exclusive: `slice_control`, `rc_control`

`transport-qos`
- exclusive: `tc_control`

### Lifecycle Split
Workflow lifecycle:
- `queued`
- `admitted`
- `running`
- `waiting_for_approval`
- `completed`
- `completed_with_issues`
- `cancelled`
- `expired`

Action lifecycle:
- `queued`
- `launching`
- `running`
- `completed`
- `failed`
- `timed_out`
- `cancelled`
- `blocked_by_conflict`

### Safety Model
- queue wait time is separate from action runtime
- lease ownership is explicit
- stale leases can be reconciled
- operator controls are targeted per workflow
- emergency reset stays available, but only as an operator escape hatch

## Migration Plan
1. Add this design log.
2. Add SQLite audit tables for workflows, steps, events, leases, queues, operator actions, and implementation logs.
3. Add a scheduler layer in the portal backend.
4. Route enforced and approved workflows through the scheduler instead of direct action launch.
5. Surface queue and lease state in the UI.
6. Keep `Reset Runtime` but relabel it as emergency-only.

## Operator Usage Guide
### Start a workflow
- advisory workflows will reach `waiting_for_approval` if they have control actions
- enforced workflows will try to acquire leases immediately
- if resources are busy, the workflow will enter `queued`

### Inspect the scheduler
Use:
- `GET /api/runtime/scheduler`
- `GET /api/runtime/leases`
- `GET /api/runtime/queues`

### Cancel a workflow
Use:
- `POST /api/workflows/{run_id}/cancel`

This removes a queued workflow or stops a running workflow and releases its leases.

### Drain a workflow
Use:
- `POST /api/workflows/{run_id}/drain`

This is the targeted operator control for a single workflow. It is safer than a full reset because it only affects one workflow run.

### Reconcile stale leases
Use:
- `POST /api/runtime/leases/reconcile`

This is for cleanup after a child run dies or the portal reloads persisted state.

### Emergency reset
Use only if the runtime is badly stuck:
- `POST /api/runtime/reset`

This clears portal-managed runtime state. It is not a service restart.

## Verification Checklist
The implementation should verify:

- conflicting workflows queue instead of failing globally
- non-conflicting workflows can run at the same time
- queue state survives refresh and portal restart
- leases are released on completion, cancel, drain, or reconcile
- the UI shows why a workflow is waiting
- advisory approval does not silently bypass scheduler safety

## Implementation Log
### 2026-03-26
- Created the design and operations log file.
- Started wiring a central scheduler and audit trail into the portal backend.
- Implemented the first scheduler-backed portal revision with queue, lease, cancel, drain, reconcile, and audit endpoints.
- Revised the frontend to surface scheduler state, queue position, lease ownership, and targeted workflow controls.

## Results Log
### 2026-03-26 Live Verification
Verified against the live build stack at `build/examples/xApp/python3` with the new scheduler APIs enabled.

- `slice-assurance` and `transport-qos` were started together in enforced mode.
- Result: both were admitted immediately and ran in parallel because they did not contend for the same exclusive resource.
- Scheduler state showed concurrent leases for `slice_control`, `rc_control`, `kpm_subscription`, and `tc_control`.

- A second `transport-qos` workflow was started while another `transport-qos` run still held `tc_control`.
- Result: the second workflow entered `queued` instead of failing or forcing a reset.
- Queue state was visible through `GET /api/runtime/queues` and in the workflow detail payload.

- The queued `transport-qos` workflow was cancelled through `POST /api/workflows/{run_id}/cancel`.
- Result: only that queued workflow changed state to `cancelled`; the active workflows kept running.
- The queued action step now reports `cancelled` instead of a generic failure.

- A fresh queued `transport-qos` workflow was then started behind the active `tc_control` holder.
- The active `transport-qos` workflow was drained through `POST /api/workflows/{run_id}/drain`.
- Result: the active workflow released `tc_control`, finished as `completed_with_issues`, and the queued workflow was automatically promoted, admitted, and launched.

- `POST /api/runtime/leases/reconcile` was called after the promotion test.
- Result: `released_leases=0` and `expired_workflows=0`, which matched the healthy live state at the time of the call.

### Implementation Notes From Verification
- The first scheduler revision exposed a bug where graph-side `queued` placeholders could prevent the real action launch after admission.
- Fix: scheduler launch now ignores placeholder results unless they already have a real run id and a live/terminal subprocess state.
- The operator-state mapping was also tightened so cancel/drain outcomes surface as `cancelled` or `completed_with_issues` instead of looking like generic runtime failures.

### Remaining Operational Notes
- `Reset Runtime` is still available, but it remains emergency-only.
- Normal operator flow should be queue, inspect, cancel, drain, or reconcile.
- Restarting services is still a separate operational action and is not equivalent to either cancel, drain, or reset.
