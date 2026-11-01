#!/usr/bin/env python3
"""Fig. 3(b): discovery, validation and invocation sequence of AppWeaver, drawn in the style of the original
panel. Every message is one the implementation sends; names and values are those of the recorded QoE-steering
run of Fig. 2 (Batch B, k=8, record 8b291b506dc5):

  Discover   BM25 search of the Agent Registry with the intent text, top 8 per family -> 19 cards
  Compose    LLM chain + Agent Card checks (dependency, interface, control scope, timescale, lifecycle)
  Validate   lease check and E2 dry-run of the RC step on the twin RIC
  Deploy     per step run_action(agent_id, action_id) on the agent portal, which launches the application's tool
             (for an rApp, rapps/runtime.py --rapp ID --tool T: the same decide() the MCP server
             flexric-rapp-directory exposes as tool ID.T) and reads the acknowledgement from its log

  python make_sequence_figure.py [--out ../../paper/Pictures/sequence_v2]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"], "pdf.fonttype": 42})
A2A_FC, A2A_EC, A2A_TXT = "#e2efd9", "#6aa84f", "#3b6d11"
REG_FC, REG_EC, REG_TXT = "#dce9f7", "#4a7ebb", "#1f4e79"
TWIN_FC, TWIN_EC, TWIN_TXT = "#ece6f5", "#8e7cc3", "#4b3a7a"
MCP_FC, MCP_EC, MCP_TXT = "#fde9d9", "#d9822b", "#9c4f0e"
GREY = "#8a8a8a"
MONO = "monospace"

LANES = [("Orchestrator\n(Planner, Compose)", A2A_FC, A2A_EC, A2A_TXT), ("Agent Registry\n(Agent Cards)", REG_FC, REG_EC, REG_TXT),
         ("E2 twin\n(RIC + emulator)", TWIN_FC, TWIN_EC, TWIN_TXT), ("Agent portal\n(domain agents)", A2A_FC, A2A_EC, A2A_TXT),
         ("xApp / rApp\ntools (MCP)", MCP_FC, MCP_EC, MCP_TXT)]
STEPS = [("kpm", "observe-rru"), ("rapp.qoe_prediction", "predict_qoe"), ("rapp.traffic_steering", "apply_steering_policy"),
         ("rc", "rc-control")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE.parents[1] / "paper" / "Pictures" / "sequence_v2"))
    args = ap.parse_args()
    W, H = 7.2, 4.45
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    xs = [0.92, 2.32, 3.72, 5.12, 6.45]
    top, bw, bh, bottom = H - 0.06, 1.24, 0.46, 0.5
    for x, (name, fc, ec, tc) in zip(xs, LANES):
        ax.add_patch(FancyBboxPatch((x - bw / 2, top - bh), bw, bh, boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec=ec, lw=1.0))
        ax.text(x, top - bh / 2, name, ha="center", va="center", fontsize=7.6, color=tc, weight="bold", linespacing=1.05)
        ax.plot([x, x], [bottom, top - bh], color="#bdbdbd", lw=0.7, ls=(0, (4, 3)), zorder=0)

    def act(x, y0, y1, fc, ec):
        ax.add_patch(plt.Rectangle((x - 0.05, y1), 0.1, y0 - y1, fc=fc, ec=ec, lw=0.7, zorder=2))

    def msg(x0, x1, y, text, color, ret=False, fs=7.0, xt=None):
        d = 1 if x1 > x0 else -1
        ax.annotate("", xy=(x1 - d * 0.06, y), xytext=(x0 + d * 0.06, y),
                    arrowprops={"arrowstyle": "->" if ret else "-|>", "color": color, "lw": 1.1,
                                "ls": (0, (4, 2.5)) if ret else "-", "mutation_scale": 8}, zorder=3)
        ax.text((x0 + x1) / 2 if xt is None else xt, y + 0.045, text, ha="center", va="bottom", fontsize=fs, family=MONO, color="#222",
                zorder=4, bbox={"fc": "white", "ec": "none", "pad": 0.4})

    def phase(y0, y1, label):
        ax.plot([0.1, 0.1], [y1, y0], color="#cfcfcf", lw=0.8)
        ax.text(0.16, (y0 + y1) / 2, label, ha="center", va="center", fontsize=7.0, color=GREY, style="italic", rotation=90,
                bbox={"fc": "white", "ec": "none", "pad": 0.5})

    act(xs[0], 3.82, 0.62, A2A_FC, A2A_EC)
    # Discover
    phase(3.86, 3.3, "Discover")
    msg(xs[0], xs[1], 3.74, "search(intent text)", REG_EC)
    act(xs[1], 3.75, 3.4, REG_FC, REG_EC)
    msg(xs[1], xs[0], 3.42, "19 Agent Cards (BM25)", REG_EC, ret=True)
    # Compose
    phase(3.22, 2.72, "Compose")
    ax.add_patch(FancyBboxPatch((xs[0] + 0.12, 2.76), 3.0, 0.42, boxstyle="round,pad=0,rounding_size=0.05",
                                fc="#f2f8ee", ec=A2A_EC, lw=0.8, ls=(0, (3, 2))))
    ax.text(xs[0] + 1.62, 3.06, "LLM chain + Agent Card checks", ha="center", va="center", fontsize=7.2, color=A2A_TXT, weight="bold")
    ax.text(xs[0] + 1.62, 2.88, "KPM \u2192 QoE prediction \u2192 traffic steering \u2192 RC\n"
            "dependency, interface, scope, timescale, lifecycle: 0 errors", ha="center", va="center", fontsize=5.9,
            color="#444", linespacing=1.15)
    # Validate
    phase(2.64, 2.1, "Validate")
    msg(xs[0], xs[2], 2.52, "lease check, dry-run rc-control", TWIN_EC)
    act(xs[2], 2.53, 2.18, TWIN_FC, TWIN_EC)
    msg(xs[2], xs[0], 2.2, "E2 control ack (7.2 s)", TWIN_EC, ret=True)
    # Deploy: one iteration per composed step
    phase(2.02, 0.6, "Deploy")
    ax.add_patch(plt.Rectangle((xs[0] + 0.12, 0.6), xs[4] + 0.5 - xs[0] - 0.12, 1.4, fc="none", ec="#9a9a9a", lw=0.7))
    ax.add_patch(plt.Polygon([(xs[0] + 0.12, 2.0), (xs[0] + 1.32, 2.0), (xs[0] + 1.32, 1.88), (xs[0] + 1.24, 1.8), (xs[0] + 0.12, 1.8)],
                             fc="#f4f4f4", ec="#9a9a9a", lw=0.7))
    ax.text(xs[0] + 0.18, 1.9, "loop  each step", fontsize=6.6, color="#444", va="center", weight="bold")
    msg(xs[0], xs[3], 1.74, "run_action(agent_id, action_id)", A2A_EC, xt=3.75)
    act(xs[3], 1.75, 0.82, A2A_FC, A2A_EC)
    msg(xs[3], xs[4], 1.5, "launch tool", MCP_EC)
    act(xs[4], 1.51, 1.12, MCP_FC, MCP_EC)
    msg(xs[4], xs[3], 1.14, "ack (E2 / policy)", MCP_EC, ret=True)
    msg(xs[3], xs[0], 0.84, "run_id, acknowledged", A2A_EC, ret=True)
    for i, (agent, action) in enumerate(STEPS):
        ax.text(xs[0] + 0.2, 1.52 - i * 0.135, f"{i + 1}  {agent} \u00b7 {action}", fontsize=6.0, family=MONO, color="#333",
                va="center", zorder=4, bbox={"fc": "white", "ec": "none", "pad": 0.3})
    ax.text(xs[4] + 0.44, 0.68, "4/4 acknowledged", fontsize=6.4, color="#444", ha="right", style="italic")
    # legend
    ly = 0.24
    items = [("orchestration call", A2A_FC, A2A_EC), ("application tool (also MCP)", MCP_FC, MCP_EC),
             ("registry", REG_FC, REG_EC), ("E2 twin", TWIN_FC, TWIN_EC)]
    x0 = 0.3
    for lab, fc, ec in items:
        ax.add_patch(plt.Rectangle((x0, ly - 0.06), 0.2, 0.12, fc=fc, ec=ec, lw=0.7))
        ax.text(x0 + 0.27, ly, lab, va="center", fontsize=6.8, color="#333")
        x0 += 0.55 + 0.052 * len(lab)
    ax.annotate("", xy=(x0 + 0.42, ly), xytext=(x0, ly), arrowprops={"arrowstyle": "->", "color": GREY, "lw": 1.0, "ls": (0, (4, 2.5))})
    ax.text(x0 + 0.5, ly, "return", va="center", fontsize=6.8, color="#333")
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}", dpi=220)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
