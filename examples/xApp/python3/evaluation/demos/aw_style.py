"""Shared figure style for the AppWeaver revision figures (Figs. 4 and 5): one font, one palette, one
meaning per colour and line style across every panel.

  method colours   fixed per method (Okabe-Ito), never by rank
  cell colours     fixed per cell id
  action           solid, coloured;  no action (same seed)  dashed grey
  control event    dotted dark grey (handover dispatched / xApp launched)
  state change     solid vermilion (cell switched off / queue discipline changed)
  after the action light shading
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FONT = {"font.family": "serif", "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
        "font.size": 7, "axes.titlesize": 7.2, "axes.labelsize": 6.8, "xtick.labelsize": 6.3, "ytick.labelsize": 6.3,
        "legend.fontsize": 6.2, "axes.linewidth": 0.6, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "legend.frameon": False, "savefig.dpi": 300,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42, "ps.fonttype": 42}
plt.rcParams.update(FONT)

DOUBLE_COL = 7.16
METHOD_COLOR = {"manual_rule": "#999999", "llm_only": "#E69F00", "langgraph_agentcard": "#0072B2", "appweaver_mem": "#009E73"}
METHOD_LABEL = {"manual_rule": "Rule router", "llm_only": "LLM (catalog)", "langgraph_agentcard": "AppWeaver",
                "appweaver_mem": "AppWeaver + templates + memory"}
CELL_COLOR = {2: "#0072B2", 3: "#E69F00", 4: "#009E73", 5: "#CC79A7"}
ACTION = "#222222"  # aggregate KPI with the workflow applied (cells keep their own colours)
NOACTION = "#8c8c8c"
EVENT = "#444444"
STATE = "#D55E00"
SHADE = "#f2f2f2"
PRED = "#56B4E9"   # twin prediction
MEAS = "#0072B2"   # live measurement


def clean(ax, grid: str = "y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if grid:
        ax.grid(axis=grid, lw=0.3, alpha=0.45)
    ax.set_axisbelow(True)


def event(ax, t: float, state: bool = False):
    ax.axvline(t, color=STATE if state else EVENT, lw=0.7 if state else 0.6, ls="-" if state else ":", zorder=1)


def shade_after(ax, t: float, t_end: float):
    ax.axvspan(t, t_end, color=SHADE, zorder=0, lw=0)


def panel_label(ax, text: str):
    ax.set_title(text, loc="left", fontsize=7.2, pad=4)
