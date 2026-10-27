#!/usr/bin/env python3
"""Analyze a Claude-provider evaluation run and export CSV + figures.

Produces, inside the run directory:
  - claude_evaluation.csv            per-record flat table (one row per intent x method)
  - claude_evaluation_summary.csv    per-method aggregate metrics
  - claude_vs_baseline.csv           per-method comparison against a previous batch (optional)
  - figures_claude/*.png             matplotlib figures

Usage (from the evaluation/ directory, conda env flexric-py310):
  python analyze_claude_results.py --run-dir runs/<timestamp>_claude \
      --baseline-summary runs/20260508T130259_final/summary.json --baseline-label "gpt-oss (Ollama)"
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

METHOD_ORDER = [
    "manual_rule",
    "single_xapp",
    "llm_only",
    "langgraph_override",
    "langgraph_enforced",
    "langgraph_llm",
    "langgraph_agentcard",
]

RECORD_COLUMNS = [
    "record_id",
    "intent_id",
    "intent_category",
    "intent_open_world",
    "method",
    "repeat_index",
    "planner_provider",
    "expected_workflow_id",
    "generated_workflow_id",
    "workflow_match",
    "tool_call_count",
    "tool_call_success_count",
    "tool_call_success_rate",
    "policy_valid",
    "hallucinated_api",
    "conflict_label",
    "conflict_detected",
    "conflict_detection_correct",
    "failure_detected",
    "recovery_attempted",
    "recovered_from_failure",
    "internal_recovery_attempted",
    "internal_recovery_succeeded",
    "human_intervention_required",
    "method_available",
    "orchestration_latency_ms",
    "execution_status",
]


def load_records(run_dir: Path) -> List[Dict[str, Any]]:
    records_path = run_dir / "records.jsonl"
    records = []
    with records_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def flatten_record(record: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = record.get("execution_artifacts") or {}
    planner_task = artifacts.get("planner_task") or {}
    tool_count = int(record.get("tool_call_count") or 0)
    tool_success = int(record.get("tool_call_success_count") or 0)
    recovery = record.get("recovery_result") or {}
    row = {key: record.get(key) for key in RECORD_COLUMNS if key in record}
    row["planner_provider"] = planner_task.get("provider_id") or ""
    row["tool_call_success_rate"] = round(tool_success / tool_count, 4) if tool_count else ""
    row["internal_recovery_attempted"] = bool(artifacts.get("internal_recovery_attempted") or recovery.get("internal_attempted") or False)
    row["internal_recovery_succeeded"] = bool(artifacts.get("internal_recovery_succeeded") or recovery.get("internal_succeeded") or False)
    return row


def rate(values: List[bool]) -> float:
    return round(sum(1 for v in values if v) / len(values), 4) if values else 0.0


def summarize(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for method in METHOD_ORDER:
        method_records = [r for r in records if r.get("method") == method and r.get("method_available", True)]
        if not method_records:
            continue
        known = [r for r in method_records if not r.get("intent_open_world")]
        open_world = [r for r in method_records if r.get("intent_open_world")]
        conflict_records = [r for r in method_records if r.get("conflict_label")]
        tool_counts = sum(int(r.get("tool_call_count") or 0) for r in method_records)
        tool_success = sum(int(r.get("tool_call_success_count") or 0) for r in method_records)
        latencies = [float(r.get("orchestration_latency_ms") or 0.0) for r in method_records]
        internal_attempts = [r for r in method_records if (r.get("execution_artifacts") or {}).get("internal_recovery_attempted")]
        rows.append(
            {
                "method": method,
                "runs": len(method_records),
                "workflow_accuracy": rate([bool(r.get("workflow_match")) for r in method_records]),
                "known_workflow_accuracy": rate([bool(r.get("workflow_match")) for r in known]),
                "open_world_workflow_accuracy": rate([bool(r.get("workflow_match")) for r in open_world]),
                "custom_workflow_rate": rate([str(r.get("generated_workflow_id") or "").startswith("custom:") for r in method_records]),
                "tool_call_success_rate": round(tool_success / tool_counts, 4) if tool_counts else 0.0,
                "policy_validity_rate": rate([bool(r.get("policy_valid", True)) for r in method_records]),
                "hallucination_rate": rate([bool(r.get("hallucinated_api")) for r in method_records]),
                "conflict_detection_accuracy": rate([bool(r.get("conflict_detection_correct")) for r in conflict_records]),
                "recovery_rate": rate([bool(r.get("recovered_from_failure")) for r in method_records if r.get("failure_detected")]),
                "internal_recovery_success_rate": rate([bool((r.get("execution_artifacts") or {}).get("internal_recovery_succeeded")) for r in internal_attempts]),
                "average_orchestration_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
    if not rows:
        return
    fieldnames = columns or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_baseline(summary_path: Path) -> Dict[str, Dict[str, Any]]:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    methods = data.get("methods") or data
    result = {}
    if isinstance(methods, dict):
        for method, payload in methods.items():
            result[method] = payload
    elif isinstance(methods, list):
        for payload in methods:
            result[str(payload.get("method"))] = payload
    return result


BASELINE_METRICS = [
    ("workflow_accuracy", "Workflow accuracy"),
    ("known_workflow_accuracy", "Known accuracy"),
    ("open_world_workflow_accuracy", "Open-world accuracy"),
    ("tool_call_success_rate", "Tool success"),
    ("conflict_detection_accuracy", "Conflict detection"),
    ("average_orchestration_latency_ms", "Latency (ms)"),
]


def compare_with_baseline(summary_rows: List[Dict[str, Any]], baseline: Dict[str, Dict[str, Any]], baseline_label: str) -> List[Dict[str, Any]]:
    rows = []
    for row in summary_rows:
        method = row["method"]
        base = baseline.get(method) or {}
        for key, label in BASELINE_METRICS:
            base_value = base.get(key)
            rows.append(
                {
                    "method": method,
                    "metric": key,
                    "metric_label": label,
                    "claude": row.get(key),
                    "baseline": base_value,
                    "baseline_label": baseline_label,
                    "delta": (round(float(row.get(key) or 0) - float(base_value), 4) if base_value is not None else ""),
                }
            )
    return rows


def bar_positions(n_groups: int, n_series: int, width: float = 0.8):
    series_width = width / n_series
    offsets = [(-width / 2) + series_width * (i + 0.5) for i in range(n_series)]
    return series_width, offsets


def plot_rates(summary_rows: List[Dict[str, Any]], out_dir: Path, prefix: str, label: str) -> None:
    metrics = [
        ("workflow_accuracy", "Workflow accuracy"),
        ("tool_call_success_rate", "Tool success"),
        ("conflict_detection_accuracy", "Conflict detection"),
        ("policy_validity_rate", "Policy validity"),
    ]
    methods = [row["method"] for row in summary_rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    series_width, offsets = bar_positions(len(methods), len(metrics))
    for (key, label), offset in zip(metrics, offsets):
        values = [float(row.get(key) or 0.0) for row in summary_rows]
        ax.bar([i + offset for i in range(len(methods))], values, width=series_width, label=label)
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title(f"{label} evaluation: method quality rates")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / f"{prefix}_workflow_rates.png", dpi=160)
    plt.close(fig)


def plot_generalization(summary_rows: List[Dict[str, Any]], out_dir: Path, prefix: str, label: str) -> None:
    metrics = [
        ("known_workflow_accuracy", "Known intents"),
        ("open_world_workflow_accuracy", "Open-world intents"),
        ("custom_workflow_rate", "Custom workflows"),
    ]
    methods = [row["method"] for row in summary_rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    series_width, offsets = bar_positions(len(methods), len(metrics))
    for (key, label), offset in zip(metrics, offsets):
        values = [float(row.get(key) or 0.0) for row in summary_rows]
        ax.bar([i + offset for i in range(len(methods))], values, width=series_width, label=label)
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title(f"{label} evaluation: known vs open-world generalization")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / f"{prefix}_workflow_generalization.png", dpi=160)
    plt.close(fig)


def plot_latency(summary_rows: List[Dict[str, Any]], out_dir: Path, prefix: str, label: str) -> None:
    methods = [row["method"] for row in summary_rows]
    values = [float(row.get("average_orchestration_latency_ms") or 0.0) for row in summary_rows]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.bar(methods, values, color="#0f6d78")
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:,.0f}", (bar.get_x() + bar.get_width() / 2, value), ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Average orchestration latency (ms)")
    ax.set_title(f"{label} evaluation: end-to-end latency by method\n(planner cache disabled — every record pays true planning cost)")
    ax.set_yscale("log")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / f"{prefix}_orchestration_latency.png", dpi=160)
    plt.close(fig)


def plot_baseline_comparison(comparison_rows: List[Dict[str, Any]], out_dir: Path, baseline_label: str, prefix: str, label: str) -> None:
    # One panel per metric, Claude vs baseline side-by-side for the LLM-driven methods.
    focus_methods = ["llm_only", "langgraph_override", "langgraph_enforced", "langgraph_llm", "langgraph_agentcard"]
    rate_metrics = [m for m, _ in BASELINE_METRICS if m != "average_orchestration_latency_ms"]
    fig, axes = plt.subplots(1, len(rate_metrics), figsize=(4 * len(rate_metrics), 4.5), sharey=True)
    for ax, metric in zip(axes, rate_metrics):
        rows = [r for r in comparison_rows if r["metric"] == metric and r["method"] in focus_methods and r["baseline"] not in (None, "")]
        methods = [r["method"] for r in rows]
        claude_vals = [float(r["claude"] or 0.0) for r in rows]
        base_vals = [float(r["baseline"] or 0.0) for r in rows]
        series_width, offsets = bar_positions(len(methods), 2, width=0.7)
        ax.bar([i + offsets[0] for i in range(len(methods))], claude_vals, width=series_width, label=label, color="#c96442")
        ax.bar([i + offsets[1] for i in range(len(methods))], base_vals, width=series_width, label=baseline_label, color="#5c7c8a")
        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels([m.replace("langgraph_", "lg_") for m in methods], rotation=30, ha="right", fontsize=8)
        ax.set_title(dict(BASELINE_METRICS)[metric], fontsize=10)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Rate")
    axes[0].legend(fontsize=8)
    fig.suptitle(f"{label} vs {baseline_label}: LLM-driven methods on the 50-intent catalog")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_dir / f"{prefix}_vs_baseline.png", dpi=160)
    plt.close(fig)


def plot_intent_heatmap(records: List[Dict[str, Any]], out_dir: Path, prefix: str, label: str) -> None:
    intents = sorted({str(r.get("intent_id")) for r in records})
    methods = [m for m in METHOD_ORDER if any(r.get("method") == m for r in records)]
    matrix = []
    for intent_id in intents:
        row = []
        for method in methods:
            cell = [r for r in records if str(r.get("intent_id")) == intent_id and r.get("method") == method]
            row.append(rate([bool(r.get("workflow_match")) for r in cell]) if cell else 0.0)
        matrix.append(row)
    fig, ax = plt.subplots(figsize=(9, max(8, 0.22 * len(intents))))
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([m.replace("langgraph_", "lg_") for m in methods], rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(intents)))
    ax.set_yticklabels(intents, fontsize=6)
    ax.set_title(f"Workflow match per intent x method ({label} provider)")
    fig.colorbar(im, ax=ax, shrink=0.6, label="Workflow match rate")
    fig.tight_layout()
    fig.savefig(out_dir / f"{prefix}_intent_heatmap.png", dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--baseline-summary", default="")
    parser.add_argument("--baseline-label", default="gpt-oss (Ollama)")
    parser.add_argument("--prefix", default="claude_evaluation", help="Filename prefix for CSVs/figures (e.g. openai_evaluation)")
    parser.add_argument("--provider-label", default="", help="Provider label used in figure titles (defaults to prefix)")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    records = load_records(run_dir)
    if not records:
        raise SystemExit(f"No records found in {run_dir}")

    prefix = args.prefix.strip() or "claude_evaluation"
    figures_dir = run_dir / f"figures_{prefix}"
    figures_dir.mkdir(exist_ok=True)

    flat_rows = [flatten_record(record) for record in records]
    write_csv(run_dir / f"{prefix}.csv", flat_rows, RECORD_COLUMNS)

    summary_rows = summarize(records)
    write_csv(run_dir / f"{prefix}_summary.csv", summary_rows)

    provider_label = args.provider_label.strip() or prefix.replace("_evaluation", "").replace("_", " ").title()
    plot_rates(summary_rows, figures_dir, prefix, provider_label)
    plot_generalization(summary_rows, figures_dir, prefix, provider_label)
    plot_latency(summary_rows, figures_dir, prefix, provider_label)
    plot_intent_heatmap(records, figures_dir, prefix, provider_label)

    if args.baseline_summary:
        baseline = load_baseline(Path(args.baseline_summary))
        comparison_rows = compare_with_baseline(summary_rows, baseline, args.baseline_label)
        write_csv(run_dir / f"{prefix}_vs_baseline.csv", comparison_rows)
        plot_baseline_comparison(comparison_rows, figures_dir, args.baseline_label, prefix, provider_label)

    print(f"records: {len(records)}")
    for row in summary_rows:
        print(
            f"{row['method']:>22}: acc={row['workflow_accuracy']:.2f} known={row['known_workflow_accuracy']:.2f} "
            f"open={row['open_world_workflow_accuracy']:.2f} tools={row['tool_call_success_rate']:.2f} "
            f"latency={row['average_orchestration_latency_ms']:.0f}ms"
        )
    print(f"CSV + figures written under {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
