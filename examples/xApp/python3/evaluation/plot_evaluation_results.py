#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PALETTE = {
    "langgraph_enforced": "#0f6d78",
    "langgraph_agentcard": "#8f5db7",
    "langgraph_llm": "#2a7f62",
    "langgraph_override": "#cc6b49",
    "llm_only": "#6c8a2b",
    "manual_rule": "#114b5f",
    "single_xapp": "#b85c38",
}

RATE_COLUMNS: List[Tuple[str, str]] = [
    ("workflow_accuracy", "Workflow Accuracy"),
    ("tool_call_success_rate", "Tool Success"),
    ("conflict_detection_accuracy", "Conflict Detection"),
    ("recovery_rate", "Recovery"),
]

GENERALIZATION_COLUMNS: List[Tuple[str, str]] = [
    ("known_workflow_accuracy", "Known"),
    ("open_world_workflow_accuracy", "Open-World"),
    ("custom_workflow_rate", "Custom Workflow Use"),
]


def load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_method_frame(summary: Dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(summary.get("methods", {})).T
    frame.index.name = "method"
    frame = frame.reset_index()
    preferred_order = [
        "manual_rule",
        "single_xapp",
        "llm_only",
        "langgraph_agentcard",
        "langgraph_llm",
        "langgraph_override",
        "langgraph_enforced",
    ]
    order_map = {name: idx for idx, name in enumerate(preferred_order)}
    frame["order"] = frame["method"].map(lambda item: order_map.get(item, 999))
    frame = frame.sort_values(["order", "method"]).drop(columns=["order"])
    return frame


def build_intent_frame(summary: Dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(summary.get("intents", {})).T
    frame.index.name = "intent_id"
    frame = frame.reset_index()
    frame = frame.sort_values("intent_id")
    return frame


def save_figure(fig: plt.Figure, base_path: Path) -> None:
    fig.savefig(base_path.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(base_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def plot_method_rates(frame: pd.DataFrame, out_dir: Path) -> None:
    x = np.arange(len(frame))
    width = 0.18
    fig, ax = plt.subplots(figsize=(12.5, 6.8))
    shade_cycle = [1.00, 0.82, 0.64, 0.46]

    for idx, (column, label) in enumerate(RATE_COLUMNS):
        values = frame[column].fillna(0.0).to_numpy(dtype=float)
        bars = ax.bar(
            x + (idx - 1.5) * width,
            values,
            width=width,
            label=label,
            color=[_shade_color(PALETTE.get(method, "#4c6a77"), shade_cycle[idx]) for method in frame["method"]],
            edgecolor="white",
            linewidth=0.8,
        )
        for bar, value in zip(bars, values):
            if np.isnan(value):
                continue
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.015,
                f"{value * 100:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90,
            )

    ax.set_title("Evaluation Rates By Method", fontsize=16, fontweight="bold")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.12)
    ax.set_xticks(x)
    ax.set_xticklabels(frame["method"], rotation=20, ha="right")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value * 100:.0f}%")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    save_figure(fig, out_dir / "workflow_rates")


def plot_latency(frame: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    colors = [PALETTE.get(method, "#4c6a77") for method in frame["method"]]
    values = frame["average_orchestration_latency_ms"].fillna(0.0).to_numpy(dtype=float)
    bars = ax.bar(frame["method"], values, color=colors, edgecolor="white", linewidth=1.0)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.015,
            f"{value:.1f} ms",
            ha="center",
            va="bottom",
            fontsize=9,
            rotation=90,
        )

    ax.set_title("Average Orchestration Latency", fontsize=16, fontweight="bold")
    ax.set_ylabel("Milliseconds")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    save_figure(fig, out_dir / "orchestration_latency")


def plot_workflow_generalization(frame: pd.DataFrame, out_dir: Path) -> None:
    x = np.arange(len(frame))
    width = 0.22
    fig, ax = plt.subplots(figsize=(12.2, 6.6))
    shade_cycle = [0.96, 0.72, 0.48]

    for idx, (column, label) in enumerate(GENERALIZATION_COLUMNS):
        values = frame[column].fillna(0.0).to_numpy(dtype=float)
        bars = ax.bar(
            x + (idx - 1) * width,
            values,
            width=width,
            label=label,
            color=[_shade_color(PALETTE.get(method, "#4c6a77"), shade_cycle[idx]) for method in frame["method"]],
            edgecolor="white",
            linewidth=0.8,
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.015,
                f"{value * 100:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90,
            )

    ax.set_title("Workflow Generalization By Method", fontsize=16, fontweight="bold")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.12)
    ax.set_xticks(x)
    ax.set_xticklabels(frame["method"], rotation=20, ha="right")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value * 100:.0f}%")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    fig.tight_layout()
    save_figure(fig, out_dir / "workflow_generalization")


def plot_intent_heatmap(frame: pd.DataFrame, out_dir: Path) -> None:
    plot_frame = pd.DataFrame(
        {
            "Workflow Match": frame["workflow_match_rate"].to_numpy(dtype=float),
            "Failure Rate": frame["failure_rate"].to_numpy(dtype=float),
            "Conflict Rate": frame["conflict_rate"].to_numpy(dtype=float),
        },
        index=frame["intent_id"],
    )
    annot_frame = plot_frame.copy()
    for column in annot_frame.columns:
        annot_frame[column] = annot_frame[column].map(lambda value: f"{value * 100:.1f}%")

    # Invert the red-path metrics so darker green still means "better".
    image_values = plot_frame.copy()
    image_values["Failure Rate"] = 1.0 - image_values["Failure Rate"]
    image_values["Conflict Rate"] = 1.0 - image_values["Conflict Rate"]

    fig, ax = plt.subplots(figsize=(10.5, 7.0))
    image = ax.imshow(image_values.to_numpy(dtype=float), cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_title("Intent-Level Evaluation Heatmap", fontsize=16, fontweight="bold")
    ax.set_xticks(np.arange(len(image_values.columns)))
    ax.set_xticklabels(list(image_values.columns), rotation=10)
    ax.set_yticks(np.arange(len(image_values.index)))
    ax.set_yticklabels(list(image_values.index))

    for row in range(image_values.shape[0]):
        for col in range(image_values.shape[1]):
            value = image_values.iat[row, col]
            text_color = "black" if 0.25 < value < 0.8 else "white"
            ax.text(col, row, annot_frame.iat[row, col], ha="center", va="center", color=text_color, fontsize=9, fontweight="bold")

    cbar = fig.colorbar(image, ax=ax, fraction=0.03, pad=0.03)
    cbar.set_label("Better Outcome", rotation=90)
    fig.tight_layout()
    save_figure(fig, out_dir / "intent_heatmap")


def plot_method_scorecard(frame: pd.DataFrame, out_dir: Path) -> None:
    display = pd.DataFrame(
        {
            "Method": frame["method"],
            "Workflow Accuracy": frame["workflow_accuracy"].map(_pct),
            "Open-world Accuracy": frame["open_world_workflow_accuracy"].map(_pct),
            "Tool Success": frame["tool_call_success_rate"].map(_pct),
            "Conflict Detection": frame["conflict_detection_accuracy"].map(_pct),
            "Recovery": frame["recovery_rate"].map(_pct),
            "Latency (ms)": frame["average_orchestration_latency_ms"].map(lambda v: "n/a" if pd.isna(v) else f"{float(v):.1f}"),
        }
    )

    fig_h = 1.4 + 0.55 * len(display)
    fig, ax = plt.subplots(figsize=(13.5, fig_h))
    ax.axis("off")
    ax.set_title("Method Scorecard", fontsize=16, fontweight="bold", pad=18)

    table = ax.table(
        cellText=display.values,
        colLabels=display.columns,
        loc="center",
        cellLoc="center",
        colLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#d8e0e5")
        if row == 0:
            cell.set_facecolor("#eaf0f3")
            cell.set_text_props(weight="bold")
        else:
            method = display.iloc[row - 1, 0]
            if col == 0:
                cell.set_facecolor(PALETTE.get(method, "#4c6a77"))
                cell.get_text().set_color("white")
                cell.get_text().set_weight("bold")
            else:
                cell.set_facecolor("#fbfcfd" if row % 2 else "#f4f7f9")

    fig.tight_layout()
    save_figure(fig, out_dir / "method_scorecard")


def plot_method_radar(frame: pd.DataFrame, out_dir: Path) -> None:
    metrics: List[Tuple[str, str]] = [
        ("workflow_accuracy", "Workflow\nAccuracy"),
        ("tool_call_success_rate", "Tool\nSuccess"),
        ("conflict_detection_accuracy", "Conflict\nDetection"),
        ("recovery_rate", "Recovery"),
        ("policy_validity_rate", "Policy\nValidity"),
    ]
    labels = [label for _, label in metrics]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8.6, 8.2), subplot_kw={"polar": True})
    fig.suptitle("Method Radar Comparison", fontsize=16, fontweight="bold", y=0.98)

    for _, row in frame.iterrows():
        method = row["method"]
        values = [float(row.get(key) or 0.0) for key, _ in metrics]
        values += values[:1]
        color = PALETTE.get(method, "#4c6a77")
        ax.plot(angles, values, linewidth=2.0, label=method, color=color)
        ax.fill(angles, values, color=color, alpha=0.12)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"], fontsize=9)
    ax.grid(alpha=0.35)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12), frameon=False)
    fig.tight_layout()
    save_figure(fig, out_dir / "method_radar")


def build_outcome_frame(records: List[Dict[str, Any]], method_order: List[str]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for method in method_order:
        method_records = [record for record in records if str(record.get("method")) == method]
        clean = 0
        failure_only = 0
        conflict_only = 0
        both = 0
        for record in method_records:
            failure = bool(record.get("failure_detected"))
            conflict = bool(record.get("conflict_detected"))
            if failure and conflict:
                both += 1
            elif failure:
                failure_only += 1
            elif conflict:
                conflict_only += 1
            else:
                clean += 1
        rows.append(
            {
                "method": method,
                "clean": clean,
                "failure_only": failure_only,
                "conflict_only": conflict_only,
                "failure_and_conflict": both,
                "run_count": len(method_records),
            }
        )
    return pd.DataFrame(rows)


def plot_failure_conflict_stacked(records: List[Dict[str, Any]], frame: pd.DataFrame, out_dir: Path) -> None:
    outcome = build_outcome_frame(records, list(frame["method"]))
    categories = [
        ("clean", "Clean", "#4d8b6b"),
        ("failure_only", "Failure Only", "#d77a61"),
        ("conflict_only", "Conflict Only", "#d9a441"),
        ("failure_and_conflict", "Failure + Conflict", "#7b5ea7"),
    ]

    fig, ax = plt.subplots(figsize=(11.8, 6.5))
    x = np.arange(len(outcome))
    cumulative = np.zeros(len(outcome))

    for key, label, color in categories:
        values = outcome[key].to_numpy(dtype=float)
        bars = ax.bar(x, values, bottom=cumulative, label=label, color=color, edgecolor="white", linewidth=0.9)
        for bar, value, bottom in zip(bars, values, cumulative):
            if value <= 0:
                continue
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bottom + value / 2,
                str(int(value)),
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
            )
        cumulative += values

    ax.set_title("Failure And Conflict Outcomes By Method", fontsize=16, fontweight="bold")
    ax.set_ylabel("Run Count")
    ax.set_xticks(x)
    ax.set_xticklabels(list(outcome["method"]), rotation=20, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    save_figure(fig, out_dir / "failure_conflict_stacked")


def write_figure_notes(summary: Dict[str, Any], out_dir: Path) -> None:
    lines: List[str] = []
    lines.append("# Matplotlib Figure Notes")
    lines.append("")
    lines.append("Generated with `flexric-py310` using `matplotlib`, `numpy`, and `pandas`.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `workflow_rates.png` / `workflow_rates.svg`")
    lines.append("- `orchestration_latency.png` / `orchestration_latency.svg`")
    lines.append("- `workflow_generalization.png` / `workflow_generalization.svg`")
    lines.append("- `intent_heatmap.png` / `intent_heatmap.svg`")
    lines.append("- `method_scorecard.png` / `method_scorecard.svg`")
    lines.append("- `method_radar.png` / `method_radar.svg`")
    lines.append("- `failure_conflict_stacked.png` / `failure_conflict_stacked.svg`")
    lines.append("")
    lines.append("## Method Snapshot")
    lines.append("")
    for method, item in summary.get("methods", {}).items():
        lines.append(
            f"- `{method}`: workflow_accuracy={_pct(item.get('workflow_accuracy'))}, "
            f"tool_success={_pct(item.get('tool_call_success_rate'))}, "
            f"conflict_detection={_pct(item.get('conflict_detection_accuracy'))}, "
            f"latency={_ms(item.get('average_orchestration_latency_ms'))}"
        )
    lines.append("")
    lines.append("## Caveat")
    lines.append("")
    lines.append("- Network-effectiveness metrics were unavailable in this batch because live KPM before/after telemetry was missing.")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _shade_color(color: str, factor: float) -> Tuple[float, float, float]:
    color = color.lstrip("#")
    rgb = [int(color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(min(1.0, channel * factor + (1.0 - factor)) for channel in rgb)


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} ms"


def main(argv: List[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: plot_evaluation_results.py <summary.json> [output_dir]", file=sys.stderr)
        return 2

    summary_path = Path(argv[1]).resolve()
    output_dir = Path(argv[2]).resolve() if len(argv) == 3 else summary_path.parent / "figures_matplotlib"
    records_path = summary_path.parent / "records.jsonl"
    ensure_dir(output_dir)

    summary = load_summary(summary_path)
    records = load_records(records_path)
    method_frame = build_method_frame(summary)
    intent_frame = build_intent_frame(summary)

    plot_method_rates(method_frame, output_dir)
    plot_latency(method_frame, output_dir)
    plot_workflow_generalization(method_frame, output_dir)
    plot_intent_heatmap(intent_frame, output_dir)
    plot_method_scorecard(method_frame, output_dir)
    plot_method_radar(method_frame, output_dir)
    plot_failure_conflict_stacked(records, method_frame, output_dir)
    write_figure_notes(summary, output_dir)

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
