# FlexRIC Evaluation Harness

This folder adds a repeatable evaluation harness around the current FlexRIC portal and LangGraph workflow runtime.

## What It Does

- loads a fixed intent catalog
- routes each intent to the current workflow templates or baseline actions
- executes the selected baseline/method
- captures before/after KPM proxy snapshots when available
- saves one JSON record per run
- writes aggregate summaries for future analysis

## Current Methods

- `manual_rule`
- `single_xapp`
- `langgraph_override`
- `langgraph_enforced`
- `llm_only`

## Important Scope Note

The current portal exposes workflow execution, scheduler control, and agent actions, but it does not yet expose native intent-to-workflow planning. The harness therefore wraps the current platform with repeatable planners so workflow-correctness and reliability can be measured consistently.

## Output Layout

Each batch run is stored under `evaluation/runs/<timestamp>/`:

- `manifest.json`
- `intents.json`
- `records.jsonl`
- `records/*.json`
- `summary.json`
- `analysis.md`

## Running It

```bash
python evaluation/run_harness.py
```

Example with an explicit method list:

```bash
python evaluation/run_harness.py --methods manual_rule single_xapp langgraph_override langgraph_enforced
```

To re-run analysis for an existing `records.jsonl`:

```bash
python evaluation/analyze_results.py evaluation/runs/<timestamp>/records.jsonl
```
