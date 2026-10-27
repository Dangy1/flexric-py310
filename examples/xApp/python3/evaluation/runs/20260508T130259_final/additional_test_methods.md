# Additional Test Methods

These are the next comparison rows worth adding after the current seven-method batch.

## Good Next Baselines

- `llm_agentcard_only`: use the same agent-card prompt as `langgraph_agentcard`, but execute directly without the LangGraph-style repair loop. This isolates how much the graph runtime and internal recovery contribute.
- `langgraph_agentcard_no_repair`: keep agent-card planning, but disable internal recovery. This isolates how much of the gain comes from better planning versus better repair.
- `langgraph_agentcard_no_catalog_guard`: remove the closed-world repair alignment and measure how often the adaptive planner harms known-template intents.
- `langgraph_llm_openworld_fallback`: keep the current catalog route first, but allow an agent-card fallback only when the catalog route is clearly a poor semantic fit.
- `manual_rule_plus_detection`: add a small deterministic detector that splits intents into known versus open-world before routing. This is the strongest fairer rule-based baseline.

## Better Stress Tests

- provider degradation: inject LLM timeout and retry conditions explicitly instead of treating provider failures as accidental
- runtime contention: increase the number of slice and TC conflict seeds beyond the current six cases
- partial telemetry: disable KPM selectively and measure whether planners degrade gracefully
- misleading wording: add adversarial intents that mention both slice and transport terms but only one domain should act
- chain minimality: score whether the generated workflow is not only correct, but also unnecessarily long

## Best Improvement Path For The Current Methods

- tighten `langgraph_agentcard` with a minimal-chain normalizer so validation-only intents stop overusing `KPM`
- add a retrieval memory keyed by intent tags so the adaptive planner can reuse proven chains
- split prompts into `diagnose`, `control`, and `validate` modes instead of asking one prompt to solve every case
- add an explicit penalty for adding `SLICE` when the expected chain is transport-only
- add a small classifier in front of `langgraph_llm` that decides whether the intent belongs to the fixed catalog or should escalate to the adaptive agent-card planner
