#!/usr/bin/env python3
"""Build IEEE-magazine-quality figures, tables, and CSVs for the AppWeaver paper.

Inputs
  --final-run      runs/20260508T130259_final          (open model: gpt-oss via Ollama, 700 records)
  --claude-run     runs/20260702T102407_787374Z        (Claude Fable 5 pilot via headless CLI)

Outputs (into this directory)
  combined_results.csv      per-method metrics, one row per (model, method)
  results_table.tex         booktabs table ready for IEEEtran
  README.md                 human-readable summary
  fig_workflow_accuracy.[pdf|png]   known vs open-world composition accuracy
  fig_quality_metrics.[pdf|png]     tool success / conflict detection / policy validity
  fig_latency.[pdf|png]             orchestration latency (log scale)
  fig_model_comparison.[pdf|png]    Claude vs open model on jointly covered cells

Style: single-column IEEE (3.5 in wide), serif fonts, colorblind- and
grayscale-safe (hatches + distinct lightness), no in-figure titles (captions
belong in LaTeX).

Run inside the flexric-py310 conda env:
  python make_paper_figures.py --final-run ../runs/20260508T130259_final \
      --claude-run ../runs/20260702T102407_787374Z
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- IEEE style
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.linewidth": 0.6,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6.5,
        "legend.frameon": False,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,  # embed TrueType for IEEE PDF eXpress
        "ps.fonttype": 42,
    }
)

SINGLE_COL = 3.5  # inches

# Method ids -> paper labels. langgraph_agentcard is the AppWeaver approach.
METHODS = [
    ("manual_rule", "Manual\nrule"),
    ("single_xapp", "Single\nxApp"),
    ("llm_only", "LLM-\nonly"),
    ("langgraph_override", "LG-\nOverride"),
    ("langgraph_enforced", "LG-\nEnforced"),
    ("langgraph_llm", "LG-LLM\n(recov.)"),
    ("langgraph_agentcard", "AppWeaver\n(agent-card)"),
]
METHOD_IDS = [m for m, _ in METHODS]
METHOD_LABELS = [l for _, l in METHODS]

# Colorblind-safe palette (Okabe-Ito) with distinct lightness for grayscale.
C_BLUE = "#0072B2"
C_ORANGE = "#E69F00"
C_GREEN = "#009E73"
C_VERM = "#D55E00"
C_GRAY = "#999999"
C_SKY = "#56B4E9"

METRICS_FOR_TABLE = [
    ("workflow_accuracy", "Workflow acc."),
    ("known_workflow_accuracy", "Known acc."),
    ("open_world_workflow_accuracy", "Open-world acc."),
    ("tool_call_success_rate", "Tool success"),
    ("conflict_detection_accuracy", "Conflict det."),
    ("policy_validity_rate", "Policy valid"),
    ("internal_recovery_success_rate", "Int. recovery"),
    ("average_orchestration_latency_ms", "Latency (ms)"),
]


def load_final_summary(final_run: Path) -> Dict[str, Dict[str, Any]]:
    data = json.loads((final_run / "summary.json").read_text(encoding="utf-8"))
    return data["methods"]


def load_claude_records(claude_run: Path) -> List[Dict[str, Any]]:
    records = []
    with (claude_run / "records.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def rate(values: List[bool]) -> float:
    return sum(1 for v in values if v) / len(values) if values else float("nan")


def summarize_claude(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for method in METHOD_IDS:
        rows = [r for r in records if r.get("method") == method]
        if not rows:
            continue
        tools = sum(int(r.get("tool_call_count") or 0) for r in rows)
        tools_ok = sum(int(r.get("tool_call_success_count") or 0) for r in rows)
        lat = [float(r.get("orchestration_latency_ms") or 0.0) for r in rows]
        out[method] = {
            "run_count": len(rows),
            "workflow_accuracy": rate([bool(r.get("workflow_match")) for r in rows]),
            "known_workflow_accuracy": rate([bool(r.get("workflow_match")) for r in rows if not r.get("intent_open_world")]),
            "open_world_workflow_accuracy": rate([bool(r.get("workflow_match")) for r in rows if r.get("intent_open_world")]),
            "tool_call_success_rate": tools_ok / tools if tools else float("nan"),
            "conflict_detection_accuracy": rate([bool(r.get("conflict_detection_correct")) for r in rows if r.get("conflict_label")]),
            "policy_validity_rate": rate([bool(r.get("policy_valid", True)) for r in rows]),
            "internal_recovery_success_rate": float("nan"),
            "average_orchestration_latency_ms": sum(lat) / len(lat) if lat else float("nan"),
        }
    return out


def fmt(value: Any, metric: str) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "--"
    if v != v:  # NaN
        return "--"
    if metric == "average_orchestration_latency_ms":
        return f"{v:,.0f}"
    return f"{100 * v:.1f}"


# ---------------------------------------------------------------- figures
def grouped_bars(ax, series, labels, colors, hatches, width=0.8):
    n = len(series)
    sw = width / n
    for i, (values, label, color, hatch) in enumerate(zip(series, labels, colors, hatches)):
        xs = [j - width / 2 + sw * (i + 0.5) for j in range(len(values))]
        ax.bar(xs, values, width=sw * 0.92, label=label, color=color, hatch=hatch,
               edgecolor="black", linewidth=0.4)


def fig_workflow_accuracy(final: Dict[str, Dict[str, Any]], out: Path) -> None:
    known = [float(final[m]["known_workflow_accuracy"]) for m in METHOD_IDS]
    openw = [float(final[m]["open_world_workflow_accuracy"]) for m in METHOD_IDS]
    overall = [float(final[m]["workflow_accuracy"]) for m in METHOD_IDS]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 1.9))
    grouped_bars(ax, [known, openw, overall],
                 ["Known intents", "Open-world intents", "Overall"],
                 [C_BLUE, C_ORANGE, C_GRAY], ["", "//", ".."])
    ax.set_xticks(range(len(METHOD_IDS)))
    ax.set_xticklabels(METHOD_LABELS, fontsize=5.5)
    ax.set_ylabel("Composition accuracy")
    ax.set_ylim(0, 1.05)
    ax.yaxis.grid(True, linewidth=0.3, alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.14), handlelength=1.4, columnspacing=0.9)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_workflow_accuracy.{ext}")
    plt.close(fig)


def fig_quality_metrics(final: Dict[str, Dict[str, Any]], out: Path) -> None:
    tool = [float(final[m]["tool_call_success_rate"]) for m in METHOD_IDS]
    conflict = [float(final[m]["conflict_detection_accuracy"]) for m in METHOD_IDS]
    policy = [float(final[m]["policy_validity_rate"]) for m in METHOD_IDS]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 1.9))
    grouped_bars(ax, [tool, conflict, policy],
                 ["Tool-call success", "Conflict detection", "Policy validity"],
                 [C_GREEN, C_VERM, C_SKY], ["", "\\\\", "xx"])
    ax.set_xticks(range(len(METHOD_IDS)))
    ax.set_xticklabels(METHOD_LABELS, fontsize=5.5)
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    ax.yaxis.grid(True, linewidth=0.3, alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.14), handlelength=1.4, columnspacing=0.9)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_quality_metrics.{ext}")
    plt.close(fig)


def fig_latency(final: Dict[str, Dict[str, Any]], claude: Dict[str, Dict[str, Any]], out: Path) -> None:
    base = [float(final[m]["average_orchestration_latency_ms"]) for m in METHOD_IDS]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 1.9))
    xs = range(len(METHOD_IDS))
    ax.bar(xs, base, width=0.55, color=C_BLUE, edgecolor="black", linewidth=0.4,
           label="Open model (gpt-oss)")
    # Overlay Claude pilot where covered (markers, not bars: different sample size).
    cx = [i for i, m in enumerate(METHOD_IDS) if m in claude]
    cy = [float(claude[METHOD_IDS[i]]["average_orchestration_latency_ms"]) for i in cx]
    if cx:
        ax.plot(cx, cy, linestyle="none", marker="D", markersize=4, color=C_VERM,
                markeredgecolor="black", markeredgewidth=0.4, label="Claude (pilot, no plan cache)")
    ax.set_yscale("log")
    ax.set_ylim(top=max(max(base), max(cy) if cx else 0) * 20)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(METHOD_LABELS, fontsize=5.5)
    ax.set_ylabel("Latency (ms, log)")
    ax.yaxis.grid(True, which="both", linewidth=0.3, alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", handlelength=1.4)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_latency.{ext}")
    plt.close(fig)


def summarize_subset(records: List[Dict[str, Any]], intents: set, methods: List[str]) -> Dict[str, Dict[str, Any]]:
    """Aggregate a records list restricted to given intents/methods (for a fair like-for-like cell comparison)."""
    subset = [r for r in records if str(r.get("intent_id")) in intents and r.get("method") in methods]
    return summarize_claude(subset)  # same aggregation logic


def fig_model_comparison(final_records: List[Dict[str, Any]], claude: Dict[str, Dict[str, Any]],
                         claude_records: List[Dict[str, Any]], out: Path) -> None:
    """Claude vs open model restricted to the SAME (intent, method) cells the Claude pilot covered."""
    methods = [m for m in METHOD_IDS if m in claude]
    if not methods:
        return
    covered_intents = {str(r.get("intent_id")) for r in claude_records}
    open_subset = summarize_subset(final_records, covered_intents, methods)
    metrics = [("workflow_accuracy", "Workflow acc."), ("tool_call_success_rate", "Tool success")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(SINGLE_COL, 1.8), sharey=True)
    for ax, (metric, label) in zip(axes, metrics):
        cl = [float(claude[m][metric]) for m in methods]
        op = [float(open_subset.get(m, {}).get(metric, float("nan"))) for m in methods]
        grouped_bars(ax, [cl, op], ["Claude (Fable 5)", "Open model (gpt-oss)"],
                     [C_VERM, C_BLUE], ["", "//"], width=0.7)
        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels([dict(METHODS)[m] for m in methods], fontsize=6)
        ax.set_xlabel(label, fontsize=7)
        ax.set_ylim(0, 1.1)
        ax.yaxis.grid(True, linewidth=0.3, alpha=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Rate")
    axes[0].legend(ncol=2, loc="upper left", bbox_to_anchor=(0, 1.18), handlelength=1.4)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_model_comparison.{ext}")
    plt.close(fig)


# ---------------------------------------------------------------- tables/CSV
def write_combined_csv(final: Dict[str, Dict[str, Any]], claude: Dict[str, Dict[str, Any]], out: Path) -> None:
    columns = ["model", "method", "runs"] + [m for m, _ in METRICS_FOR_TABLE]
    rows = []
    for method in METHOD_IDS:
        payload = final[method]
        rows.append({"model": "gpt-oss (Ollama)", "method": method, "runs": payload.get("run_count", ""),
                     **{k: payload.get(k, "") for k, _ in METRICS_FOR_TABLE}})
    for method in METHOD_IDS:
        if method in claude:
            payload = claude[method]
            rows.append({"model": "Claude Fable 5 (pilot)", "method": method, "runs": payload.get("run_count", ""),
                         **{k: payload.get(k, "") for k, _ in METRICS_FOR_TABLE}})
    with (out / "combined_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_latex_table(final: Dict[str, Dict[str, Any]], out: Path) -> None:
    label_by_id = {m: l.replace("-\n", "-").replace("\n", " ") for m, l in METHODS}
    lines = [
        "% Auto-generated from evaluation batch 20260508T130259_final (50 intents x 7 methods x 2 repeats, 700 records).",
        "% Open model: gpt-oss via Ollama. Values in percent except latency (ms).",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Workflow orchestration performance across composition methods (50-intent catalog).}",
        "\\label{tab:appweaver-results}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabular}{@{}lcccccc@{}}",
        "\\toprule",
        "\\textbf{Method} & \\makecell{\\textbf{Known}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Open-world}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Tool}\\\\\\textbf{succ.}} & \\makecell{\\textbf{Conflict}\\\\\\textbf{det.}} & \\makecell{\\textbf{Policy}\\\\\\textbf{valid}} & \\makecell{\\textbf{Latency}\\\\\\textbf{(ms)}} \\\\",
        "\\midrule",
    ]
    for method in METHOD_IDS:
        p = final[method]
        row = " & ".join([
            label_by_id[method] if method != "langgraph_agentcard" else "\\textbf{AppWeaver (agent-card)}",
            fmt(p.get("known_workflow_accuracy"), "known_workflow_accuracy"),
            fmt(p.get("open_world_workflow_accuracy"), "open_world_workflow_accuracy"),
            fmt(p.get("tool_call_success_rate"), "tool_call_success_rate"),
            fmt(p.get("conflict_detection_accuracy"), "conflict_detection_accuracy"),
            fmt(p.get("policy_validity_rate"), "policy_validity_rate"),
            fmt(p.get("average_orchestration_latency_ms"), "average_orchestration_latency_ms"),
        ])
        prefix = "\\rowcolor{gray!12}\n" if method == "langgraph_agentcard" else ""
        lines.append(prefix + row + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (out / "results_table.tex").write_text("\n".join(lines), encoding="utf-8")


def write_readme(final: Dict[str, Dict[str, Any]], claude: Dict[str, Dict[str, Any]],
                 final_run: Path, claude_run: Path, out: Path) -> None:
    def table(models: Dict[str, Dict[str, Any]]) -> List[str]:
        header = "| Method | " + " | ".join(label for _, label in METRICS_FOR_TABLE) + " |"
        sep = "|---" * (len(METRICS_FOR_TABLE) + 1) + "|"
        body = []
        for method in METHOD_IDS:
            if method not in models:
                continue
            p = models[method]
            cells = " | ".join(fmt(p.get(k), k) + ("" if k == "average_orchestration_latency_ms" else "%") if fmt(p.get(k), k) != "--" else "--"
                               for k, _ in METRICS_FOR_TABLE)
            body.append(f"| {dict(METHODS)[method].replace(chr(10), ' ')} | {cells} |")
        return [header, sep] + body

    lines = [
        "# AppWeaver paper results",
        "",
        f"Generated 2026-07-02 from:",
        f"- **Open model (gpt-oss via Ollama)**: `{final_run.name}` — 50 intents x 7 methods x 2 repeats = 700 records",
        f"- **Claude Fable 5 (headless CLI)**: `{claude_run.name}` — pilot batch, 2 intents x 2 methods (planner cache disabled)",
        "",
        "`langgraph_agentcard` corresponds to the **AppWeaver** approach (agent-card discovery",
        "and adaptive composition); the other methods are baselines.",
        "",
        "## Open model (gpt-oss) — full batch",
        "",
        *table(final),
        "",
        "## Claude Fable 5 — pilot batch (coverage: xr_latency_guard, congestion_relief; llm_only + agentcard)",
        "",
        *table(claude),
        "",
        "## Caveats for the paper",
        "",
        "- The Claude column is a **pilot** (4 records); the full 50-intent Claude batch was",
        "  stopped early by the operator. Rerun `run_harness.py` with `CLAUDE_CLI_PROVIDER=1`",
        "  for a publishable sample before citing Claude numbers beyond a qualitative check.",
        "- Claude pilot latency is **not directly comparable** to the open-model batch: the",
        "  pilot disabled the planner cache (every record pays full planning cost) while the",
        "  final gpt-oss batch used a 7200 s planner cache.",
        "- Network-effect KPIs (latency/throughput/PRB deltas) were unavailable in both runs",
        "  (live KPM telemetry down); metrics cover orchestration behavior only.",
        "- Recovery: prefer `internal_recovery_success_rate` over `recovery_rate` (the latter",
        "  is inflated by external replay after stressor removal).",
        "",
        "## Files",
        "",
        "- `combined_results.csv` — machine-readable per-method metrics for both models",
        "- `results_table.tex` — IEEEtran booktabs table (uses `\\makecell`, `xcolor` `gray!12` — already in your preamble)",
        "- `fig_workflow_accuracy.pdf` — known vs open-world composition accuracy",
        "- `fig_quality_metrics.pdf` — tool success / conflict detection / policy validity",
        "- `fig_latency.pdf` — orchestration latency, log scale (Claude pilot overlaid as markers)",
        "- `fig_model_comparison.pdf` — Claude vs open model on jointly covered cells",
        "- PNG twins of each figure for slides/preview.",
        "",
        "Suggested captions map to the paper metrics: composition accuracy ~ workflow validity,",
        "tool-call success ~ deployment success, orchestration latency ~ time-to-deploy.",
    ]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-run", required=True)
    parser.add_argument("--claude-run", required=True)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    final_run = Path(args.final_run).resolve()
    claude_run = Path(args.claude_run).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    final = load_final_summary(final_run)
    claude = summarize_claude(load_claude_records(claude_run))

    write_combined_csv(final, claude, out)
    write_latex_table(final, out)
    write_readme(final, claude, final_run, claude_run, out)
    fig_workflow_accuracy(final, out)
    fig_quality_metrics(final, out)
    fig_latency(final, claude, out)
    final_records = load_claude_records(final_run)  # same JSONL loader works for any run
    claude_records = load_claude_records(claude_run)
    fig_model_comparison(final_records, claude, claude_records, out)

    print(f"Wrote CSV, LaTeX table, README, and figures to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
