#!/usr/bin/env python3
"""Fig. 4 candidate: system KPIs over time around the moment an AppWeaver workflow acts (Demos D2, D3).

Columns
  (a) ns-3 hotspot, KPM -> qoe_prediction -> traffic_steering -> RC (handovers)
  (b) ns-3 night,   KPM -> energy_saving -> RC (handovers, then cell switch-off)
  (c) real link,    AppWeaver apply-codel over E2 (queue FIFO -> CoDel)
Rows (ns-3)
  1 users per cell      E2 KPM L3servingSINR3gpp_cell_<c>_UEID_<imsi>, last report per UE in each 100 ms period
  2 load / power        E2 KPM RRU.PrbUsedDl.UEID summed per cell (a) or ns-3 energy trace per cell, W (b)
  3 DL received         ns-3 DlPdcpStats.txt RxBytes of all UEs per 0.25 s epoch
  4 users served        UEs that received >= half their 3.2 Mb/s offered rate in the epoch (QoE-relevant)
Rows (real link)
  2 ping RTT, 3 goodput (0.5 s bins), 4 share of pings with RTT > 100 ms per 1 s
Style (aw_style): action solid, same seed without the action dashed grey, dotted = control dispatched,
vermilion = state change (cell off / queue swap), shading = after the action.

The ns-3 inputs are the per-run traces kept in the build tree (kpm.csv, ns3_out/).

  python make_kpm_dynamics.py --hotspot RUNS/<D2_hotspot> --night RUNS/<D2_night> --d3 RUNS/<D3> \
      [--hotspot-seed 104] [--night-seed 101] [--d3-rep 1] [--out fig_kpm_dynamics]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import aw_style as S
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CELLS = [2, 3, 4, 5]
OFFSET = {2: 0.0, 3: 0.0, 4: -0.1, 5: 0.1}  # keeps cells 4/5 visible when they serve the same count
PERIOD_US = 100_000
OFFERED_MBPS = 3.2
SERVING = re.compile(r"L3servingSINR3gpp_cell_(\d+)_UEID_(\d+)")
T_END = 7.75  # traffic stops at 7.9 s


def e2_series(run: Path):
    serving = defaultdict(dict)
    prb = defaultdict(lambda: defaultdict(float))
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
    users, last = {c: [] for c in CELLS}, {}
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
        grid, j, ts, ps, prev_t, prev_e = [round(0.1 * i, 1) for i in range(1, 79)], 0, [], [], 0.0, 0.0
        for t in grid:
            while j + 1 < len(rows) and rows[j + 1][0] <= t:
                j += 1
            e = rows[j][1] if rows and rows[j][0] <= t else 0.0
            ts.append(t); ps.append((e - prev_e) / (t - prev_t)); prev_t, prev_e = t, e
        out[c] = (ts, ps)
    return out


def pdcp_series(run: Path):
    """Per 0.25 s epoch: total DL received (Mbit/s) and users served (>= half the offered rate)."""
    per = defaultdict(lambda: defaultdict(float))
    for line in (run / "ns3_out" / "DlPdcpStats.txt").open():
        f = line.split()
        if len(f) < 11 or line.startswith("%"):
            continue
        per[(float(f[0]), float(f[1]))][int(f[3])] += float(f[9])
    t, total, served = [], [], []
    for (s, e), ues in sorted(per.items()):
        if e > T_END:
            continue
        rates = [8 * b / (e - s) / 1e6 for b in ues.values()]
        t.append(e); total.append(sum(rates)); served.append(sum(1 for r in rates if r >= OFFERED_MBPS / 2))
    return t, total, served


def ns3_column(axes, batch: Path, seed: int, workflow: str, title: str, kind: str):
    run, noop = batch / "runs" / f"live_s{seed}_{workflow}", batch / "runs" / f"live_s{seed}_noop"
    res = json.loads((run / "result.json").read_text())
    t_act = res["act_sim_time_s"]
    cmds = res.get("commands_dispatched_sim_s") or []
    t, users, prb = e2_series(run)
    tn, users_n, prb_n = e2_series(noop)
    for c in CELLS:
        axes[0].step(t, [u + OFFSET[c] for u in users[c]], where="post", color=S.CELL_COLOR[c], lw=1.0, label=f"cell {c}")
        axes[0].step(tn, [u + OFFSET[c] for u in users_n[c]], where="post", color=S.CELL_COLOR[c], lw=0.6, ls="--", alpha=0.45)
    axes[0].set_ylabel("users attached\nper cell")
    S.panel_label(axes[0], title)
    if kind == "prb":
        for c in CELLS:
            axes[1].plot(t, prb[c], color=S.CELL_COLOR[c], lw=0.8)
        for c in sorted({int(s["from"]) for s in (res.get("policy") or {}).get("shed", [])}):
            axes[1].plot(tn, prb_n[c], color=S.CELL_COLOR[c], lw=0.6, ls="--", alpha=0.55)
        axes[1].set_ylabel("PRB used per cell\n(E2 KPM, of 139)")
    else:
        pw, pw_n = power_series(run), power_series(noop)
        for c in CELLS:
            axes[1].plot(*pw[c], color=S.CELL_COLOR[c], lw=0.8)
        axes[1].plot(pw_n[4][0], pw_n[4][1], color=S.CELL_COLOR[4], lw=0.6, ls="--", alpha=0.55)
        axes[1].set_ylabel("power per cell\n(W)")
    th, tot, srv = pdcp_series(run)
    thn, totn, srvn = pdcp_series(noop)
    axes[2].plot(thn, totn, color=S.NOACTION, lw=0.8, ls="--", label="no action (same seed)")
    axes[2].plot(th, tot, color=S.ACTION, lw=1.0, label="workflow applied")
    axes[2].set_ylabel("DL received\n(Mbit/s)")
    axes[3].step(thn, srvn, where="post", color=S.NOACTION, lw=0.8, ls="--")
    axes[3].step(th, srv, where="post", color=S.ACTION, lw=1.0)
    axes[3].set_ylabel("users served\n(>= 1.6 Mbit/s)")
    axes[3].set_xlabel("simulated time (s)")
    axes[3].yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for i, ax in enumerate(axes):
        S.clean(ax)
        S.shade_after(ax, t_act, T_END)
        for tc, cmd in cmds:
            S.event(ax, tc, state=cmd.startswith("OFF"))
        ax.set_xlim(0.5, T_END)
    hos = [c for _, c in cmds if c.startswith("HO")]
    offs = [c.split()[1] for _, c in cmds if c.startswith("OFF")]
    note = f"{len(hos)} handovers at {t_act:.1f} s" + (f"; cells {', '.join(offs)} off at {max(tc for tc, c in cmds if c.startswith('OFF')):.1f} s" if offs else "")
    axes[1].text(0.99, 0.97, note, transform=axes[1].transAxes, ha="right", va="top", fontsize=5.8, color=S.EVENT,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0, "alpha": 0.8})
    return res, (th, tot, srv), (thn, totn, srvn)


def d3_column(axes, d3: Path, rep: int):
    rdir = d3 / f"rep{rep}"
    r = json.loads((rdir / "result.json").read_text())
    t0 = r["t0"]
    series = [s for s in r["rtt_series"] if s[0] >= 0.5]
    t_ctrl = float((rdir / "hook.log").read_text().split()[0]) - t0
    t_launch = r["t_act_launch"] - t0
    t_end = max(s[0] for s in series)
    rx = [tuple(map(float, l.split(","))) for l in (rdir / "rx.csv").read_text().splitlines()[1:] if l.strip()]
    acc = defaultdict(float)
    for t, b in rx:
        acc[int((t - t0) / 0.5)] += b
    gx = sorted(k for k in acc if 1 <= k and (k + 1) * 0.5 <= t_end)
    S.panel_label(axes[0], "(c) Real link: TC action via E2")
    axes[0].text(0.5, 0.45, "4 bulk TCP flows, 10 Mbit/s bottleneck,\n2000-packet FIFO (bufferbloat)\n"
                 f"AppWeaver apply-codel launched {t_launch:.1f} s;\nE2 control applied {t_ctrl:.1f} s: FIFO $\\rightarrow$ CoDel",
                 ha="center", va="center", fontsize=6.2, transform=axes[0].transAxes)
    axes[0].axis("off")
    axes[1].plot([s[0] for s in series], [s[1] for s in series], color=S.ACTION, lw=0.6)
    axes[1].set_ylabel("ping RTT\n(ms)")
    axes[2].plot([(k + 0.5) * 0.5 for k in gx], [8 * acc[k] / 0.5 / 1e6 for k in gx], color=S.ACTION, lw=1.0)
    axes[2].set_ylim(0, 12)
    axes[2].set_ylabel("goodput\n(Mbit/s)")
    per_s = defaultdict(list)
    for t, v in series:
        per_s[int(t)].append(v)
    xs = sorted(per_s)
    axes[3].step(xs, [100 * sum(1 for v in per_s[x] if v > 100) / len(per_s[x]) for x in xs], where="post", color=S.ACTION, lw=1.0)
    axes[3].set_ylabel("pings with\nRTT > 100 ms (%)")
    axes[3].set_xlabel("time (s)")
    for ax in axes[1:]:
        S.clean(ax)
        S.shade_after(ax, t_ctrl, t_end)
        S.event(ax, t_launch)
        S.event(ax, t_ctrl, state=True)
        ax.set_xlim(0, t_end)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
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
    fig, axes = plt.subplots(4, ncol, figsize=(S.DOUBLE_COL, 5.0), sharex="col", gridspec_kw={"height_ratios": [0.85, 1, 0.9, 0.75]})
    hs = ns3_column(axes[:, 0], Path(args.hotspot), args.hotspot_seed, args.hotspot_workflow,
                    "(a) ns-3 hotspot: KPM$\\rightarrow$QoE pred.$\\rightarrow$steering$\\rightarrow$RC", "prb")
    ns = ns3_column(axes[:, 1], Path(args.night), args.night_seed, "energy_saving",
                    "(b) ns-3 night: KPM$\\rightarrow$energy saving$\\rightarrow$RC", "power")
    if args.d3:
        d3_column(axes[:, 2], Path(args.d3), args.d3_rep)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    extra = [(plt.Line2D([], [], color=S.ACTION, lw=1.0), "workflow applied"),
             (plt.Line2D([], [], color=S.NOACTION, ls="--", lw=0.8), "same seed, no action"),
             (plt.Line2D([], [], color=S.EVENT, ls=":", lw=0.8), "control dispatched"),
             (plt.Line2D([], [], color=S.STATE, lw=0.8), "cell off / queue swap")]
    fig.legend(handles + [h for h, _ in extra], labels + [l for _, l in extra], ncol=8, loc="upper center",
               bbox_to_anchor=(0.5, 1.035), handlelength=1.5, columnspacing=1.0)
    fig.align_ylabels(axes[:, 0]); fig.align_ylabels(axes[:, 1])
    if args.d3:
        fig.align_ylabels(axes[1:, 2])
    fig.tight_layout(h_pad=0.35, w_pad=0.6)
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    summ = {}
    for name, res, (th, tot, srv), (thn, totn, srvn) in (("hotspot", *hs), ("night", *ns)):
        after = lambda xs, ys: [y for x, y in zip(xs, ys) if x > res["act_sim_time_s"] + 0.5]  # noqa: E731
        summ[name] = {"commands": res.get("commands_dispatched_sim_s"),
                      "served_after_mean": round(sum(after(th, srv)) / len(after(th, srv)), 2),
                      "served_after_noop_mean": round(sum(after(thn, srvn)) / len(after(thn, srvn)), 2),
                      "dl_after_mean": round(sum(after(th, tot)) / len(after(th, tot)), 2),
                      "dl_after_noop_mean": round(sum(after(thn, totn)) / len(after(thn, totn)), 2)}
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
