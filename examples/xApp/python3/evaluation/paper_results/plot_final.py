#!/usr/bin/env python3
"""
AppWeaver evaluation figures for headless environments with full frame.

Usage:
    1) Put this file in the same folder as combined_results.csv
    2) pip install pandas matplotlib numpy
    3) python plot_final.py

Outputs:
    figures/appweaver_accuracy.png / .pdf
    figures/appweaver_latency.png / .pdf
    figures/appweaver_reliability.png / .pdf
"""

from pathlib import Path
import sys

import matplotlib

# Use non-interactive backend for headless servers.
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from matplotlib.patches import Rectangle


# ---------------------------------------------------------------------
# Locate CSV
# ---------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CSV = HERE / "combined_results.csv"

if not CSV.exists():
    CSV = Path.cwd() / "combined_results.csv"

if not CSV.exists():
    sys.exit(
        f"combined_results.csv not found in:\n"
        f"  {HERE}\n"
        f"  {Path.cwd()}"
    )


# ---------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------
OUT_DIR = HERE / "figures"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.7,
    "axes.spines.top": True,
    "axes.spines.right": True,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
    "figure.dpi": 120,
    "savefig.dpi": 600,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------
df = pd.read_csv(CSV)

required_cols = [
    "model",
    "method",
    "known_workflow_accuracy",
    "open_world_workflow_accuracy",
    "average_orchestration_latency_ms",
    "tool_call_success_rate",
    "conflict_detection_accuracy",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    sys.exit(f"Missing required columns in CSV: {missing_cols}")

df = df[df["model"] == "gpt-oss (Ollama)"]

if df.empty:
    sys.exit("No rows found for model == 'gpt-oss (Ollama)'.")

method_order = [
    "single_xapp",
    "manual_rule",
    "llm_only",
    "langgraph_agentcard",
]

method_labels = [
    "Single\nxApp",
    "Manual\nrules",
    "LLM\nonly",
    "AppWeaver",
]

missing_methods = [m for m in method_order if m not in set(df["method"])]
if missing_methods:
    sys.exit(f"Missing methods in CSV: {missing_methods}")

df = df.set_index("method").loc[method_order]


# ---------------------------------------------------------------------
# Extract values
# ---------------------------------------------------------------------
known_acc = df["known_workflow_accuracy"].to_numpy() * 100
open_acc = df["open_world_workflow_accuracy"].to_numpy() * 100
latency_ms = df["average_orchestration_latency_ms"].to_numpy()
tool_success = df["tool_call_success_rate"].to_numpy() * 100
conflict_acc = df["conflict_detection_accuracy"].to_numpy() * 100


# ---------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------
ACCENT = "#C7621E"
BLUE = "#3E6FA8"
SLATE = "#B8C4D0"
GRAY = "#8A8983"
OURS_BG = "#F3E7DA"
DIVIDER = "#B9B8B2"
FRAME = "#333333"

x_pos = np.arange(len(method_order))
appweaver_idx = len(method_order) - 1
bar_width = 0.38


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def force_full_frame(axis):
    """
    Force a full rectangular frame around the plot.

    This uses both visible spines and an axes-coordinate rectangle,
    so the full frame is visible even if a backend/style suppresses spines.
    """
    for side in ["left", "right", "top", "bottom"]:
        axis.spines[side].set_visible(True)
        axis.spines[side].set_linewidth(0.75)
        axis.spines[side].set_color(FRAME)
        axis.spines[side].set_zorder(20)

    axis.tick_params(
        axis="both",
        which="both",
        direction="out",
        width=0.6,
        length=3,
        color=FRAME,
    )

    border = Rectangle(
        (0, 0),
        1,
        1,
        transform=axis.transAxes,
        fill=False,
        edgecolor=FRAME,
        linewidth=0.75,
        zorder=50,
        clip_on=False,
    )
    axis.add_patch(border)


def highlight_appweaver_column(axis):
    """Highlight AppWeaver column."""
    axis.axvspan(
        appweaver_idx - 0.5,
        appweaver_idx + 0.5,
        color=OURS_BG,
        zorder=0,
    )
    axis.axvline(
        appweaver_idx - 0.5,
        color=DIVIDER,
        linewidth=0.7,
        linestyle=(0, (3, 2)),
        zorder=1,
    )


def save_figure(fig, name):
    """Save figure as PNG and PDF."""
    png_path = OUT_DIR / f"{name}.png"
    pdf_path = OUT_DIR / f"{name}.pdf"

    fig.savefig(png_path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.03)

    print(f"Saved: {png_path}")
    print(f"Saved: {pdf_path}")


# ---------------------------------------------------------------------
# Figure 1: Workflow accuracy
# ---------------------------------------------------------------------
fig_acc, ax_acc = plt.subplots(figsize=(3.5, 2.5))

highlight_appweaver_column(ax_acc)

bars_known = ax_acc.bar(
    x_pos - bar_width / 2,
    known_acc,
    bar_width,
    label="Known",
    color=SLATE,
    edgecolor="white",
    linewidth=0.4,
    zorder=2,
)

bars_open = ax_acc.bar(
    x_pos + bar_width / 2,
    open_acc,
    bar_width,
    label="Open-world",
    color=[BLUE,  BLUE,  BLUE,  ACCENT],
    edgecolor="white",
    linewidth=0.4,
    zorder=2,
)

for bar, value in zip(bars_open, open_acc):
    ax_acc.text(
        bar.get_x() + bar.get_width() / 2,
        value + 2,
        f"{value:.0f}",
        ha="center",
        va="bottom",
        fontsize=6.8,
        color=ACCENT if value == open_acc[-1] else FRAME,
    )

ax_acc.set_ylim(0, 112)
ax_acc.set_ylabel("Workflow accuracy")
ax_acc.yaxis.set_major_formatter(PercentFormatter())
ax_acc.set_xticks(x_pos)
ax_acc.set_xticklabels(method_labels)
ax_acc.legend(
    frameon=False,
    loc="upper left",
    handlelength=1.1,
    labelspacing=0.3,
)
ax_acc.margins(x=0.02)
ax_acc.grid(axis="y", color="#E6E5E0", linewidth=0.4, zorder=0)
ax_acc.set_axisbelow(True)

force_full_frame(ax_acc)

fig_acc.tight_layout(pad=0.5)
save_figure(fig_acc, "appweaver_accuracy")


# ---------------------------------------------------------------------
# Figure 2: Orchestration latency
# ---------------------------------------------------------------------
fig_lat, ax_lat = plt.subplots(figsize=(3.9, 2.45))

y_pos = np.arange(len(method_order))[::-1]

bars_latency = ax_lat.barh(
    y_pos,
    latency_ms,
    color=[GRAY,  GRAY,  GRAY,  ACCENT],
    edgecolor="white",
    linewidth=0.4,
    height=0.62,
    zorder=2,
)

# Highlight AppWeaver row.
ax_lat.axhspan(
    -0.5,
    0.5,
    color=OURS_BG,
    zorder=0,
)

ax_lat.axhline(
    0.5,
    color=DIVIDER,
    linewidth=0.7,
    linestyle=(0, (3, 2)),
    zorder=1,
)

ax_lat.set_xscale("log")

# Extra right-side room so latency text stays inside the frame.
lat_min = max(np.min(latency_ms[latency_ms > 0]) * 0.5, 0.1)
lat_max = np.max(latency_ms)
ax_lat.set_xlim(lat_min, lat_max * 7.0)

ax_lat.set_xlabel("Orchestration latency (ms)")
ax_lat.set_yticks(y_pos)
ax_lat.set_yticklabels([label.replace("\n", " ") for label in method_labels])

for bar, value in zip(bars_latency, latency_ms):
    if value >= 1000:
        text = f"{value / 1000:.1f} s"
    elif value >= 1:
        text = f"{value:.0f} ms"
    else:
        text = f"{value:.1f} ms"

    ax_lat.text(
        value * 1.25,
        bar.get_y() + bar.get_height() / 2,
        text,
        va="center",
        ha="left",
        fontsize=6.8,
        color=FRAME,
        clip_on=True,
    )

ax_lat.grid(
    axis="x",
    which="both",
    color="#E6E5E0",
    linewidth=0.4,
    zorder=0,
)
ax_lat.set_axisbelow(True)

force_full_frame(ax_lat)

fig_lat.tight_layout(pad=0.6)
save_figure(fig_lat, "appweaver_latency")


# ---------------------------------------------------------------------
# Figure 3: Reliability
# ---------------------------------------------------------------------
fig_rel, ax_rel = plt.subplots(figsize=(3.5, 2.5))

highlight_appweaver_column(ax_rel)

bars_tool = ax_rel.bar(
    x_pos - bar_width / 2,
    tool_success,
    bar_width,
    label="Tool-call success",
    color=SLATE,
    edgecolor="white",
    linewidth=0.4,
    zorder=2,
)

bars_conflict = ax_rel.bar(
    x_pos + bar_width / 2,
    conflict_acc,
    bar_width,
    label="Conflict detection",
    color=[BLUE,  BLUE,  BLUE,  ACCENT],
    edgecolor="white",
    linewidth=0.4,
    zorder=2,
)

ax_rel.set_ylim(80, 103)
ax_rel.set_ylabel("Rate")
ax_rel.yaxis.set_major_formatter(PercentFormatter())
ax_rel.set_xticks(x_pos)
ax_rel.set_xticklabels(method_labels)
ax_rel.legend(
    frameon=False,
    loc="upper left",
    handlelength=1.1,
    labelspacing=0.3,
)
ax_rel.margins(x=0.02)
ax_rel.grid(axis="y", color="#E6E5E0", linewidth=0.4, zorder=0)
ax_rel.set_axisbelow(True)

force_full_frame(ax_rel)

fig_rel.tight_layout(pad=0.5)
save_figure(fig_rel, "appweaver_reliability")


# ---------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------
plt.close("all")

print(f"\nLoaded data from: {CSV}")
print(f"Figures saved in: {OUT_DIR}")
print("Done.")
