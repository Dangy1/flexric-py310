#!/usr/bin/env python3
"""Build the AppWeaver paper figures, LaTeX tables and CSV from evaluation batches.

Every number is recomputed from a batch's `records.jsonl`; `manifest.json` supplies the model,
inference settings and registry size. Nothing is read from the May-2026 batches.

Inputs
  --batch-a RUN            Batch A: intents_50.json, paper registry (FLEXRIC_RAPP_DIRECTORY unset)
  --batch-b RUN [RUN ...]  Batch B: intents_v2.json with the rApp Directory; one run per
                           retrieval depth (labelled from manifest -> retrieval_k)

Outputs (into --out, default: this directory)
  combined_results.csv           one row per (batch, method): value, ci_lo, ci_hi per metric
  results_table.tex              Batch A table (Table II)
  results_table_registry.tex     Batch B table (written only with --batch-b)
  results_macros.tex             \\awres{A|B8|Ball}{method}{metric} for numbers cited in the text
  figures/fig_accuracy.[pdf|png]       Batch A known vs open-world accuracy, 95% CI
  figures/fig_reliability.[pdf|png]    acknowledged tool calls, conflict recall, conflict FP rate
  figures/fig_latency.[pdf|png]        per-record latency distribution (log scale)
  figures/fig_registry_splits.[pdf|png] Batch B accuracy per split and retrieval depth
  figures/fig_hallucination.[pdf|png]  hallucinated references per record

Confidence intervals (stated in every caption/README):
  * accuracies and acknowledged-call rate: intent-clustered percentile bootstrap (2000 resamples,
    seed 0). Repeats of one intent are correlated, so intents, not records, are resampled.
  * conflict recall / false-positive rate: Wilson score interval over records (only 6 seeded
    intents, too few clusters for a bootstrap).

Accuracy is "accepted" accuracy (exact ordered match with any chain in the intent's
`accepted_workflows`; for intents_50 that is the single labelled chain) unless a column says
"exact" or "set". See evaluation/METRICS.md.

Run inside the flexric-py310 conda env:
  python make_paper_figures.py --batch-a ../runs/<A> --batch-b ../runs/<B_k8> ../runs/<B_k0>
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import sys

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze_results import conflict_flagged  # noqa: E402  (same detection rule as the batch summaries)
import matplotlib.pyplot as plt

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.linewidth": 0.6,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 7,
        "legend.fontsize": 6.5,
        "legend.frameon": False,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

SINGLE_COL = 3.5  # inches
DOUBLE_COL = 7.16

METHODS: List[Tuple[str, str]] = [
    ("manual_rule", "Rule\nrouter"),
    ("single_xapp", "Single\napp"),
    ("llm_blind", "LLM\n(no catalog)"),
    ("llm_only", "LLM\n(catalog)"),
    ("agentcard_no_repair", "AppWeaver\n(no repair)"),
    ("langgraph_agentcard", "AppWeaver"),
]
LABEL = dict(METHODS)
SPLITS = [("known", "Known"), ("open_world", "Open-world"), ("unseen_capability", "Unseen capability")]

# Okabe-Ito, validated with the dataviz palette checker (light surface); hatches carry identity in print.
C_BLUE, C_ORANGE, C_GREEN, C_VERM, C_SKY, C_GRAY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#999999"
HATCHES = ["", "//", ".."]
BOOT_N = 2000


# ---------------------------------------------------------------- loading
class Batch:
    def __init__(self, path: Path, role: str) -> None:
        self.path = path
        self.role = role
        self.id = path.name
        self.manifest: Dict[str, Any] = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        records_file = path / "records.jsonl"
        if not records_file.exists():
            records_file = path / "records.partial.jsonl"  # unfinished batch, for previews only
        self.complete = records_file.name == "records.jsonl"
        self.records = [json.loads(line) for line in records_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.records = [r for r in self.records if r.get("method_available") is not False]
        self.methods = [m for m, _ in METHODS if any(r.get("method") == m for r in self.records)]

    @property
    def model(self) -> str:
        models = {str(r.get("planner_model")) for r in self.records if r.get("planner_model")}
        if models:
            return ",".join(sorted(models))
        for provider in self.manifest.get("providers", []):
            if provider.get("enabled") and provider.get("id") != "claude":
                return str(provider.get("model"))
        return "unknown"

    @property
    def settings(self) -> Dict[str, Any]:
        return dict(self.manifest.get("planner_inference_settings") or {})

    @property
    def retrieval_k(self) -> int:
        return int((self.manifest.get("evaluation_runtime_config") or {}).get("retrieval_k") or 0)

    @property
    def preliminary(self) -> bool:
        return not self.model.startswith("gpt-oss")

    def describe(self) -> str:
        reg = self.manifest.get("registry") or {}
        repeats = len({r.get("repeat_index") for r in self.records})
        intents = len({r.get("intent_id") for r in self.records})
        return (
            f"`{self.id}` - {intents} intents x {len(self.methods)} methods x {repeats} repeats = "
            f"{len(self.records)} records; planner `{self.model}`, settings {json.dumps(self.settings, sort_keys=True)}, "
            f"registry {reg.get('agent_count', '?')} cards, retrieval_k={self.retrieval_k}"
            + ("" if self.complete else " **(INCOMPLETE: partial records)**")
            + (" **PRELIMINARY (not the paper's model)**" if self.preliminary else "")
        )


def split_of(record: Dict[str, Any]) -> str:
    return str(record.get("intent_split") or ("open_world" if record.get("intent_open_world") else "known"))


# ---------------------------------------------------------------- statistics
def _clusters(records: Sequence[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        groups[str(r.get("intent_id"))].append(r)
    return [groups[k] for k in sorted(groups)]


def ratio_bootstrap(records: Sequence[Dict[str, Any]], num: Callable[[Dict[str, Any]], float],
                    den: Callable[[Dict[str, Any]], float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Point estimate sum(num)/sum(den) with an intent-clustered percentile bootstrap CI."""
    clusters = _clusters(records)
    sums = [(sum(num(r) for r in c), sum(den(r) for r in c)) for c in clusters]
    total_den = sum(d for _, d in sums)
    if not clusters or total_den == 0:
        return None, None, None
    point = sum(n for n, _ in sums) / total_den
    if len(clusters) == 1:
        return point, None, None
    rng = random.Random(0)
    stats = []
    for _ in range(BOOT_N):
        draw = [sums[rng.randrange(len(sums))] for _ in sums]
        d = sum(x for _, x in draw)
        if d:
            stats.append(sum(x for x, _ in draw) / d)
    stats.sort()
    return point, stats[int(0.025 * (len(stats) - 1))], stats[int(math.ceil(0.975 * (len(stats) - 1)))]


def wilson(successes: int, total: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if total <= 0:
        return None, None, None
    z = 1.959964
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered))) - 1))]


def flag(key: str) -> Callable[[Dict[str, Any]], float]:
    return lambda r: 1.0 if r.get(key) is True else 0.0


ONE = lambda r: 1.0  # noqa: E731


def method_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"records": len(records), "intents": len({r.get("intent_id") for r in records}),
                           "repeats": len({r.get("repeat_index") for r in records})}
    out["accuracy"] = ratio_bootstrap(records, flag("workflow_match_any_accepted"), ONE)
    out["exact_accuracy"] = ratio_bootstrap(records, flag("workflow_match"), ONE)
    out["set_accuracy"] = ratio_bootstrap(records, flag("workflow_set_match"), ONE)
    for split, _ in SPLITS:
        subset = [r for r in records if split_of(r) == split]
        out[f"{split}_records"] = len(subset)
        out[f"{split}_intents"] = len({r.get("intent_id") for r in subset})
        out[f"{split}_accuracy"] = ratio_bootstrap(subset, flag("workflow_match_any_accepted"), ONE)

    calls = lambda r: [c for c in (r.get("tool_calls") or []) if c.get("acknowledged") is not None]  # noqa: E731
    out["tool_calls"] = sum(len(r.get("tool_calls") or []) for r in records)
    out["ack_rate"] = ratio_bootstrap(records, lambda r: sum(1 for c in calls(r) if c.get("acknowledged") is True),
                                      lambda r: len(calls(r)))
    out["launch_rate"] = ratio_bootstrap(records, lambda r: sum(1 for c in (r.get("tool_calls") or []) if c.get("status") == "success"),
                                         lambda r: len(r.get("tool_calls") or []))

    seeded = [r for r in records if r.get("conflict_label") is True]
    unseeded = [r for r in records if r.get("conflict_label") is False]
    out["seeded_records"] = len(seeded)
    out["conflict_recall"] = wilson(sum(1 for r in seeded if conflict_flagged(r)), len(seeded))
    out["conflict_fp_rate"] = wilson(sum(1 for r in unseeded if conflict_flagged(r)), len(unseeded))
    out["seeded_recovered"] = wilson(sum(1 for r in seeded if (r.get("execution_artifacts") or {}).get("internal_recovery_succeeded")), len(seeded))

    out["hallucinated_refs"] = sum(int(r.get("hallucinated_reference_count") or 0) for r in records)
    out["hallucinated_per_record"] = ratio_bootstrap(records, lambda r: float(r.get("hallucinated_reference_count") or 0), ONE)
    out["records_with_hallucination"] = sum(1 for r in records if int(r.get("hallucinated_reference_count") or 0) > 0)

    retr = [r for r in records if r.get("retrieval_hit") is not None]
    out["retrieval_hit_rate"] = ratio_bootstrap(retr, flag("retrieval_hit"), ONE) if retr else (None, None, None)
    compat = [r for r in records if r.get("compat_ok") is not None]
    out["compat_ok_rate"] = wilson(sum(1 for r in compat if r.get("compat_ok") is True), len(compat)) if compat else (None, None, None)

    chars = [int((r.get("retrieval") or {}).get("prompt_chars") or 0) for r in records]
    chars = [c for c in chars if c > 0]
    out["prompt_chars_median"] = percentile(chars, 0.5) if chars else None
    # Open-world labels use base-registry apps only; this share shows how often a directory rApp entered the chain.
    ow = [r for r in records if r.get("intent_split") == "open_world"]
    out["open_world_rapp_rate"] = (sum(1 for r in ow if any(str(x).upper().startswith("RAPP.") for x in (r.get("generated_workflow") or [])))
                                   / len(ow)) if ow else None

    lat = [float(r["orchestration_latency_ms"]) for r in records if r.get("orchestration_latency_ms") is not None]
    out["latency_values_ms"] = lat
    out["latency_n"] = len(lat)
    out["latency_mean_ms"] = sum(lat) / len(lat) if lat else None
    out["latency_sd_ms"] = (math.sqrt(sum((x - out["latency_mean_ms"]) ** 2 for x in lat) / (len(lat) - 1)) if len(lat) > 1 else None)
    out["latency_median_ms"] = percentile(lat, 0.5)
    out["latency_p95_ms"] = percentile(lat, 0.95)
    out["latency_max_ms"] = max(lat) if lat else None
    out["planner_cached_records"] = sum(1 for r in records if r.get("planner_cached") is True)
    return out


def batch_metrics(batch: Batch) -> Dict[str, Dict[str, Any]]:
    return {m: method_metrics([r for r in batch.records if r.get("method") == m]) for m in batch.methods}


# ---------------------------------------------------------------- formatting
def pct(triple: Tuple[Optional[float], Optional[float], Optional[float]], ci: bool = True) -> str:
    v, lo, hi = triple
    if v is None:
        return "--"
    if not ci or lo is None:
        return f"{100 * v:.1f}"
    return f"{100 * v:.1f} {{\\scriptsize[{100 * lo:.0f},{100 * hi:.0f}]}}"


def pct_md(triple: Tuple[Optional[float], Optional[float], Optional[float]]) -> str:
    v, lo, hi = triple
    if v is None:
        return "--"
    return f"{100 * v:.1f}%" + (f" [{100 * lo:.0f}, {100 * hi:.0f}]" if lo is not None else "")


def secs(ms: Optional[float], tex: bool = True) -> str:
    if ms is None:
        return "--"
    return f"{ms / 1000:.2f}" if ms >= 10 else ("$<$0.01" if tex else "<0.01")


def _yerr(triples: Sequence[Tuple[Optional[float], Optional[float], Optional[float]]]) -> Tuple[List[float], List[List[float]]]:
    vals, lo, hi = [], [], []
    for v, l, h in triples:
        v = float("nan") if v is None else v
        vals.append(v)
        lo.append(0.0 if l is None or v != v else max(0.0, v - l))
        hi.append(0.0 if h is None or v != v else max(0.0, h - v))
    return vals, [lo, hi]


def grouped(ax, groups: List[List[Tuple]], labels: List[str], colors: List[str], width: float = 0.8,
            value_labels: bool = True) -> None:
    n = len(groups)
    sw = width / n
    for i, (triples, label, color) in enumerate(zip(groups, labels, colors)):
        vals, err = _yerr(triples)
        xs = [j - width / 2 + sw * (i + 0.5) for j in range(len(vals))]
        ax.bar(xs, vals, width=sw * 0.9, label=label, color=color, hatch=HATCHES[i % len(HATCHES)],
               edgecolor="black", linewidth=0.4, zorder=2)
        ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor="black", elinewidth=0.5, capsize=1.2, capthick=0.5, zorder=3)
        if value_labels:
            for x, v, top in zip(xs, vals, err[1]):
                if v == v:
                    ax.text(x, v + top + 0.015, f"{100 * v:.0f}", ha="center", va="bottom", fontsize=5.5, zorder=4)


def _finish(ax, ylabel: str, methods: List[str]) -> None:
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([LABEL[m] for m in methods], fontsize=5.6)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1.12)
    ax.yaxis.grid(True, linewidth=0.3, alpha=0.5)
    ax.set_axisbelow(True)
    if "langgraph_agentcard" in methods:
        i = methods.index("langgraph_agentcard")
        ax.axvspan(i - 0.5, i + 0.5, color="#F2F2F2", zorder=0)


def save(fig, out: Path, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{name}.{ext}")
    plt.close(fig)


# ---------------------------------------------------------------- figures
def fig_accuracy(batch: Batch, metrics: Dict[str, Dict[str, Any]], out: Path) -> None:
    methods = batch.methods
    m0 = metrics[methods[0]]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.0))
    grouped(ax, [[metrics[m]["known_accuracy"] for m in methods], [metrics[m]["open_world_accuracy"] for m in methods]],
            [f"Known intents ({m0['known_intents']} intents)", f"Open-world intents ({m0['open_world_intents']} intents)"],
            [C_BLUE, C_ORANGE], width=0.72)
    _finish(ax, "Workflow accuracy", methods)
    ax.legend(ncol=2, loc="upper left", bbox_to_anchor=(0, 1.16), handlelength=1.4, columnspacing=1.0)
    save(fig, out, "fig_accuracy")


def fig_reliability(batch: Batch, metrics: Dict[str, Dict[str, Any]], out: Path) -> None:
    methods = batch.methods
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.0))
    # Seeded conflicts are refused by the portal lease for every method that reaches the busy agent;
    # what differs is whether the method then reaches a clean execution (internal recovery).
    grouped(ax, [[metrics[m]["ack_rate"] for m in methods], [metrics[m]["conflict_recall"] for m in methods],
                 [metrics[m]["seeded_recovered"] for m in methods]],
            ["Acknowledged tool calls", "Seeded conflict refused", "Seeded conflict recovered"],
            [C_GREEN, C_VERM, C_SKY])
    _finish(ax, "Rate", methods)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.16), handlelength=1.4, columnspacing=0.8)
    save(fig, out, "fig_reliability")


def fig_latency(batch: Batch, metrics: Dict[str, Dict[str, Any]], out: Path) -> None:
    methods = [m for m in batch.methods if metrics[m]["latency_values_ms"]]
    data = [[max(v, 0.1) / 1000.0 for v in metrics[m]["latency_values_ms"]] for m in methods]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.0))
    ax.boxplot(data, positions=range(len(methods)), widths=0.5, whis=(5, 95), showfliers=True,
               flierprops={"marker": ".", "markersize": 2, "markerfacecolor": C_GRAY, "markeredgecolor": "none"},
               medianprops={"color": C_VERM, "linewidth": 0.9}, boxprops={"linewidth": 0.5},
               whiskerprops={"linewidth": 0.5}, capprops={"linewidth": 0.5})
    ax.axhline(1.0, color=C_GRAY, linewidth=0.6, linestyle=(0, (3, 2)))
    ax.text(len(methods) - 0.5, 1.08, "Non-RT RIC loop (1 s)", ha="right", va="bottom", fontsize=5.5, color="#555555")
    ax.set_yscale("log")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([LABEL[m] for m in methods], fontsize=5.6)
    ax.set_ylabel("Intent-to-plan latency (s, log)")
    ax.yaxis.grid(True, which="major", linewidth=0.3, alpha=0.5)
    ax.set_axisbelow(True)
    save(fig, out, "fig_latency")


def fig_registry_splits(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path) -> None:
    fig, axes = plt.subplots(1, len(batches), figsize=(DOUBLE_COL if len(batches) > 1 else SINGLE_COL, 2.0), sharey=True,
                             squeeze=False)
    for ax, batch in zip(axes[0], batches):
        metrics = all_metrics[batch.id]
        methods = batch.methods
        m0 = metrics[methods[0]]
        splits = [(s, label) for s, label in SPLITS if m0[f"{s}_intents"]]
        grouped(ax, [[metrics[m][f"{s}_accuracy"] for m in methods] for s, _ in splits],
                [f"{label} ({m0[f'{s}_intents']} intents)" for s, label in splits], [C_BLUE, C_ORANGE, C_GREEN])
        _finish(ax, "Workflow accuracy" if ax is axes[0][0] else "", methods)
        ax.set_title(f"rApp Directory, retrieval k={batch.retrieval_k or 'all'}", fontsize=7, pad=14)
    axes[0][0].legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.12), handlelength=1.4, columnspacing=0.9)
    save(fig, out, "fig_registry_splits")


def fig_hallucination(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path) -> None:
    methods = [m for m, _ in METHODS if any(m in b.methods for b in batches)]
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 1.9))
    colors = [C_BLUE, C_ORANGE, C_GREEN, C_SKY]
    groups, labels = [], []
    for batch in batches:
        metrics = all_metrics[batch.id]
        groups.append([metrics[m]["hallucinated_per_record"] if m in metrics else (None, None, None) for m in methods])
        labels.append(batch_label(batch))
    n = len(groups)
    sw = 0.8 / n
    ymax = 0.0
    for i, (triples, label) in enumerate(zip(groups, labels)):
        vals, err = _yerr(triples)
        xs = [j - 0.4 + sw * (i + 0.5) for j in range(len(vals))]
        ax.bar(xs, vals, width=sw * 0.9, label=label, color=colors[i % 4], hatch=HATCHES[i % 3], edgecolor="black", linewidth=0.4, zorder=2)
        ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor="black", elinewidth=0.5, capsize=1.2, capthick=0.5, zorder=3)
        ymax = max([ymax] + [v + e for v, e in zip(vals, err[1]) if v == v])
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([LABEL[m] for m in methods], fontsize=5.6)
    ax.set_ylabel("Hallucinated refs / record")
    ax.set_ylim(0, max(0.5, ymax * 1.25))
    ax.yaxis.grid(True, linewidth=0.3, alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", handlelength=1.4)
    save(fig, out, "fig_hallucination")


TWIN_WORKFLOWS = [("energy_saving", "Energy saving"), ("traffic_steering", "Traffic steering"), ("qoe_steering", "QoE-driven steering")]
TWIN_KPIS = [("prb_used_dl", "DL PRBs used"), ("dl_throughput_mbps", "DL throughput"), ("dl_buffer_kbytes", "DL buffer"),
             ("energy_j_per_s", "gNB energy")]


def twin_title(twin_dir: Path) -> str:
    manifest = json.loads((twin_dir / "manifest.json").read_text(encoding="utf-8"))
    return f"twin {manifest.get('twin_ues')} UEs, live {manifest.get('live_ues')} UEs"


def fig_twin(twin_dirs: List[Path], out: Path) -> None:
    """Predicted (twin) vs actual (live) relative KPI change, one point per seed pair; one row per T6 batch.

    The RLC buffer is left out: its no-op level is near zero in several runs, so its relative change is
    not meaningful (TWIN_VALIDATION.md reports it in kB).
    """
    kpis = [(k, label) for k, label in TWIN_KPIS if k != "dl_buffer_kbytes"]
    fig, axes = plt.subplots(len(twin_dirs), len(kpis), figsize=(DOUBLE_COL * 0.8, 2.3 * len(twin_dirs)), squeeze=False)
    markers = {"energy_saving": "o", "traffic_steering": "s", "qoe_steering": "^"}
    colors = {"energy_saving": C_GREEN, "traffic_steering": C_BLUE, "qoe_steering": C_ORANGE}
    for row, twin_dir in zip(axes, twin_dirs):
        rows = json.loads((twin_dir / "summary.json").read_text(encoding="utf-8"))["rows"]
        for ax, (kpi, label) in zip(row, kpis):
            lim = 1.0
            for wf, wf_label in TWIN_WORKFLOWS:
                pts = [(100 * r["predicted_delta"] / r["twin_noop"], 100 * r["actual_delta"] / r["live_noop"])
                       for r in rows if r["workflow"] == wf and r["kpi"] == kpi and r["twin_noop"] and r["live_noop"]]
                if not pts:
                    continue
                xs, ys = zip(*pts)
                lim = max([lim] + [abs(v) for v in xs + ys])
                ax.scatter(xs, ys, s=14, marker=markers[wf], color=colors[wf], edgecolor="black", linewidth=0.3,
                           label=wf_label, zorder=3)
            lim *= 1.15
            ax.plot([-lim, lim], [-lim, lim], color=C_GRAY, linewidth=0.6, linestyle=(0, (3, 2)), zorder=1)
            ax.axhline(0, color="#CCCCCC", linewidth=0.4, zorder=0)
            ax.axvline(0, color="#CCCCCC", linewidth=0.4, zorder=0)
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_box_aspect(1)
            ax.set_title(f"{label}\n({twin_title(twin_dir)})", fontsize=6.5)
            ax.set_xlabel("Twin-predicted change (%)", fontsize=6.5)
            ax.tick_params(labelsize=6)
        row[0].set_ylabel("Measured live change (%)", fontsize=6.5)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, handlelength=1.0, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, out, "fig_twin_validation")


def twin_macros(twin_dir: Path, role: str = "T") -> List[str]:
    summary = json.loads((twin_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((twin_dir / "manifest.json").read_text(encoding="utf-8"))

    def put(method: str, key: str, value: Any) -> str:
        return f"\\expandafter\\def\\csname awr@{role}@{method}@{key}\\endcsname{{{value}}}"

    lines = [put("batch", "id", twin_dir.name.replace("_", "\\_"))]
    lines += [put("batch", key, manifest.get(key)) for key in ("twin_ues", "live_ues", "n_gnb", "sim_time_s")]
    lines.append(put("batch", "pairs", len({r["pair"] for r in summary["rows"]})))
    for key, stats in summary["by_workflow_kpi"].items():
        wf, kpi = key.split("/")
        for stat in ("mape_pct", "sign_agreement", "mean_actual_rel_pct", "mean_predicted_rel_pct", "mean_abs_rel_error_pp", "pairs"):
            value = stats.get(stat)
            if value is None:
                continue
            text = f"{100 * value:.0f}" if stat == "sign_agreement" else (str(value) if stat == "pairs" else f"{value:.1f}")
            lines.append(put(wf, f"{kpi}_{stat}", text))
    return lines


def batch_label(batch: Batch) -> str:
    if batch.role == "A":
        return "Batch A (paper registry)"
    return f"Batch B (directory, k={batch.retrieval_k or 'all'})"


# ---------------------------------------------------------------- tables / CSV
CSV_METRICS = ["accuracy", "exact_accuracy", "set_accuracy", "known_accuracy", "open_world_accuracy",
               "unseen_capability_accuracy", "ack_rate", "launch_rate", "conflict_recall", "conflict_fp_rate",
               "seeded_recovered", "hallucinated_per_record", "retrieval_hit_rate", "compat_ok_rate"]
CSV_SCALARS = ["records", "intents", "repeats", "known_records", "open_world_records", "unseen_capability_records",
               "tool_calls", "seeded_records", "hallucinated_refs", "records_with_hallucination", "latency_n",
               "latency_mean_ms", "latency_sd_ms", "latency_median_ms", "latency_p95_ms", "latency_max_ms",
               "planner_cached_records"]


def write_csv(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path) -> None:
    columns = ["batch", "role", "model", "think", "retrieval_k", "method"] + CSV_SCALARS
    for key in CSV_METRICS:
        columns += [key, f"{key}_ci_lo", f"{key}_ci_hi"]
    with (out / "combined_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for batch in batches:
            for method, m in all_metrics[batch.id].items():
                row = {"batch": batch.id, "role": batch.role, "model": batch.model, "think": batch.settings.get("think", ""),
                       "retrieval_k": batch.retrieval_k, "method": method}
                row.update({k: m.get(k) for k in CSV_SCALARS})
                for key in CSV_METRICS:
                    row[key], row[f"{key}_ci_lo"], row[f"{key}_ci_hi"] = m[key]
                writer.writerow(row)


def _tex_header(batch: Batch, what: str) -> List[str]:
    lines = [f"% Auto-generated by make_paper_figures.py from evaluation/runs/{batch.id} ({what}).",
             f"% Planner {batch.model}, inference settings {json.dumps(batch.settings, sort_keys=True)}.",
             "% Percent with 95% CI in brackets (intent-clustered bootstrap; conflict columns: Wilson)."]
    if batch.preliminary:
        lines.append("% PRELIMINARY: planner is not the paper's model (gpt-oss); do not cite as final.")
    return lines


def write_table_a(batch: Batch, metrics: Dict[str, Dict[str, Any]], out: Path) -> None:
    m0 = metrics[batch.methods[0]]
    caption = (f"Composition and reliability on the 50-intent benchmark ({m0['known_intents']} known, "
               f"{m0['open_world_intents']} open-world intents; {m0['repeats']} repeats; planner {batch.model}). "
               "Percent with 95\\% CI; conflicts: seeded records refused by the lease before control (refused) and "
               "brought to a clean execution by the method (recovered); no method flagged an unseeded record. "
               "Latency is intent-to-plan wall clock, median / p95 in seconds.")
    if batch.preliminary:
        caption = "\\textbf{PRELIMINARY.} " + caption
    lines = _tex_header(batch, "Batch A") + [
        "\\begin{table*}[t]", "\\centering", f"\\caption{{{caption}}}", "\\label{tab:appweaver-results}",
        "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}", "\\begin{tabular}{@{}lcccccccc@{}}", "\\toprule",
        "\\textbf{Method} & \\makecell{\\textbf{Known}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Open-world}\\\\\\textbf{acc.}} & "
        "\\makecell{\\textbf{Set}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Ack.}\\\\\\textbf{tool calls}} & "
        "\\makecell{\\textbf{Conflict}\\\\\\textbf{refused}} & \\makecell{\\textbf{Conflict}\\\\\\textbf{recovered}} & "
        "\\makecell{\\textbf{Halluc.}\\\\\\textbf{refs}} & "
        "\\makecell{\\textbf{Latency (s)}\\\\\\textbf{med. / p95}} \\\\",
        "\\midrule",
    ]
    for method in batch.methods:
        m = metrics[method]
        name = LABEL[method].replace("\n", " ")
        row = " & ".join([
            f"\\textbf{{{name}}}" if method == "langgraph_agentcard" else name,
            pct(m["known_accuracy"]), pct(m["open_world_accuracy"]), pct(m["set_accuracy"]),
            pct(m["ack_rate"]) + f" {{\\scriptsize(n={m['tool_calls']})}}",
            pct(m["conflict_recall"]), pct(m["seeded_recovered"]), str(m["hallucinated_refs"]),
            f"{secs(m['latency_median_ms'])} / {secs(m['latency_p95_ms'])}",
        ])
        lines.append(("\\rowcolor{gray!12}\n" if method == "langgraph_agentcard" else "") + row + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""]
    (out / "results_table.tex").write_text("\n".join(lines), encoding="utf-8")


def write_table_b(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path) -> None:
    first = batches[0]
    m0 = all_metrics[first.id][first.methods[0]]
    reg = first.manifest.get("registry") or {}
    caption = (f"Registry-scale benchmark: {reg.get('agent_count', '?')} cards in the Agent Registry "
               f"({m0['known_intents']} known, {m0['open_world_intents']} open-world, "
               f"{m0['unseen_capability_intents']} unseen-capability intents; {m0['repeats']} repeats; planner {first.model}). "
               "Accuracy counts any accepted chain; retrieval hit = all needed cards in the top-$k$ prompt.")
    if any(b.preliminary for b in batches):
        caption = "\\textbf{PRELIMINARY.} " + caption
    lines = []
    for b in batches:
        lines += _tex_header(b, f"Batch B, retrieval_k={b.retrieval_k}")
    lines += [
        "\\begin{table*}[t]", "\\centering", f"\\caption{{{caption}}}", "\\label{tab:appweaver-registry}",
        "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}", "\\begin{tabular}{@{}llcccccc@{}}", "\\toprule",
        "\\textbf{Method} & $k$ & \\makecell{\\textbf{Known}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Open-world}\\\\\\textbf{acc.}} & "
        "\\makecell{\\textbf{Unseen-cap.}\\\\\\textbf{acc.}} & \\makecell{\\textbf{Retrieval}\\\\\\textbf{hit}} & "
        "\\makecell{\\textbf{Halluc.}\\\\\\textbf{refs}} & \\makecell{\\textbf{Compat.}\\\\\\textbf{clean}} \\\\",
        "\\midrule",
    ]
    for b in batches:
        for method in b.methods:
            m = all_metrics[b.id][method]
            name = LABEL[method].replace("\n", " ")
            lines.append(" & ".join([
                f"\\textbf{{{name}}}" if method == "langgraph_agentcard" else name, str(b.retrieval_k or "all"),
                pct(m["known_accuracy"]), pct(m["open_world_accuracy"]), pct(m["unseen_capability_accuracy"]),
                pct(m["retrieval_hit_rate"], ci=False), str(m["hallucinated_refs"]), pct(m["compat_ok_rate"], ci=False),
            ]) + " \\\\")
        if b is not batches[-1]:
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""]
    (out / "results_table_registry.tex").write_text("\n".join(lines), encoding="utf-8")


def macro_role(batch: Batch) -> str:
    return "A" if batch.role == "A" else f"B{batch.retrieval_k or 'all'}"


def write_macros(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path,
                 twin_dirs: Sequence[Path] = ()) -> None:
    """`\\awres{<A|B8|Ball>}{<method>}{<metric>}` for every number the paper text cites.

    Rates are percent with one decimal (`<metric>`, `<metric>_lo`, `<metric>_hi`); latencies in seconds;
    counts as integers. Batch-level facts: `\\awres{<role>}{batch}{id|model|records|intents|repeats|cards}`.
    """
    lines = ["% Auto-generated by make_paper_figures.py; do not edit. Usage: \\awres{A}{langgraph_agentcard}{known_accuracy}",
             "\\makeatletter",
             "\\providecommand{\\awres}[3]{\\@ifundefined{awr@#1@#2@#3}{\\textbf{??}}{\\csname awr@#1@#2@#3\\endcsname}}",
             "\\makeatother"]

    def put(role: str, method: str, key: str, value: str) -> None:
        lines.append(f"\\expandafter\\def\\csname awr@{role}@{method}@{key}\\endcsname{{{value}}}")

    for batch in batches:
        role = macro_role(batch)
        reg = batch.manifest.get("registry") or {}
        put(role, "batch", "id", batch.id.replace("_", "\\_"))
        put(role, "batch", "model", batch.model)
        put(role, "batch", "records", str(len(batch.records)))
        put(role, "batch", "intents", str(len({r.get("intent_id") for r in batch.records})))
        put(role, "batch", "repeats", str(len({r.get("repeat_index") for r in batch.records})))
        put(role, "batch", "cards", str(reg.get("agent_count", "")))
        put(role, "batch", "executable", str(reg.get("executable_agent_count", "")))
        for method, m in all_metrics[batch.id].items():
            for key in CSV_METRICS:
                v, lo, hi = m[key]
                if v is None:
                    continue
                put(role, method, key, f"{100 * v:.1f}")
                if lo is not None:
                    put(role, method, f"{key}_lo", f"{100 * lo:.1f}")
                    put(role, method, f"{key}_hi", f"{100 * hi:.1f}")
            for key in ("latency_median_ms", "latency_p95_ms", "latency_max_ms", "latency_mean_ms", "latency_sd_ms"):
                if m.get(key) is not None:
                    put(role, method, key.replace("_ms", "_s"), f"{m[key] / 1000:.2f}")
            if m.get("prompt_chars_median") is not None:
                put(role, method, "prompt_kchars_median", f"{m['prompt_chars_median'] / 1000:.1f}")
            if m.get("open_world_rapp_rate") is not None:
                put(role, method, "open_world_rapp_rate", f"{100 * m['open_world_rapp_rate']:.1f}")
            for key in ("records", "tool_calls", "seeded_records", "hallucinated_refs", "records_with_hallucination",
                        "known_intents", "open_world_intents", "unseen_capability_intents", "planner_cached_records"):
                put(role, method, key, str(m.get(key, "")))
    # T = first T6 batch (twin load unknown), TL = second (load-calibrated twin).
    for twin_dir, role in zip(twin_dirs, ("T", "TL")):
        lines += twin_macros(twin_dir, role)
    (out / "results_macros.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(batches: List[Batch], all_metrics: Dict[str, Dict[str, Dict[str, Any]]], out: Path) -> None:
    lines = ["# AppWeaver paper results", "",
             "Generated by `make_paper_figures.py` from the batches below (every number is recomputed from",
             "`records.jsonl`). Metric definitions: `../METRICS.md`. 95% CIs: intent-clustered percentile bootstrap",
             "(2000 resamples) for accuracies, acknowledged calls and hallucinations per record; Wilson score",
             "interval for conflict recall / false-positive rate (6 seeded intents).", "",
             "No number from the May-2026 batches appears here.", "", "## Batches", ""]
    lines += [f"- **{batch_label(b)}**: {b.describe()}" for b in batches]
    for b in batches:
        metrics = all_metrics[b.id]
        lines += ["", f"## {batch_label(b)} - `{b.id}`", ""]
        if b.preliminary:
            lines += [f"> **Preliminary.** Planner `{b.model}` stands in for gpt-oss (broken on spark2 under Ollama 0.40).",
                      "> These numbers validate the pipeline; they are not the paper's results.", ""]
        lines += ["| Method | Accuracy | Known | Open-world | Unseen cap. | Exact | Set | Ack. calls | Conflict refused | Conflict recovered | Conflict FP | Halluc. refs | Retrieval hit | Latency med / p95 / max (s) |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for method in b.methods:
            m = metrics[method]
            lines.append("| " + " | ".join([
                LABEL[method].replace("\n", " "), pct_md(m["accuracy"]), pct_md(m["known_accuracy"]), pct_md(m["open_world_accuracy"]),
                pct_md(m["unseen_capability_accuracy"]), pct_md(m["exact_accuracy"]), pct_md(m["set_accuracy"]),
                f"{pct_md(m['ack_rate'])} (n={m['tool_calls']})",
                f"{pct_md(m['conflict_recall'])} (n={m['seeded_records']})", pct_md(m["seeded_recovered"]), pct_md(m["conflict_fp_rate"]),
                f"{m['hallucinated_refs']} in {m['records_with_hallucination']} records", pct_md(m["retrieval_hit_rate"]),
                " / ".join(secs(m[k], tex=False) for k in ("latency_median_ms", "latency_p95_ms", "latency_max_ms")),
            ]) + " |")
        cached = sum(m["planner_cached_records"] for m in metrics.values())
        lines += ["", f"Planner-cached records: {cached} (must be 0 for headline latency)."]
    lines += ["", "## Files", "",
              "- `combined_results.csv` - per (batch, method): value and CI bounds for every metric",
              "- `results_table.tex` - Batch A table; `results_table_registry.tex` - Batch B table",
              "- `figures/fig_accuracy` - Batch A known vs open-world accuracy with 95% CI",
              "- `figures/fig_reliability` - acknowledged tool calls, seeded conflicts refused by the lease and recovered",
              "- `figures/fig_latency` - per-record intent-to-plan latency (box = IQR, whiskers 5-95th pct, dots beyond)",
              "- `figures/fig_registry_splits` - Batch B accuracy per split, one panel per retrieval depth",
              "- `figures/fig_hallucination` - hallucinated registry references per record",
              "- `plot_final.py` - slide-style variants built from `combined_results.csv`", ""]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch-a", required=True)
    parser.add_argument("--batch-b", nargs="*", default=[])
    parser.add_argument("--twin", nargs="*", default=[], help="T6 run directories (run_twin_validation.py output): base, then load-calibrated")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    out = Path(args.out).resolve()
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    batch_a = Batch(Path(args.batch_a).resolve(), "A")
    batches_b = sorted((Batch(Path(p).resolve(), "B") for p in args.batch_b), key=lambda b: -(b.retrieval_k or 10**6))
    batches = [batch_a] + batches_b
    all_metrics = {b.id: batch_metrics(b) for b in batches}

    write_csv(batches, all_metrics, out)
    write_table_a(batch_a, all_metrics[batch_a.id], out)
    fig_accuracy(batch_a, all_metrics[batch_a.id], figures)
    fig_reliability(batch_a, all_metrics[batch_a.id], figures)
    fig_latency(batch_a, all_metrics[batch_a.id], figures)
    if batches_b:
        write_table_b(batches_b, all_metrics, out)
        fig_registry_splits(batches_b, all_metrics, figures)
    fig_hallucination(batches, all_metrics, figures)
    write_readme(batches, all_metrics, out)
    twin_dirs = [Path(p).resolve() for p in args.twin]
    if twin_dirs:
        fig_twin(twin_dirs, figures)
    write_macros(batches, all_metrics, out, twin_dirs)
    print(f"Wrote CSV, tables, README and figures to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
