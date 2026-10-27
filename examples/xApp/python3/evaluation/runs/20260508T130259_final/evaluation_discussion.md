# Evaluation Discussion

This batch expands the evaluation from the earlier small closed-world set to `50` intents, including `39` open-world intents and `6` explicit conflict cases. The key change is that the comparison now separates known-template accuracy from open-world workflow accuracy.

The main result is that `langgraph_agentcard` is the strongest method for open-world orchestration in the current platform. It reaches `100%` known-workflow accuracy, `50.0%` open-world workflow accuracy, `62.0%` custom-workflow use, `100%` tool success, and `100%` internal recovery success when recovery is attempted. No other method comes close on open-world workflow accuracy. This is the clearest evidence that agent-card planning plus LLM reasoning does help when the intent is outside the fixed workflow catalog.

The second result is that the predefined-workflow methods all converge to roughly the same ceiling on unknown tasks. `manual_rule`, `langgraph_enforced`, `langgraph_override`, and `langgraph_llm` all land at `12.8%` open-world workflow accuracy. That is not a coincidence. Those methods still route through the three existing workflow templates, so they cannot express most of the new expected chains in this suite.

`langgraph_llm` still matters, but for a different reason. It is the strongest closed-world autonomous reasoning result: `100%` known-workflow accuracy, `100%` tool success, `100%` conflict detection, and `100%` internal recovery success, with much lower latency than `langgraph_agentcard`. In other words, it is the best method when the workflow family is already known and the goal is safe graph execution plus repair.

`langgraph_override` remains the cleanest approval-in-the-loop result. It matches the catalog ceiling on workflow correctness, reaches `100%` tool success and `100%` conflict detection, and keeps human approval in every run. That makes it a strong safety-oriented baseline, but not the strongest adaptive planner.

`manual_rule` remains useful as a deterministic oracle for the closed-world portion of the suite. It is fast and reaches `100%` known-workflow accuracy, but its overall workflow accuracy falls to `32.0%` because it cannot generalize beyond the predefined templates. `single_xapp` is still only a lower-bound simplicity baseline; it is fast because it does less work, and its overall workflow accuracy falls to `6.0%`.

`llm_only` sits between the catalog baselines and the adaptive graph method. It reaches `17.9%` open-world workflow accuracy, which is slightly better than the catalog-only methods, but it misses closed-world cases that should be easy and has weaker conflict detection. That is consistent with its design: it reasons over the intent, but it does not get graph-level guardrails or the adaptive agent-card execution path.

The most important limitation in this batch is that the adaptive method is still only partly generalized. `50.0%` open-world accuracy is a real improvement, but the miss patterns show that it often over-selects observation or slice steps. The most common errors are adding `KPM` before a simpler `TC -> RC` validation chain, or choosing `KPM -> SLICE -> RC` where `KPM -> TC -> RC` would have matched the expected workflow more closely. So the current adaptive planner is meaningfully better, but not yet well calibrated.

The recovery metric also needs careful reading. The harness-level `recovery_rate` is `100%` for every method because external replay after reset still succeeds reliably on these synthetic conflict cases. The more meaningful discriminator is `internal_recovery_success_rate`, where only the repair-capable LangGraph methods contribute. On that metric, both `langgraph_llm` and `langgraph_agentcard` achieved `100%` success in this batch.
