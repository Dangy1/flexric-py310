#!/usr/bin/env python3
"""Fig. 5 candidate: composition accuracy and the KPI impact of the deployed workflows, one figure.

  (a) rule accuracy per batch, (b) open-world accuracy on intents no operator template solves; from
      paper_results/combined_results.csv (95% intent-clustered bootstrap CIs, as in the repository tables);
  (c) KPI change caused by the deployed workflow, twin prediction next to live measurement, mean +- sd over
      5 seed pairs (ns-3, D2) or 5 repeats (real link, D3; no twin there). Change = workflow run vs the same
      instance and seed without the action. Users served = UEs receiving >= half their offered rate,
      averaged over the KPI window (ns-3 PDCP trace).

  python make_compact_figure.py --d2-hotspot RUNS/<D2_hotspot> --d2-night RUNS/<D2_night> --d3 RUNS/<D3> \
      [--traces BUILD_RUNS] [--out fig_results_compact]

--traces: directory holding the same D2 batches with their ns-3 traces (the build tree); needed for
users served, which result.json does not carry.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import aw_style as S
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "paper_results" / "combined_results.csv"
METHODS = ["manual_rule", "llm_only", "langgraph_agentcard", "appweaver_mem"]
BATCHES = [("A", 0, "A"), ("B", 8, "B, k=8"), ("B", 0, "B, all"), ("C", 0, "C")]
OFFERED_MBPS = 3.2


def load_csv():
    with CSV.open() as handle:
        return {(r["role"], int(r["retrieval_k"] or 0), r["method"]): r for r in csv.DictReader(handle)}


def bars(ax, rows, key, title):
    width = 0.8 / len(METHODS)
    for j, m in enumerate(METHODS):
        xs, ys, lo, hi = [], [], [], []
        for i, (role, k, _) in enumerate(BATCHES):
            r = rows.get((role, k, m))
            if not r or r.get(key) in ("", None):
                continue
            v = float(r[key]) * 100
            xs.append(i - 0.4 + width * (j + 0.5)); ys.append(v)
            lo.append(v - float(r[f"{key}_ci_lo"] or r[key]) * 100); hi.append(float(r[f"{key}_ci_hi"] or r[key]) * 100 - v)
        ax.bar(xs, ys, width * 0.9, color=S.METHOD_COLOR[m], label=S.METHOD_LABEL[m], yerr=[lo, hi],
               error_kw={"lw": 0.5, "capsize": 1.2, "ecolor": "#333"})
        for x, y in zip(xs, ys):
            if y < 0.5:
                ax.text(x, 1.5, "0", ha="center", va="bottom", fontsize=5.5, color="#444")
    ax.set_xticks(range(len(BATCHES)), [b[2] for b in BATCHES])
    ax.set_ylim(0, 105); ax.set_ylabel("correct workflows (%)")
    S.clean(ax); S.panel_label(ax, title)


def served_users(run_dir: Path, t0: float, t1: float):
    rx = defaultdict(float)
    for line in (run_dir / "ns3_out" / "DlPdcpStats.txt").open():
        f = line.split()
        if len(f) < 11 or line.startswith("%"):
            continue
        if float(f[0]) >= t0 - 1e-9 and float(f[1]) <= t1 + 1e-9:
            rx[int(f[3])] += float(f[9])
    return sum(1 for b in rx.values() if 8 * b / (t1 - t0) / 1e6 >= OFFERED_MBPS / 2)


def d2_changes(batch: Path, traces: Path, workflow: str):
    """{role: {kpi: [pct change per pair]}} for role twin (seed p) and live (seed p+100)."""
    out = {"twin": defaultdict(list), "live": defaultdict(list)}
    pct = lambda a, b: 100.0 * (a - b) / b if b else None  # noqa: E731
    for wf_dir in sorted((batch / "runs").glob(f"*_s*_{workflow}")):
        role, seed = wf_dir.name.split("_")[0], wf_dir.name.split("_")[1]
        noop_dir = batch / "runs" / f"{role}_{seed}_noop"
        if not noop_dir.exists():
            continue
        wf, nb = json.loads((wf_dir / "result.json").read_text()), json.loads((noop_dir / "result.json").read_text())
        if not (wf.get("ok") and nb.get("ok")):
            continue
        d = out[role]
        d["throughput"].append(pct(wf["kpi"]["dl_throughput_mbps"], nb["kpi"]["dl_throughput_mbps"]))
        d["energy"].append(pct(wf["kpi"]["energy_j_per_s"], nb["kpi"]["energy_j_per_s"]))
        hot = sorted({str(s["from"]) for s in (wf.get("policy") or {}).get("shed", [])})
        if hot:
            d["hot_prb"].append(pct(sum(wf["kpi_per_cell"][c]["prb_used_dl"] for c in hot),
                                    sum(nb["kpi_per_cell"][c]["prb_used_dl"] for c in hot)))
        t0, t1 = wf["kpi_window_sim_s"]
        tw, tn = traces / batch.name / "runs" / wf_dir.name, traces / batch.name / "runs" / noop_dir.name
        if (tw / "ns3_out").exists() and (tn / "ns3_out").exists():
            d["served"].append(pct(served_users(tw, t0, t1), served_users(tn, t0, t1)))
    return out


def ms(v):
    v = [x for x in v if x is not None]
    return (statistics.fmean(v), statistics.stdev(v) if len(v) > 1 else 0.0, len(v)) if v else (None, None, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d2-hotspot", default="")
    ap.add_argument("--d2-night", default="")
    ap.add_argument("--d3", default="")
    ap.add_argument("--traces", default=str(Path.home() / "flexric/build/examples/xApp/python3/evaluation/twin/build/runs"))
    ap.add_argument("--out", default=str(HERE / "fig_results_compact"))
    args = ap.parse_args()
    rows = load_csv()
    traces = Path(args.traces)
    items = []  # (group, label, twin (m, sd, n) or None, live (m, sd, n))
    if args.d2_hotspot:
        ch = d2_changes(Path(args.d2_hotspot), traces, "qoe_steering")
        for k, lab in (("throughput", "DL throughput"), ("served", "users served"), ("hot_prb", "source-cell PRB")):
            items.append(("QoE steering", lab, ms(ch["twin"][k]), ms(ch["live"][k])))
    if args.d2_night:
        ch = d2_changes(Path(args.d2_night), traces, "energy_saving")
        for k, lab in (("energy", "gNB energy"), ("throughput", "DL throughput"), ("served", "users served")):
            items.append(("Energy saving", lab, ms(ch["twin"][k]), ms(ch["live"][k])))
    if args.d3:
        reps = json.loads((Path(args.d3) / "summary.json").read_text())["repeats"]
        rtt = [100 * (r["rtt_after"]["median_ms"] - r["rtt_before"]["median_ms"]) / r["rtt_before"]["median_ms"] for r in reps]
        gp = [100 * (r["goodput_after_mbps"] - r["goodput_before_mbps"]) / r["goodput_before_mbps"] for r in reps]
        items += [("CoDel", "RTT, median", None, ms(rtt)), ("CoDel", "goodput", None, ms(gp))]

    fig = plt.figure(figsize=(S.DOUBLE_COL, 2.45))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.25], wspace=0.42)
    ax_a, ax_b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    bars(ax_a, rows, "rule_accuracy", "(a) All intents")
    bars(ax_b, rows, "open_world_nontpl_rule_accuracy", "(b) Open-world, no template fits")
    ax_b.set_ylabel("")
    h, l = ax_a.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, bbox_to_anchor=(0.36, 1.0), handlelength=1.0, columnspacing=1.2)
    if items:
        ax = fig.add_subplot(gs[2])
        n = len(items)
        ys = [n - 1 - i for i in range(n)]
        for y, (grp, lab, twin, live) in zip(ys, items):
            if live[0] is not None:
                ax.barh(y + (0.17 if twin else 0), live[0], height=0.32 if twin else 0.5, color=S.MEAS, xerr=live[1],
                        error_kw={"lw": 0.5, "capsize": 1.0, "ecolor": "#333"})
                ax.text(live[0] + (live[1] + 4 if live[0] >= 0 else -live[1] - 4), y + (0.17 if twin else 0), f"{live[0]:+.0f}",
                        va="center", ha="left" if live[0] >= 0 else "right", fontsize=5.6)
            if twin and twin[0] is not None:
                ax.barh(y - 0.17, twin[0], height=0.32, color=S.PRED, xerr=twin[1], error_kw={"lw": 0.5, "capsize": 1.0, "ecolor": "#333"})
        ax.set_yticks(ys, [lab for _, lab, _, _ in items])
        ax.axvline(0, color="#444", lw=0.5)
        groups = []
        for y, it in zip(ys, items):
            if not groups or groups[-1][0] != it[0]:
                groups.append([it[0], y, y])
            groups[-1][2] = y
        for name, top, bottom in groups:
            ax.text(1.02, (top + bottom) / 2, name, transform=ax.get_yaxis_transform(), rotation=270, va="center", ha="left", fontsize=5.6, color="#444")
            if bottom != ys[-1]:
                ax.axhline(bottom - 0.5, color="#bbb", lw=0.4)
        lim = max(abs(it[3][0]) + it[3][1] for it in items) + 22
        ax.set_xlim(-lim, 40)
        ax.set_xlabel("change vs no action (%)")
        S.clean(ax, grid="x")
        S.panel_label(ax, "(c) KPI impact of the deployed workflow")
        ax.legend([plt.Rectangle((0, 0), 1, 1, color=S.MEAS), plt.Rectangle((0, 0), 1, 1, color=S.PRED)],
                  ["live, measured", "twin, predicted"], loc="upper left", fontsize=5.8, handlelength=0.9)
    fig.subplots_adjust(top=0.83, bottom=0.17, left=0.06, right=0.95)
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    out = [{"group": g, "kpi": l, "twin": t, "live": v} for g, l, t, v in items]
    Path(args.out).with_suffix(".json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
