#!/usr/bin/env python3
"""
AppWeaver slide-style figures (sans-serif, full frame) from combined_results.csv.

The CSV is written by make_paper_figures.py; every rate carries `<metric>_ci_lo/_ci_hi`
(95% CI, see README.md). Only Batch A rows (role == "A") are plotted.

Usage:
    python make_paper_figures.py --batch-a ../runs/<A> ...   # writes combined_results.csv
    python plot_final.py

Outputs:
    figures/appweaver_accuracy.png / .pdf      known vs open-world accuracy, 95% CI
    figures/appweaver_latency.png / .pdf       median intent-to-plan latency, whisker to p95
    figures/appweaver_reliability.png / .pdf   acknowledged tool calls and conflict recall, 95% CI
"""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
CSV = HERE / "combined_results.csv"
if not CSV.exists():
    sys.exit(f"combined_results.csv not found in {HERE}; run make_paper_figures.py first.")
OUT_DIR = HERE / "figures"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.7,
    "figure.dpi": 120,
    "savefig.dpi": 600,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

df = pd.read_csv(CSV)
df = df[df["role"] == "A"]
if df.empty:
    sys.exit("No Batch A rows (role == 'A') in combined_results.csv.")
model = str(df["model"].iloc[0])
preliminary = not model.startswith("gpt-oss")

METHODS = [
    ("single_xapp", "Single\napp"),
    ("manual_rule", "Rule\nrouter"),
    ("llm_blind", "LLM\n(no catalog)"),
    ("llm_only", "LLM\n(catalog)"),
    ("agentcard_no_repair", "AppWeaver\n(no repair)"),
    ("langgraph_agentcard", "AppWeaver"),
]
METHODS = [(m, label) for m, label in METHODS if m in set(df["method"])]
df = df.set_index("method").loc[[m for m, _ in METHODS]]
x_pos = np.arange(len(METHODS))
appweaver_idx = [m for m, _ in METHODS].index("langgraph_agentcard") if "langgraph_agentcard" in df.index else None

ACCENT = "#C7621E"
BLUE = "#3E6FA8"
SLATE = "#B8C4D0"
OURS_BG = "#F3E7DA"
DIVIDER = "#B9B8B2"
FRAME = "#333333"
bar_width = 0.38


def rate_with_err(metric):
    """Percent values and asymmetric CI error bars; NaN-safe."""
    v = df[metric].to_numpy(dtype=float) * 100
    lo = df[f"{metric}_ci_lo"].to_numpy(dtype=float) * 100
    hi = df[f"{metric}_ci_hi"].to_numpy(dtype=float) * 100
    err = np.vstack([np.nan_to_num(v - lo), np.nan_to_num(hi - v)])
    return v, np.clip(err, 0, None)


def force_full_frame(axis):
    for side in ["left", "right", "top", "bottom"]:
        axis.spines[side].set_visible(True)
        axis.spines[side].set_linewidth(0.75)
        axis.spines[side].set_color(FRAME)
    axis.tick_params(axis="both", which="both", direction="out", width=0.6, length=3, color=FRAME)
    axis.add_patch(Rectangle((0, 0), 1, 1, transform=axis.transAxes, fill=False, edgecolor=FRAME,
                             linewidth=0.75, zorder=50, clip_on=False))


def highlight_appweaver_column(axis):
    if appweaver_idx is None:
        return
    axis.axvspan(appweaver_idx - 0.5, appweaver_idx + 0.5, color=OURS_BG, zorder=0)
    axis.axvline(appweaver_idx - 0.5, color=DIVIDER, linewidth=0.7, linestyle=(0, (3, 2)), zorder=1)


def label_bars(axis, xs, values, err_hi):
    for x, v, e in zip(xs, values, err_hi):
        if not np.isnan(v):
            axis.text(x, v + e + 1.5, f"{v:.0f}", ha="center", va="bottom", fontsize=6.5, zorder=4)


def finish(axis, ylabel):
    axis.set_xticks(x_pos)
    axis.set_xticklabels([label for _, label in METHODS])
    axis.set_ylabel(ylabel)
    axis.set_xlim(-0.55, len(METHODS) - 0.45)
    axis.yaxis.grid(True, linewidth=0.4, alpha=0.4, zorder=0)
    force_full_frame(axis)


def save_figure(fig, name):
    for ext in ("png", "pdf"):
        path = OUT_DIR / f"{name}.{ext}"
        fig.savefig(path, bbox_inches="tight", pad_inches=0.03)
        print(f"Saved: {path}")
    plt.close(fig)


def bars(axis, offset, metric, label, color, hatch=""):
    v, err = rate_with_err(metric)
    xs = x_pos + offset
    axis.bar(xs, v, bar_width, label=label, color=color, hatch=hatch, edgecolor="white", linewidth=0.4, zorder=2)
    axis.errorbar(xs, v, yerr=err, fmt="none", ecolor=FRAME, elinewidth=0.6, capsize=1.5, zorder=3)
    label_bars(axis, xs, v, err[1])


def mark_preliminary(axis):
    if preliminary:
        axis.set_xlabel(f"PRELIMINARY: planner {model}, not the paper's model", fontsize=6, color=ACCENT)

# Figure 1: workflow accuracy, known vs open-world, 95% CI
fig, ax = plt.subplots(figsize=(4.6, 2.6))
highlight_appweaver_column(ax)
known_n = int(df["known_records"].iloc[0] / max(1, df["repeats"].iloc[0]))
open_n = int(df["open_world_records"].iloc[0] / max(1, df["repeats"].iloc[0]))
bars(ax, -bar_width / 2, "known_accuracy", f"Known ({known_n} intents)", SLATE)
bars(ax, bar_width / 2, "open_world_accuracy", f"Open-world ({open_n} intents)", ACCENT, hatch="//")
ax.set_ylim(0, 112)
ax.yaxis.set_major_formatter(PercentFormatter())
finish(ax, "Workflow accuracy")
mark_preliminary(ax)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)
save_figure(fig, "appweaver_accuracy")

# Figure 2: latency, median with whisker to p95
fig, ax = plt.subplots(figsize=(4.6, 2.4))
highlight_appweaver_column(ax)
median_s = df["latency_median_ms"].to_numpy(dtype=float) / 1000
p95_s = df["latency_p95_ms"].to_numpy(dtype=float) / 1000
median_plot = np.clip(median_s, 1e-4, None)
ax.bar(x_pos, median_plot, 0.55, color=BLUE, edgecolor="white", linewidth=0.4, zorder=2, label="Median")
ax.errorbar(x_pos, median_plot, yerr=[np.zeros_like(median_plot), np.clip(p95_s - median_s, 0, None)], fmt="none",
            ecolor=FRAME, elinewidth=0.6, capsize=1.5, zorder=3, label="to p95")
ax.axhline(1.0, color=DIVIDER, linewidth=0.8, linestyle=(0, (3, 2)))
ax.set_yscale("log")
finish(ax, "Intent-to-plan latency (s)")
mark_preliminary(ax)
ax.legend(loc="upper left", frameon=False)
save_figure(fig, "appweaver_latency")

# Figure 3: reliability, acknowledged tool calls and conflict recall, 95% CI
fig, ax = plt.subplots(figsize=(4.6, 2.6))
highlight_appweaver_column(ax)
bars(ax, -bar_width / 2, "ack_rate", "Acknowledged tool calls", SLATE)
bars(ax, bar_width / 2, "conflict_recall", "Conflict recall", ACCENT, hatch="//")
ax.set_ylim(0, 112)
ax.yaxis.set_major_formatter(PercentFormatter())
finish(ax, "Rate")
mark_preliminary(ax)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False)
save_figure(fig, "appweaver_reliability")
