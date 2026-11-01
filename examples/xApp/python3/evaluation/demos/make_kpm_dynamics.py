#!/usr/bin/env python3
"""KPM time series around the moment an AppWeaver action chain is applied (Demos D2 and D3).

Columns: (1) hotspot, KPM -> qoe_prediction -> traffic_steering -> RC (handovers), (2) night,
KPM -> energy_saving -> RC (handovers + cell switch-off), (3) real link, AppWeaver apply-codel over E2.
Rows: (i) users served per cell, (ii) per-cell load (E2 KPM PRB) or per-cell power (ns-3 energy trace)
or ping RTT, (iii) UE-received throughput (ns-3 PDCP trace) or goodput. Solid = run with the action,
dashed grey = the same seed without it (no-op). Vertical lines: dispatch time of every RC command
(result.json commands_dispatched_sim_s) or the wall-clock time of the tc change (hook.log).

The ns-3 inputs are the per-run traces kept in the build tree (kpm.csv, ns3_out/); the committed run
directories hold result.json only. Data sources:
  users per cell: E2 KPM L3servingSINR3gpp_cell_<c>_UEID_<imsi> records per 100 ms period (as the RIC sees it)
  PRB per cell:   E2 KPM RRU.PrbUsedDl.UEID summed over the UEs of the cell's DU report, per 100 ms period
  power per cell: energyfilecell<c>.csv cumulative energy, differentiated per 100 ms
  throughput:     DlPdcpStats.txt RxBytes of all UEs per 0.25 s epoch

  python make_kpm_dynamics.py --hotspot RUNS/<D2_hotspot> --night RUNS/<D2_night> --d3 RUNS/<D3> \
      [--hotspot-seed 105] [--night-seed 101] [--d3-rep 1] [--out fig_kpm_dynamics]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"], "font.size": 7,
                     "axes.linewidth": 0.6, "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight", "pdf.fonttype": 42})
CELLS = [2, 3, 4, 5]
# Okabe-Ito per cell, fixed (cell identity, never rank)
CELL_COLOR = {2: "#0072B2", 3: "#E69F00", 4: "#009E73", 5: "#CC79A7"}
GREY = "#8c8c8c"
OFFSET = {2: 0.0, 3: 0.0, 4: -0.09, 5: 0.09}  # keeps cells 4/5 visible when they serve the same count
PERIOD_US = 100_000
SERVING = re.compile(r"L3servingSINR3gpp_cell_(\d+)_UEID_(\d+)")


def e2_series(run: Path):
    """Per 100 ms period k: users per cell (last serving report of each UE in the period) and PRB per cell."""
    serving = defaultdict(dict)                         # k -> {ue: cell}
    prb = defaultdict(lambda: defaultdict(float))       # k -> cell -> PRB
    with (run / "kpm.csv").open(errors="replace") as handle:
        next(handle, None)
        for line in handle:
            f = line.rstrip("\n").split(",")
            if len(f) < 8 or f[7] == "":
                continue
            try:
                k, nb = int(f[1]) // PERIOD_US, int(f[3])
            except ValueError:
                continue
            m = SERVING.match(f[5])
            if m:
                serving[k][int(m.group(2))] = int(m.group(1))
            elif f[5] == "RRU.PrbUsedDl.UEID" and nb >= 2:
                prb[k][nb] += float(f[7])
    ks = sorted(set(serving) | set(prb))
    users = {c: [] for c in CELLS}
    last = {}
    for k in ks:
        last.update(serving.get(k, {}))
        for c in CELLS:
            users[c].append(sum(1 for cell in last.values() if cell == c))
    return [k * 0.1 for k in ks], users, {c: [prb[k].get(c, 0.0) for k in ks] for c in CELLS}


def power_series(run: Path):
    out = {}
    for c in CELLS:
        rows = []
        for r in csv.reader((run / "ns3_out" / f"energyfilecell{c}.csv").open()):
            try:
                rows.append((float(r[0]), float(r[1])))
            except (ValueError, IndexError):
                continue
        grid, j, ts, ps = [round(0.1 * i, 1) for i in range(1, 80)], 0, [], []
        prev_t, prev_e = 0.0, 0.0
        for t in grid:
            while j + 1 < len(rows) and rows[j + 1][0] <= t:
                j += 1
            e = rows[j][1] if rows and rows[j][0] <= t else 0.0
            ts.append(t); ps.append((e - prev_e) / (t - prev_t)); prev_t, prev_e = t, e
        out[c] = (ts, ps)
    return out


def pdcp_series(run: Path):
    per = defaultdict(float)
    for line in (run / "ns3_out" / "DlPdcpStats.txt").open():
        f = line.split()
        if len(f) < 11 or line.startswith("%"):
            continue
        per[(float(f[0]), float(f[1]))] += float(f[9])
    eps = sorted(per)
    return [e for _, e in eps], [8 * per[(s, e)] / (e - s) / 1e6 for s, e in eps]


def mark_actions(ax, result, first=False):
    for t, cmd in result.get("commands_dispatched_sim_s") or []:
        off = cmd.startswith("OFF")
        ax.axvline(t, color="#D55E00" if off else "#444444", lw=0.6, ls="-" if off else ":", zorder=0)
    if first and result.get("commands_dispatched_sim_s"):
        cmds = [c for _, c in result["commands_dispatched_sim_s"]]
        txt = ", ".join(cmds[:4]) + (" ..." if len(cmds) > 4 else "")
        ax.text(0.01, 1.03, f"RC at {result['act_sim_time_s']:.1f} s: {txt}", transform=ax.transAxes, fontsize=5.5, color="#444")


def style(ax, ylabel=None, xlabel=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(lw=0.3, alpha=0.4)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=6.5)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=6.5)


def ns3_column(axes, batch: Path, seed: int, workflow: str, title: str, kind: str):
    run, noop = batch / "runs" / f"live_s{seed}_{workflow}", batch / "runs" / f"live_s{seed}_noop"
    res = json.loads((run / "result.json").read_text())
    t, users, prb = e2_series(run)
    tn, users_n, prb_n = e2_series(noop)
    for c in CELLS:
        axes[0].step(t, [u + OFFSET[c] for u in users[c]], where="post", color=CELL_COLOR[c], lw=1.0, label=f"cell {c}")
        axes[0].step(tn, [u + OFFSET[c] for u in users_n[c]], where="post", color=CELL_COLOR[c], lw=0.6, ls="--", alpha=0.45)
    axes[0].set_title(title, fontsize=7.2, pad=10)
    if kind == "prb":
        for c in CELLS:
            axes[1].plot(t, prb[c], color=CELL_COLOR[c], lw=0.8)
        hot = sorted({int(s["from"]) for s in (res.get("policy") or {}).get("shed", [])})
        for c in hot:
            axes[1].plot(tn, prb_n[c], color=CELL_COLOR[c], lw=0.6, ls="--", alpha=0.6)
        style(axes[1], "PRB per cell (E2 KPM)")
    else:
        pw, pw_n = power_series(run), power_series(noop)
        for c in CELLS:
            axes[1].plot(*pw[c], color=CELL_COLOR[c], lw=0.8)
        axes[1].plot(pw_n[4][0], [a + b for a, b in zip(pw_n[4][1], pw_n[5][1])], color=GREY, lw=0.6, ls="--", label="cells 4+5, no action")
        axes[1].legend(fontsize=5.5, loc="upper right")
        style(axes[1], "power per cell (W)")
    trim = lambda xy: ([x for x in xy[0] if x <= 7.75], [y for x, y in zip(*xy) if x <= 7.75])  # noqa: E731  traffic stops at 7.9 s
    th, thn = trim(pdcp_series(run)), trim(pdcp_series(noop))
    axes[2].plot(*thn, color=GREY, lw=0.8, ls="--", label="no action (same seed)")
    axes[2].plot(*th, color="#0072B2" if kind == "prb" else "#D55E00", lw=1.0, label="action applied")
    axes[2].legend(fontsize=5.5, loc="lower left")
    style(axes[0], "users per cell")
    style(axes[2], "DL received (Mbit/s)", "simulated time (s)")
    for i, ax in enumerate(axes):
        mark_actions(ax, res, first=(i == 1))
        ax.set_xlim(0.5, 7.8)
    return res


def d3_column(axes, d3: Path, rep: int):
    rdir = d3 / f"rep{rep}"
    r = json.loads((rdir / "result.json").read_text())
    t0 = r["t0"]
    series = r["rtt_series"]
    hook = [l.split() for l in (rdir / "hook.log").read_text().splitlines()]
    t_ctrl = float(hook[0][0]) - t0
    t_launch = r["t_act_launch"] - t0
    rx = [tuple(map(float, l.split(","))) for l in (rdir / "rx.csv").read_text().splitlines()[1:] if l.strip()]
    # goodput per 0.5 s
    acc, bins = defaultdict(float), 0.5
    for t, b in rx:
        acc[int((t - t0) / bins)] += b
    gx = sorted(k for k in acc if k >= 0)
    axes[0].text(0.5, 0.5, "4 bulk TCP flows through a\n10 Mbit/s bottleneck (2000-pkt FIFO)\n\n"
                 f"xApp launched at {t_launch:.1f} s\n(AppWeaver apply-codel)\nE2 control applied at {t_ctrl:.1f} s:\nqueue FIFO -> CoDel (20 ms / 400 ms)",
                 ha="center", va="center", fontsize=6, transform=axes[0].transAxes)
    axes[0].axis("off")
    axes[0].set_title("(c) Real link: CoDel via E2 (TC)", fontsize=7.2, pad=10)
    series = [s for s in series if s[0] >= 0.5]
    axes[1].plot([s[0] for s in series], [s[1] for s in series], color="#56B4E9", lw=0.7)
    style(axes[1], "ping RTT (ms)")
    axes[2].plot([(k + 0.5) * bins for k in gx], [8 * acc[k] / bins / 1e6 for k in gx], color="#56B4E9", lw=1.0)
    axes[2].set_ylim(0, 12)
    style(axes[2], "goodput (Mbit/s)", "time (s)")
    for ax in axes[1:]:
        ax.axvline(t_launch, color="#444", lw=0.6, ls=":")
        ax.axvline(t_ctrl, color="#D55E00", lw=0.7)
    axes[1].text(t_ctrl + 0.8, max(s[1] for s in series) * 0.85, "FIFO -> CoDel", fontsize=6, color="#D55E00")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hotspot", required=True)
    ap.add_argument("--night", required=True)
    ap.add_argument("--d3", default="")
    ap.add_argument("--hotspot-seed", type=int, default=104)
    ap.add_argument("--hotspot-workflow", default="qoe_steering")
    ap.add_argument("--night-seed", type=int, default=101)
    ap.add_argument("--d3-rep", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "fig_kpm_dynamics"))
    args = ap.parse_args()
    ncol = 3 if args.d3 else 2
    fig, axes = plt.subplots(3, ncol, figsize=(7.16, 4.6), sharex="col", gridspec_kw={"height_ratios": [0.8, 1, 1]})
    hs = ns3_column(axes[:, 0], Path(args.hotspot), args.hotspot_seed, args.hotspot_workflow,
                    "(a) Hotspot: KPM -> QoE pred. -> steering -> RC", "prb")
    ns = ns3_column(axes[:, 1], Path(args.night), args.night_seed, "energy_saving",
                    "(b) Night: KPM -> energy saving -> RC", "power")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], color=GREY, ls="--", lw=0.8)); labels.append("dashed: same seed, no action")
    handles.append(plt.Line2D([], [], color="#444", ls=":", lw=0.8)); labels.append("handover / xApp launch")
    handles.append(plt.Line2D([], [], color="#D55E00", lw=0.8)); labels.append("cell off / tc change")
    fig.legend(handles, labels, fontsize=5.8, ncol=7, loc="upper center", bbox_to_anchor=(0.5, 1.03), handlelength=1.4)
    if args.d3:
        d3_column(axes[:, 2], Path(args.d3), args.d3_rep)
    fig.align_ylabels(axes[:, 0])
    fig.tight_layout(h_pad=0.4, w_pad=0.3)
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    print(json.dumps({"hotspot": {"seed": args.hotspot_seed, "commands": hs.get("commands_dispatched_sim_s"), "kpi": hs["kpi"]},
                      "night": {"seed": args.night_seed, "commands": ns.get("commands_dispatched_sim_s"), "kpi": ns["kpi"]}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
