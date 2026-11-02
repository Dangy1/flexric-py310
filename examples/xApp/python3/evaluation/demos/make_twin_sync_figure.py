#!/usr/bin/env python3
"""Figure R1 of the response letter: what the network twin needs to predict a steering workflow's effect.

Hotspot layout, QoE and traffic steering, twin seed p vs live seed p+100. Every statistic is over distinct
decisions (seed pair + UE-level commands); the snapshot-age batches repeat many decisions exactly and a
repeat is counted once; seeds where no control was issued carry no effect and are left out.

  own decision      D2: the twin knows the layout and resolves the policy to users on its own KPM
  live decision     D2S: AppWeaver decides on the live KPM snapshot, the twin rehearses exactly the UE-level
                    RC commands that live then executes (snapshot ages 0-1.5 s pooled)
  re-run            the twin's repeatability: the same seed and commands simulated again (same inputs)

  (a) twin-predicted vs live-measured change per decision (circle throughput, square users served,
      triangle source-cell PRB)
  (b) mean |twin - live| per KPI for the two protocols, and the re-run spread (+- standard error)
  (c) agreement of the twin's accept/reject verdict with the live outcome (pre-declared rule), Wilson 95% CI
  (d) live throughput change of the QoE-steering decision per seed against the age of the live snapshot
      it was decided on: the age changes which users are moved, not the twin's accuracy

  python make_twin_sync_figure.py [--runs ../runs] [--traces BUILD_RUNS] [--out fig_twin_sync]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import aw_style as S
import matplotlib.pyplot as plt
from make_compact_figure import d2_decisions

HERE = Path(__file__).resolve().parent
LAYOUT = "20261101T103300Z_D2_hotspot"
STATE = [("0", "20261102T081207Z_D2S_hotspot"), ("0.5", "20261102T081207Z_D2S_age0.5_hotspot"),
         ("1.0", "20261102T081207Z_D2S_age1.0_hotspot"), ("1.5", "20261102T081207Z_D2S_age1.5_hotspot")]
WORKFLOWS = ("qoe_steering", "traffic_steering")
KPIS = [("throughput", "DL throughput", "o"), ("served", "users served", "s"), ("hot_prb", "source-cell PRB", "^")]
OWN, LIVE, RERUN = S.NOACTION, S.MEAS, "#c9c9c9"
SEED_COLOR = {1: "#0072B2", 2: "#E69F00", 3: "#009E73", 4: "#CC79A7", 5: "#D55E00"}


def gate_rows(batch: Path):
    """{(pair, workflow): (twin verdict, live verdict)} from the batch's per-pair gate table."""
    out = {}
    for line in (batch / "summary.md").read_text().splitlines():
        f = [x.strip() for x in line.split("|")]
        if len(f) > 7 and f[1].isdigit() and f[2] in WORKFLOWS and f[5] in ("accept", "reject"):
            out[(int(f[1]), f[2])] = (f[5], f[7])
    return out


def decisions(batches, traces):
    """Distinct decisions over the batches: key (pair, twin commands, live commands) -> record + verdicts.
    Also returns every twin run per (pair, commands) for the re-run spread."""
    seen, recs, twin_runs = set(), [], defaultdict(list)
    for b in batches:
        gates = gate_rows(b)
        for wf in WORKFLOWS:
            for rec in d2_decisions(b, traces, wf):
                twin_runs[(rec["pair"], rec["twin"]["commands"])].append(rec["twin"])
                key = (rec["pair"], rec["twin"]["commands"], rec["live"]["commands"])
                if key in seen:
                    continue
                seen.add(key)
                recs.append({**rec, "workflow": wf, "verdict": gates.get((rec["pair"], wf))})
    return recs, twin_runs


def mean_se(v):
    v = [x for x in v if x is not None]
    return statistics.fmean(v), (statistics.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0), len(v)


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
    own, _ = decisions([runs / LAYOUT], traces)
    live, twin_runs = decisions([runs / b for _, b in STATE], traces)

    def err(recs, k):
        return [abs(r["twin"][k] - r["live"][k]) for r in recs if r["twin"][k] is not None and r["live"][k] is not None]

    rerun = {k: [abs(a[k] - b[k]) for runs_ in twin_runs.values() for a, b in itertools.combinations(runs_, 2)
                 if a[k] is not None and b[k] is not None] for k, *_ in KPIS}

    fig = plt.figure(figsize=(S.DOUBLE_COL, 2.3))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.0, 1.0, 0.62, 0.95], wspace=0.5)
    ax_a, ax_b, ax_c, ax_d = (fig.add_subplot(gs[i]) for i in range(4))

    # (a) prediction vs outcome
    for recs, color, filled, z in ((own, OWN, False, 2), (live, LIVE, True, 3)):
        for k, _, marker in KPIS:
            pts = [(r["twin"][k], r["live"][k]) for r in recs if r["twin"][k] is not None and r["live"][k] is not None]
            ax_a.scatter([t for t, _ in pts], [l for _, l in pts], s=11, marker=marker, facecolor=color if filled else "none",
                         edgecolor=color, lw=0.7, alpha=0.9, zorder=z)
    lim = (-75, 30)
    ax_a.plot(lim, lim, color="#444", lw=0.6, ls="--", zorder=1)
    ax_a.set_xlim(lim); ax_a.set_ylim(lim)
    ax_a.set_xlabel("twin-predicted change (%)"); ax_a.set_ylabel("live-measured change (%)")
    S.clean(ax_a, grid="both")
    S.panel_label(ax_a, "(a) Prediction vs outcome")
    e_own = statistics.fmean([e for k, *_ in KPIS for e in err(own, k)])
    e_live = statistics.fmean([e for k, *_ in KPIS for e in err(live, k)])
    h = [plt.Line2D([], [], ls="", marker="o", mfc="none", mec=OWN, ms=4), plt.Line2D([], [], ls="", marker="o", mfc=LIVE, mec=LIVE, ms=4)]
    ax_a.legend(h, [f"own decision, n={len(own)}\nmean |err| {e_own:.0f} pp", f"live decision, n={len(live)}\nmean |err| {e_live:.0f} pp"],
                loc="lower right", fontsize=5.4, handletextpad=0.3, borderaxespad=0.2, labelspacing=0.5)

    # (b) error by protocol, with the twin's re-run spread
    w = 0.26
    for i, (k, lab, _) in enumerate(KPIS):
        for j, (vals, color) in enumerate(((err(own, k), OWN), (err(live, k), LIVE), (rerun[k], RERUN))):
            m, se, n = mean_se(vals)
            ax_b.bar(i + (j - 1) * w, m, width=w * 0.92, color=color, yerr=se, error_kw={"lw": 0.5, "capsize": 1.2, "ecolor": "#333"})
            ax_b.text(i + (j - 1) * w, m + se + 0.6, f"{m:.0f}", ha="center", va="bottom", fontsize=5.0)
    ax_b.set_xticks(range(len(KPIS)), ["DL\nthroughput", "users\nserved", "source-\ncell PRB"])
    ax_b.set_ylabel("|twin − live| (percentage points)")
    S.clean(ax_b)
    ax_b.set_ylim(0, 60)
    S.panel_label(ax_b, "(b) Twin error")
    ax_b.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in (OWN, LIVE, RERUN)],
                ["twin's own decision", "live decision rehearsed", "twin re-run, same inputs"], loc="upper left", fontsize=5.4, handlelength=0.9)

    # (c) verdict agreement
    for i, (recs, color, lab) in enumerate(((own, OWN, "own\ndecision"), (live, LIVE, "live\ndecision"))):
        v = [r["verdict"] for r in recs if r["verdict"]]
        k = sum(a == b for a, b in v)
        p, lo, hi = wilson(k, len(v))
        ax_c.bar(i, p, width=0.6, color=color, yerr=[[p - lo], [hi - p]], error_kw={"lw": 0.5, "capsize": 1.5, "ecolor": "#333"})
        ax_c.text(i, 3, f"{k}/{len(v)}", ha="center", va="bottom", fontsize=5.4, color="white")
    ax_c.set_xticks([0, 1], ["own\ndecision", "live\ndecision"])
    ax_c.set_xlim(-0.6, 1.6); ax_c.set_ylim(0, 105)
    ax_c.set_ylabel("verdict matches live (%)")
    S.clean(ax_c)
    S.panel_label(ax_c, "(c) Accept/reject")

    # (d) snapshot age vs the live outcome of the QoE-steering decision
    ages = [float(a) for a, _ in STATE]
    per_seed = defaultdict(dict)
    for a, b in STATE:
        for rec in d2_decisions(runs / b, traces, "qoe_steering"):
            per_seed[rec["pair"]][float(a)] = rec["live"]["throughput"]
    for p, vals in sorted(per_seed.items()):
        xs = [a for a in ages if a in vals]
        ax_d.plot(xs, [vals[a] for a in xs], color=SEED_COLOR[p], marker="o", ms=2.8, lw=0.9, label=f"seed {p}")
    ax_d.axhline(0, color="#444", lw=0.5)
    ax_d.set_xticks(ages, [f"{a:g}" for a in ages])
    ax_d.set_xlabel("age of the live snapshot (s)")
    ax_d.set_ylabel("live throughput change (%)")
    S.clean(ax_d)
    S.panel_label(ax_d, "(d) QoE steering vs snapshot age")
    ax_d.legend(loc="lower right", fontsize=5.0, ncol=2, handlelength=1.0, columnspacing=0.6)

    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    summary = {"distinct_decisions": {"own": len(own), "live": len(live)},
               "err_pp": {name: {k: mean_se(err(recs, k)) for k, *_ in KPIS} for name, recs in (("own", own), ("live", live))},
               "rerun_pp": {k: mean_se(v) for k, v in rerun.items()},
               "verdict": {name: [sum(a == b for a, b in (r["verdict"] for r in recs if r["verdict"])), sum(1 for r in recs if r["verdict"])]
                           for name, recs in (("own", own), ("live", live))},
               "qoe_live_throughput_by_age": {str(p): v for p, v in per_seed.items()}}
    Path(args.out).with_suffix(".json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
