#!/usr/bin/env python3
"""One double-column figure with everything the magazine page budget allows (candidate replacement of Fig. 5).

  (a) rule accuracy per batch, (b) open-world accuracy on intents no operator template solves, both from
      paper_results/combined_results.csv (95% intent-clustered bootstrap CIs, as in the paper tables);
  (c) network effect of deployed AppWeaver workflows, live measurements (mean +- sd over seeds / repeats):
      D2 ns-3 hotspot steering and night energy saving (run_twin_validation.py --layout), D3 CoDel on a real
      bottleneck (tc_dataplane/run_tc_demo.py). Panel (c) is drawn only when the batch directories are given.

  python make_compact_figure.py [--d2-hotspot DIR] [--d2-night DIR] [--d3 DIR] [--out fig_results_compact]
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "paper_results" / "combined_results.csv"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"], "font.size": 7.5,
                     "axes.linewidth": 0.6, "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight", "pdf.fonttype": 42})
# Okabe-Ito, fixed order per method (same palette as make_paper_figures.py)
METHODS = [("manual_rule", "Rule router", "#999999"), ("llm_only", "LLM (catalog)", "#E69F00"),
           ("langgraph_agentcard", "AppWeaver", "#0072B2"), ("appweaver_mem", "AppWeaver + tpl + memory", "#009E73")]
BATCHES = [("A", 0, "A"), ("B", 8, "B, k=8"), ("B", 0, "B, all"), ("C", 0, "C")]


def load_csv():
    rows = {}
    with CSV.open() as handle:
        for r in csv.DictReader(handle):
            rows[(r["role"], int(r["retrieval_k"] or 0), r["method"])] = r
    return rows


def bars(ax, rows, key, title):
    width = 0.8 / len(METHODS)
    for j, (m, label, color) in enumerate(METHODS):
        xs, ys, lo, hi = [], [], [], []
        for i, (role, k, _) in enumerate(BATCHES):
            r = rows.get((role, k, m))
            if not r or r.get(key) in ("", None):
                continue
            v = float(r[key]) * 100
            xs.append(i - 0.4 + width * (j + 0.5)); ys.append(v)
            lo.append(v - float(r[f"{key}_ci_lo"] or r[key]) * 100); hi.append(float(r[f"{key}_ci_hi"] or r[key]) * 100 - v)
        ax.bar(xs, ys, width * 0.92, color=color, label=label, yerr=[lo, hi], error_kw={"lw": 0.5, "capsize": 1.2})
        for x, y in zip(xs, ys):
            if y < 0.5:
                ax.text(x, 1.5, "0", ha="center", va="bottom", fontsize=5.5, color="#444")
    ax.set_xticks(range(len(BATCHES)), [b[2] for b in BATCHES], fontsize=7)
    ax.set_ylim(0, 105); ax.set_ylabel("%"); ax.set_title(title, fontsize=7.5)
    ax.grid(axis="y", lw=0.3, alpha=0.5); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def d2_live_changes(batch: Path, workflow: str):
    """Per live seed: % change vs the same seed's no-op for throughput, hot/remaining PRB, energy, delay."""
    res = {}
    for p in sorted((batch / "runs").glob(f"live_s*_{workflow}")):
        seed = p.name.split("_")[1]
        wf, noop = json.loads((p / "result.json").read_text()), batch / "runs" / f"live_{seed}_noop" / "result.json"
        if not noop.exists() or not wf.get("ok"):
            continue
        nb = json.loads(noop.read_text())
        pct = lambda a, b: 100.0 * (a - b) / b if b else None  # noqa: E731
        hot = sorted({str(s["from"]) for s in (wf.get("policy") or {}).get("shed", [])})
        row = {"throughput": pct(wf["kpi"]["dl_throughput_mbps"], nb["kpi"]["dl_throughput_mbps"]),
               "energy": pct(wf["kpi"]["energy_j_per_s"], nb["kpi"]["energy_j_per_s"]),
               "delay": pct(wf["kpi"]["dl_delay_ms"], nb["kpi"]["dl_delay_ms"])}
        if hot:
            row["hot_prb"] = pct(sum(wf["kpi_per_cell"][c]["prb_used_dl"] for c in hot), sum(nb["kpi_per_cell"][c]["prb_used_dl"] for c in hot))
        res[seed] = row
    return res


def mean_sd(values):
    v = [x for x in values if x is not None]
    return (statistics.fmean(v), statistics.stdev(v) if len(v) > 1 else 0.0, len(v)) if v else (None, None, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d2-hotspot", default="")
    ap.add_argument("--d2-night", default="")
    ap.add_argument("--d3", default="")
    ap.add_argument("--out", default=str(HERE / "fig_results_compact"))
    args = ap.parse_args()
    rows = load_csv()
    impact = []  # (label, mean, sd, n, color)
    if args.d2_hotspot:
        ch = d2_live_changes(Path(args.d2_hotspot), "qoe_steering")
        for key, label in (("hot_prb", "QoE steering: hot-cell PRB"), ("throughput", "QoE steering: throughput")):
            impact.append((label, *mean_sd([r.get(key) for r in ch.values()]), "#0072B2"))
    if args.d2_night:
        ch = d2_live_changes(Path(args.d2_night), "energy_saving")
        for key, label in (("energy", "Energy saving: gNB energy"), ("throughput", "Energy saving: throughput")):
            impact.append((label, *mean_sd([r.get(key) for r in ch.values()]), "#D55E00"))
    if args.d3:
        s = json.loads((Path(args.d3) / "summary.json").read_text())
        reps = s["repeats"]
        rtt = [100 * (r["rtt_after"]["median_ms"] - r["rtt_before"]["median_ms"]) / r["rtt_before"]["median_ms"] for r in reps if r.get("rtt_after")]
        gp = [100 * (r["goodput_after_mbps"] - r["goodput_before_mbps"]) / r["goodput_before_mbps"] for r in reps if r.get("goodput_after_mbps")]
        impact += [("CoDel: RTT (median)", *mean_sd(rtt), "#56B4E9"), ("CoDel: goodput", *mean_sd(gp), "#56B4E9")]

    ncol = 3 if impact else 2
    fig, axes = plt.subplots(1, ncol, figsize=(7.16, 2.15), gridspec_kw={"width_ratios": [1, 1, 1.05][:ncol]})
    bars(axes[0], rows, "rule_accuracy", "(a) Workflow accuracy (rule)")
    bars(axes[1], rows, "open_world_nontpl_rule_accuracy", "(b) Open-world, no template fits")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=6.5, handlelength=1.0, bbox_to_anchor=(0.5, 1.06))
    if impact:
        ax = axes[2]
        ys = list(range(len(impact)))[::-1]
        ax.barh(ys, [m for _, m, *_ in impact], xerr=[s for _, _, s, *_ in impact], color=[c for *_, c in impact], height=0.6,
                error_kw={"lw": 0.5, "capsize": 1.2})
        ax.set_yticks(ys, [l for l, *_ in impact], fontsize=6)
        for y, (_, m, sd, n, _) in zip(ys, impact):
            ax.text(m + (sd + 3 if m >= 0 else -sd - 3), y, f"{m:+.0f}%", va="center", ha="left" if m >= 0 else "right", fontsize=6)
        lim = max(abs(m) + sd for _, m, sd, *_ in impact) + 25
        ax.set_xlim(-lim, max(25, max(m + sd for _, m, sd, *_ in impact) + 25))
        ax.axvline(0, color="#444", lw=0.5); ax.set_xlabel("change vs no action (%)")
        ax.set_title("(c) Network effect, live measurement", fontsize=7.5)
        ax.grid(axis="x", lw=0.3, alpha=0.5); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout(w_pad=0.6)
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}")
    (Path(args.out).with_suffix(".json")).write_text(json.dumps({"impact": impact}, indent=2))
    print(json.dumps({"impact": impact}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
