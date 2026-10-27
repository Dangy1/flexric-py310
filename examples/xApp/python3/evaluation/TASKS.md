# Evaluation Tasks

This folder separates the evaluation work into repeatable tasks around the current FlexRIC portal platform.

## Task 1: Intent Catalog

- Define 10 initial intents.
- Record a manually curated expected workflow for each intent.
- Label conflict-inducing cases explicitly.

## Task 2: Harness Logging

- Save one structured JSON record per run.
- Persist raw execution payloads so results can be re-analyzed later.
- Capture workflow/tool-call state, reliability flags, and proxy telemetry snapshots.

## Task 3: Baseline Executors

- `manual_rule`: deterministic rule router plus direct action launches.
- `single_xapp`: first mapped xApp action only.
- `langgraph_override`: advisory workflow followed by manual approval override.
- `langgraph_enforced`: current LangGraph workflow path with RC approval and scheduler handling.
- `llm_only`: optional provider-driven planner without LangGraph. Implemented in code, but may be skipped when the provider is unreachable.

## Task 4: Metric Capture

- Snapshot KPM figures before and after each run.
- Convert available KPM series into reusable proxy metrics:
  - `latency_ms` from `DRB.RlcSduDelayDl`
  - `throughput_mbps` from `DRB.UEThpDl`
  - `prb_utilization` from `RRU.PrbTotDl`
  - `sla_violation_rate` currently unavailable from the live portal payload and therefore recorded as `null`

## Task 5: Analysis

- Compute workflow accuracy.
- Compute tool-call success rate.
- Compute recovery rate.
- Compute policy validity and hallucination rate.
- Compute conflict-detection accuracy against labeled scenarios.
- Compute average orchestration latency.
- Save machine-readable summary JSON and a Markdown analysis report.

## Task 6: Initial Batch

- Run an initial timestamped batch in the current environment.
- Save:
  - copied intent catalog
  - manifest with environment state
  - per-run JSON records
  - JSONL aggregate
  - summary JSON
  - Markdown analysis

## Current Platform Assumption

The current portal does not yet expose native intent-to-workflow planning. This harness therefore evaluates repeatable intent routing around the existing workflow templates and records that limitation in the output artifacts.
