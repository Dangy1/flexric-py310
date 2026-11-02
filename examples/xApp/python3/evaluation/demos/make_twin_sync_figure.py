#!/usr/bin/env python3
"""Twin synchronization vs prediction accuracy (hotspot, QoE and traffic steering, 5 seed pairs each).

  (a) twin-predicted vs live-measured KPI change per decision: twin with the layout only (it resolves the
      policy to users on its own state) vs twin fed the live KPM snapshot (all snapshot ages pooled)
  (b) mean |twin - live| per KPI against the age of the live snapshot (re-sync every 2x the age)
  (c) agreement of the twin's accept/reject verdict with the live outcome (pre-declared rule), Wilson 95% CI

  python make_twin_sync_figure.py [--runs ../runs] [--traces BUILD_RUNS] [--out fig_twin_sync]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import aw_style as S
import matplotlib.pyplot as plt
from make_compact_figure import d2_changes

HERE = Path(__file__).resolve().parent
LAYOUT = "20261101T103300Z_D2_hotspot"
STATE = [("0", "20261102T081207Z_D2S_hotspot"), ("0.5", "20261102T081207Z_D2S_age0.5_hotspot"),
         ("1.0", "20261102T081207Z_D2S_age1.0_hotspot"), ("1.5", "20261102T081207Z_D2S_age1.5_hotspot")]
WORKFLOWS = ("qoe_steering", "traffic_steering")
KPIS = [("throughput", "DL throughput", "#0072B2", "o"), ("served", "users served", "#E69F00", "s"),
        ("hot_prb", "source-cell PRB", "#CC79A7", "^")]
SYNC_COLOR = {"layout": S.NOACTION, "state": S.MEAS}


def pairs(batch: Path, traces: Path, kpi: str):
    out = []
    for wf in WORKFLOWS:
        ch = d2_changes(batch, traces, wf)
        out += [(t, l) for t, l in zip(ch["twin"][kpi], ch["live"][kpi]) if t is not None and l is not None]
    return out


def gate(batch: Path):
    """(agree, n) over the steering workflows from the batch's summary.md gate table."""
    k = n = 0
    for line in (batch / "summary.md").read_text().splitlines():
        f = [x.strip() for x in line.split("|")]
        if len(f) > 7 and f[1] in WORKFLOWS and f[2].isdigit():
            agree = int(f[7].split("(")[1].split("/")[0])
            k, n = k + agree, n + int(f[2])
    return k, n


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * (c - h), 100 * (c + h)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", default=str(HERE.parent / "runs"))
    ap.add_argument("--traces", default=str(Path.home() / "flexric/build/examples/xApp/python3/evaluation/twin/build/runs"))
    ap.add_argument("--out", default=str(HERE / "fig_twin_sync"))
    args = ap.parse_args()
    runs, traces = Path(args.runs), Path(args.traces)
    levels = [("layout\nonly", runs / LAYOUT, "layout")] + [(f"{a} s", runs / b, "state") for a, b in STATE]
    data = {lab: {k: pairs(b, traces, k) for k, *_ in KPIS} for lab, b, _ in levels}
    gates = {lab: gate(b) for lab, b, _ in levels}

    fig = plt.figure(figsize=(S.DOUBLE_COL, 2.35))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.15, 0.95], wspace=0.38)
    ax_a, ax_b, ax_c = (fig.add_subplot(gs[i]) for i in range(3))

    # (a) predicted vs measured
    err = {"layout": [], "state": []}
    for lab, _, kind in levels:
        for k, _, _, marker in KPIS:
            pts = data[lab][k]
            err[kind] += [abs(t - l) for t, l in pts]
            ax_a.scatter([t for t, _ in pts], [l for _, l in pts], s=11 if kind == "state" else 13, marker=marker,
                         facecolor=SYNC_COLOR[kind] if kind == "state" else "none", edgecolor=SYNC_COLOR[kind],
                         lw=0.7, alpha=0.85, zorder=3 if kind == "state" else 2)
    lim = (-75, 30)
    ax_a.plot(lim, lim, color="#444", lw=0.6, ls="--", zorder=1)
    ax_a.set_xlim(lim); ax_a.set_ylim(lim)
    ax_a.set_xlabel("twin-predicted change (%)"); ax_a.set_ylabel("live-measured change (%)")
    S.clean(ax_a, grid="both")
    S.panel_label(ax_a, "(a) Prediction vs outcome")
    h = [plt.Line2D([], [], ls="", marker="o", mfc="none", mec=S.NOACTION, ms=4),
         plt.Line2D([], [], ls="", marker="o", mfc=S.MEAS, mec=S.MEAS, ms=4)]
    h += [plt.Line2D([], [], ls="", marker=m, mfc="#777", mec="#777", ms=3.6) for *_, m in KPIS]
    ax_a.legend(h, [f"layout only, |err| {statistics.fmean(err['layout']):.0f} pp",
                    f"live snapshot, |err| {statistics.fmean(err['state']):.0f} pp"] + [lab for _, lab, *_ in KPIS],
                loc="lower right", fontsize=5.6, handletextpad=0.3, borderaxespad=0.2, labelspacing=0.25)
    ax_a.text(lim[1] - 2, lim[1] - 6, "y = x", ha="right", va="top", fontsize=5.6, color="#444")

    # (b) error vs snapshot age
    xs = list(range(len(levels)))
    for k, lab, color, marker in KPIS:
        m, se = [], []
        for lev, *_ in levels:
            e = [abs(t - l) for t, l in data[lev][k]]
            m.append(statistics.fmean(e))
            se.append(statistics.stdev(e) / math.sqrt(len(e)) if len(e) > 1 else 0.0)
        ax_b.errorbar(xs[:1], m[:1], yerr=se[:1], color=color, marker=marker, ms=3.4, ls="", capsize=1.5, elinewidth=0.5,
                      mfc="none")  # layout only: its own category, not on the age axis
        ax_b.errorbar(xs[1:], m[1:], yerr=se[1:], color=color, marker=marker, ms=3.4, lw=1.0, capsize=1.5, elinewidth=0.5, label=lab)
    ax_b.axvline(0.5, color="#bbb", lw=0.5)
    ax_b.set_xticks(xs, [lev for lev, *_ in levels])
    ax_b.set_xlim(-0.5, len(levels) - 0.5)
    ax_b.set_xlabel("age of the live snapshot (re-sync every 2× age)")
    ax_b.set_ylabel("|twin − live| (percentage points)")
    ax_b.set_ylim(0, None)
    S.clean(ax_b)
    S.panel_label(ax_b, "(b) Twin error vs synchronization")
    ax_b.legend(loc="upper right", fontsize=5.8, handlelength=1.4)

    # (c) verdict agreement
    bars = [(lev, *gates[lev], kind) for lev, _, kind in levels]
    k_all = sum(g[1] for g in bars if g[3] == "state")
    n_all = sum(g[2] for g in bars if g[3] == "state")
    bars.append(("all\nsnapshots", k_all, n_all, "state"))
    for i, (lev, k, n, kind) in enumerate(bars):
        p, lo, hi = wilson(k, n)
        last = i == len(bars) - 1
        ax_c.bar(i + (0.25 if last else 0), p, width=0.62, color=SYNC_COLOR[kind], alpha=1.0 if last or kind == "layout" else 0.55,
                 yerr=[[p - lo], [hi - p]], error_kw={"lw": 0.5, "capsize": 1.5, "ecolor": "#333"})
    ax_c.set_xticks([i + (0.25 if i == len(bars) - 1 else 0) for i in range(len(bars))], [f"{b[0]}\n{b[1]}/{b[2]}" for b in bars],
                    fontsize=5.6)
    ax_c.set_ylim(0, 105)
    ax_c.set_ylabel("verdict matches live (%)")
    S.clean(ax_c)
    S.panel_label(ax_c, "(c) Accept/reject agreement")

    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    summary = {"err_pp_mean": {k: statistics.fmean(v) for k, v in err.items()},
               "per_level": {lev.replace("\n", " "): {k: statistics.fmean(abs(t - l) for t, l in data[lev][k]) for k, *_ in KPIS} | {"gate": gates[lev]}
                             for lev, *_ in levels}, "gate_pooled_state": [k_all, n_all]}
    Path(args.out).with_suffix(".json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
