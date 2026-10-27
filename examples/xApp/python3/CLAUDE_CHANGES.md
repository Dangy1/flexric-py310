# CLAUDE_CHANGES — FlexRIC Agent Portal hardening log

Date: 2026-07-02
Author: Claude (Opus 4.8), reviewed with the project owner.
Scope: `flexric_agent_portal.py` (backend), `agent_portal/` (frontend).
Verification: `python -c "import flexric_agent_portal"` boots cleanly in the
`flexric-py310` conda env (46 routes, 9 agents); `node --check` passes for
`app.js`, `agent.js`, `js/common.js`.

These changes came out of a full code review of the agentic RAN portal
(frontend → FastAPI portal → LangGraph backend → xApp SDK). Each entry lists
the defect, why it mattered, and the fix.

---

## Backend fixes (`flexric_agent_portal.py`)

### 1. "Blocked forever" retry bug in the scheduler action launcher
- **Where:** `_launch_scheduled_actions_locked()`
- **Defect:** a `blocked_by_conflict` result was written with a synthetic id
  (`blocked:<run>:<agent>:<action>`), and the relaunch guard treated any result
  *with an id* and that status as "already real". On the next admission
  (queue promotion or manual approval) the action was skipped permanently.
  The stale-placeholder filter also only removed entries *without* an id, so
  blocked markers stacked up as duplicate siblings.
- **Fix:** `blocked_by_conflict` is now explicitly re-launchable; a result only
  counts as "live" when its id maps to a real `RunState` in `RUNS`. Stale
  `queued`/`blocked_by_conflict` placeholders that don't map to a live run are
  dropped before relaunch, so each action has exactly one current result.

### 2. Exception masking — every launch failure looked like a conflict
- **Where:** `_run_action_locked()`, `_launch_scheduled_actions_locked()`
- **Defect:** all exceptions (missing script, permissions, unknown agent) were
  recorded as `blocked_by_conflict`, indistinguishable from a genuine resource
  conflict. Operators could not tell "queued behind another workflow" apart
  from "permanently broken".
- **Fix:** introduced `AgentBusyError(RuntimeError)`; only that (agent already
  running an action) maps to `blocked_by_conflict`. Every other exception now
  produces `status="failed"` with an `action-error` event carrying the
  exception type, and is *not* retried by the queue. The existing 409 mapping
  in `api_run_action` still works (`AgentBusyError` subclasses `RuntimeError`).

### 3. Zombie leases — heartbeats refreshed for dead workflows
- **Where:** `_refresh_scheduler_heartbeats_locked()`, new
  `_enforce_lease_timeouts_locked()`, `_poll_workflows_locked()`,
  `_reconcile_scheduler_locked()`
- **Defect:** heartbeats were blindly refreshed on every poll for any workflow
  with an "active" lease, so `timeout_at` never mattered; a silently crashed
  subprocess held `slice_control`/`tc_control` forever until a *manual*
  reconcile.
- **Fix:** heartbeats now only refresh when the workflow has a live child
  process or is still inside its execution window. A new
  `_enforce_lease_timeouts_locked()` force-releases leases past `timeout_at`
  with no live children, finalizes the stuck workflow as
  `completed_with_issues` with a `lease-timeout` event, and runs on every
  poll cycle *and* inside reconcile. Queue promotion then unblocks waiters
  automatically.

### 4. Stale queue diagnostics
- **Where:** `_promote_queued_workflows_locked()`
- **Defect:** `blocked_reason`/`queue_entries` were computed once when the
  workflow was queued and never updated, so the UI showed blockers that had
  already released.
- **Fix:** blockers are re-evaluated on each promotion pass; when they change,
  `blocked_reason` and `queue_entries` are refreshed (without spamming a new
  event per poll).

### 5. Approval audit trail overwritten
- **Where:** `_approve_graph_workflow_locked()`
- **Defect:** manual approval replaced the graph/RC gate's `approval_reason`
  with the generic UI text, losing the automated verdict in the audit trail.
- **Fix:** the graph's original reason is preserved as
  `graph_approval_reason` on the workflow and inside the manual-approval
  event metadata; the operator's reason becomes the active `approval_reason`.

### 6. Orphaned xApp subprocesses after portal restart
- **Where:** startup path, new `_terminate_orphan_processes()`
- **Defect:** actions launch with `start_new_session=True`; when the portal
  restarted, persisted runs were marked failed but the actual xApp processes
  survived, holding E2 subscriptions/resources with no owner.
- **Fix:** on startup, persisted in-flight run results with a recorded pid are
  checked against `/proc/<pid>/cmdline`; only processes that are verifiably
  our xApp suite scripts get `SIGTERM` to their process group (recycled pids
  are never touched). A change-log entry records how many were cleaned.

### 7. Input validation on user-supplied fields
- **Where:** new `_validate_text()` + `api_workflow_run`, `api_agent_message`,
  `api_run_task`, `api_workflow_approve`, `api_workflow_save`
- **Defect:** `mode` accepted any string (silently behaving like advisory);
  goals/prompts/messages/reasons/names had no length limits.
- **Fix:** `mode` must be `advisory` or `enforced` (else 400). Length caps:
  goal 2000, task prompt 8000, handoff message 4000, approval reason /
  saved-workflow purpose 1000, names/kinds 200. Required-field checks for
  handoff content, task prompt, and saved-workflow name.

### 8. Optional API token for mutating endpoints
- **Where:** new `_portal_api_token()`, HTTP middleware, `_portal_html()`
- **Defect:** anyone who could reach the portal port (notably with
  `run_agent_portal_lan.sh` binding 0.0.0.0) could POST to launch subprocesses,
  approve enforced workflows, or reset the runtime.
- **Fix:** when `FLEXRIC_PORTAL_API_TOKEN` is set, every mutating `/api/*`
  request must carry a matching `X-Portal-Token` header (constant-time
  comparison); GETs stay open for dashboards. The token is injected into the
  served HTML as a `<meta name="portal-token">` tag so the same-origin UI keeps
  working. **Honest threat model:** because the page itself is unauthenticated,
  this primarily defeats cross-origin/CSRF-style mutation, not a direct network
  attacker — for LAN exposure, keep 127.0.0.1 binding or front with an
  authenticated proxy. Default (no env var) is unchanged behavior.

### 9. Lock-discipline guard
- **Where:** new `_assert_state_lock_held()`, used by `_run_action_locked()`
  and `_launch_scheduled_actions_locked()`
- **Context:** review confirmed all current callers hold the global
  `STATE_LOCK` (RLock), so the reported check-then-insert race is not
  reachable today. The assertion makes that invariant explicit so a future
  unlocked caller (e.g., a new A2A path) fails fast instead of racing.

## Backend — reviewed, intentionally NOT changed

- **Graph runs synchronously under `STATE_LOCK`** (`api_workflow_run`): with
  LLM diagnosis enabled this serializes all API traffic behind the model call.
  Left as-is because the graph is deterministic-fast by default; noted as the
  top candidate for a future async refactor.
- **Per-resource FIFO queueing:** a younger workflow needing only free
  resources is admitted ahead of an older one blocked on other resources.
  This is intentional work-conservation, not a fairness bug.
- **Advisory workflows showing "waiting_for_approval":** intentional — it
  powers the manual-override flow (and the `langgraph_override` evaluation
  method).
- **Duplicate runs of the same workflow template:** allowed by design; the
  lease scheduler serializes conflicting runs (and the evaluation's conflict
  seeding depends on this).

---

## Frontend fixes (`agent_portal/`)

### 10. XSS: handoff message content rendered unescaped
- **Where:** `app.js` `renderMessages()` and the handoff-result panel;
  `agent.js` handoff result + run-log tail
- **Defect:** `message.content` (free-text user input, also reachable via the
  A2A JSON-RPC `message.send`) was interpolated into `innerHTML` without
  escaping — stored XSS for anyone viewing the message feed.
- **Fix:** all message/content interpolations now go through `escapeHtml()`.

### 11. `escapeHtml()` didn't escape quotes
- **Where:** `js/common.js` (and the `agent.js` copy)
- **Defect:** `"` and `'` were left intact, leaving attribute-context
  injection open wherever escaped text lands inside an HTML attribute.
- **Fix:** quotes are now escaped (`&quot;`, `&#39;`).

### 12. API-token support in `fetchJson()`
- **Where:** `app.js`, `agent.js`
- **Fix:** mutating fetches attach `X-Portal-Token` from the injected meta tag
  (no-op when the operator hasn't configured a token).

### 13. Bounded comparison snapshots + quota feedback
- **Where:** `app.js` `saveComparisonSnapshots()`
- **Defect:** the localStorage payload could grow unbounded and quota errors
  vanished into the console.
- **Fix:** only the two known slots (`baseline`, `optimized`) are persisted;
  quota failures now surface a banner while the in-session snapshot survives.

## Evaluation additions (build tree: `build/examples/xApp/python3/`)

### 14. Fixes ported to the build-tree portal copy
The evaluation harness (`evaluation/run_harness.py`) imports its **own copy** of
`flexric_agent_portal.py` from the build tree (which additionally carries
eval-only instrumentation: observation-action cache, duration notes). All
backend fixes above (#1–#5, #9) were ported there so the new evaluation runs
against the fixed system.

### 15. New `claude` LLM provider (both portal copies)
- Opt-in via `CLAUDE_CLI_PROVIDER=1`; requires the `claude` CLI on PATH.
- Runs `claude -p --output-format text` headless (prompt on stdin, no tools),
  `CLAUDE_CLI_MODEL` optionally pins a model, `CLAUDE_CLI_TIMEOUT` (default
  180 s) bounds the call. Listed first so `provider="auto"` prefers it when
  enabled; Ollama/OpenAI behavior is unchanged when the flag is unset.

### 16. Claude evaluation batch + analysis pipeline
- New `evaluation/analyze_claude_results.py`: flattens `records.jsonl` into
  `claude_evaluation.csv`, aggregates `claude_evaluation_summary.csv`,
  compares against a previous batch summary (`claude_vs_baseline.csv`), and
  renders figures under `figures_claude/`.
- Run conditions (chosen to address the methodology critique of earlier
  batches): planner cache **disabled** (`--planner-cache-ttl-s 0`) so every
  record pays true planning cost, and workflow poll timeout raised to 2.0 s
  (was 0.6–0.8 s) to reduce early-exit bias against enforced execution.
- Executed in the `flexric-py310` conda env with `CLAUDE_CLI_PROVIDER=1`,
  `OLLAMA_MODEL=""`, `OPENAI_API_KEY=""` so Claude is the only enabled
  provider.

## Frontend — reviewed, worth knowing

- `agent.html`/`agent.js` are legacy: the backend serves `index.html` (the SPA)
  for every route including `/agents/{id}`. They were still patched
  defensively but are candidates for deletion.
- The earlier review claim that utilities were duplicated because `common.js`
  is unused was **partially wrong**: `app.js` imports `js/common.js` as an ES
  module; only `agent.js` (legacy) carries copies.
- Stale workflow-run selection already falls back safely in `loadPortal()` —
  no change needed.
- Known limitations left open (UX, not correctness): 3-second polling instead
  of SSE/WebSocket, no ARIA/accessibility pass, no dark/responsive mode.
