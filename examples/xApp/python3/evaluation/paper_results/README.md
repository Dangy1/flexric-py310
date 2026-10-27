# AppWeaver paper results

Generated 2026-07-02 from:
- **Open model (gpt-oss via Ollama)**: `20260508T130259_final` — 50 intents x 7 methods x 2 repeats = 700 records
- **Claude Fable 5 (headless CLI)**: `20260702T102407_787374Z` — pilot batch, 2 intents x 2 methods (planner cache disabled)

`langgraph_agentcard` corresponds to the **AppWeaver** approach (agent-card discovery
and adaptive composition); the other methods are baselines.

## Open model (gpt-oss) — full batch

| Method | Workflow acc. | Known acc. | Open-world acc. | Tool success | Conflict det. | Policy valid | Int. recovery | Latency (ms) |
|---|---|---|---|---|---|---|---|---|
| Manual rule | 32.0% | 100.0% | 12.8% | 95.6% | 88.0% | 100.0% | -- | 1 |
| Single xApp | 6.0% | 27.3% | 0.0% | 92.0% | 88.0% | 100.0% | -- | 0 |
| LLM- only | 30.0% | 72.7% | 17.9% | 98.2% | 88.0% | 100.0% | -- | 1,014 |
| LG- Override | 32.0% | 100.0% | 12.8% | 100.0% | 100.0% | 100.0% | -- | 135 |
| LG- Enforced | 32.0% | 100.0% | 12.8% | 89.7% | 100.0% | 100.0% | -- | 47 |
| LG-LLM (recov.) | 32.0% | 100.0% | 12.8% | 100.0% | 100.0% | 100.0% | 100.0% | 315 |
| AppWeaver (agent-card) | 61.0% | 100.0% | 50.0% | 100.0% | 96.0% | 100.0% | 100.0% | 3,250 |

## Claude Fable 5 — pilot batch (coverage: xr_latency_guard, congestion_relief; llm_only + agentcard)

| Method | Workflow acc. | Known acc. | Open-world acc. | Tool success | Conflict det. | Policy valid | Int. recovery | Latency (ms) |
|---|---|---|---|---|---|---|---|---|
| LLM- only | 100.0% | 100.0% | -- | 100.0% | -- | 100.0% | -- | 10,941 |
| AppWeaver (agent-card) | 100.0% | 100.0% | -- | 100.0% | -- | 100.0% | -- | 15,964 |

## Caveats for the paper

- The Claude column is a **pilot** (4 records); the full 50-intent Claude batch was
  stopped early by the operator. Rerun `run_harness.py` with `CLAUDE_CLI_PROVIDER=1`
  for a publishable sample before citing Claude numbers beyond a qualitative check.
- Claude pilot latency is **not directly comparable** to the open-model batch: the
  pilot disabled the planner cache (every record pays full planning cost) while the
  final gpt-oss batch used a 7200 s planner cache.
- Network-effect KPIs (latency/throughput/PRB deltas) were unavailable in both runs
  (live KPM telemetry down); metrics cover orchestration behavior only.
- Recovery: prefer `internal_recovery_success_rate` over `recovery_rate` (the latter
  is inflated by external replay after stressor removal).

## Files

- `combined_results.csv` — machine-readable per-method metrics for both models
- `results_table.tex` — IEEEtran booktabs table (uses `\makecell`, `xcolor` `gray!12` — already in your preamble)
- `fig_workflow_accuracy.pdf` — known vs open-world composition accuracy
- `fig_quality_metrics.pdf` — tool success / conflict detection / policy validity
- `fig_latency.pdf` — orchestration latency, log scale (Claude pilot overlaid as markers)
- `fig_model_comparison.pdf` — Claude vs open model on jointly covered cells
- PNG twins of each figure for slides/preview.

Suggested captions map to the paper metrics: composition accuracy ~ workflow validity,
tool-call success ~ deployment success, orchestration latency ~ time-to-deploy.