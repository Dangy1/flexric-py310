# Final Method Notes

## Result Positions

- `langgraph_agentcard` is the strongest open-world orchestration result in this batch.
- `langgraph_llm` is the strongest closed-world autonomous reasoning result.
- `langgraph_override` is the strongest approval-in-the-loop safety baseline.
- `langgraph_enforced` is the fastest catalog-based autonomous LangGraph result.
- `manual_rule` is the deterministic closed-world oracle baseline.
- `llm_only` is the reasoning-only baseline.
- `single_xapp` is the lower-bound simplicity baseline.

## Why `langgraph_agentcard` Wins The Open-World Split

`langgraph_agentcard` is the only method here that can produce custom workflows from executable agent cards instead of forcing every intent into the existing workflow catalog. That is why its `open_world_workflow_accuracy` rises to `50.0%` while the catalog methods stay at `12.8%`.

It also preserves `100%` known-workflow accuracy because the repair layer now aligns closed-world intents back to the known catalog whenever the intent is already in-scope.

## Why `langgraph_agentcard` Is Still Imperfect

The miss patterns show a consistent bias:

- it often adds `KPM` before simpler `TC -> RC` validation chains
- it sometimes inserts `SLICE` when the expected chain is transport-dominant
- it sometimes stops early after observation or slice selection instead of carrying the chain through validation

That means the agent-card planner is adaptive, but not yet minimal. It still needs stronger chain-normalization rules.

## Why `langgraph_llm` Still Matters

`langgraph_llm` does not improve open-world workflow coverage because it still validates the LLM plan back into the fixed workflow catalog. But it is still the best autonomous graph method for known workflows:

- `100%` known-workflow accuracy
- `100%` tool success
- `100%` conflict detection
- `100%` internal recovery success
- `314.6 ms` average orchestration latency

This is the right method to emphasize when the paper story is "safe graph orchestration for known workflow families."

## Why The Other Methods Differ

`manual_rule` is fast because it does no reasoning. It maps intents to a small fixed catalog and therefore does very well on the known subset and poorly on the open-world subset.

`single_xapp` is fast because it launches only one action. It is not a better orchestrator. Its low workflow accuracy shows that clearly.

`llm_only` is slower than the deterministic baselines because it still calls the provider, and it is less reliable than the graph methods because it executes without graph-level guardrails.

`langgraph_override` stays strong on tool execution and conflict detection because the approval path removes many unsafe execution cases, but it pays for that with `100%` human intervention.

`langgraph_enforced` is very fast among the graph methods, but it still inherits the fixed workflow catalog ceiling and has weaker tool success than the recovery-aware methods.

## Recovery Interpretation

Do not over-read the batch-wide `recovery_rate` by itself. In this harness, that metric includes the outer replay path after reset, so it saturates easily.

The more meaningful metric is `internal_recovery_success_rate`:

- `langgraph_llm`: `100%`
- `langgraph_agentcard`: `100%`

Those are the methods that actually repaired their own runs inside the orchestration method.
