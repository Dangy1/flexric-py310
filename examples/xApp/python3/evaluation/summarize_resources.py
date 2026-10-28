#!/usr/bin/env python3
"""Per-method time breakdown and resource consumption of an evaluation batch.

Inputs: a run directory (records.jsonl or records.partial.jsonl) and the resource_monitor.py CSV.
Outputs (into the run directory unless --out): `resources_summary.json` and `resources_summary.md`.

Time per record (seconds, from the records):
  planner      LLM planner call(s): planner_task (+ recovery planner task) ended_at - started_at
  validate     AppWeaver Validate node (compat, E2 conformance, lease pre-check, twin dry-run)
  dryrun       of which: tier-1 twin dry-run of E2 control steps
  lease_wait   bounded wait for a busy application (same budget for every method)
  deploy       launch latency of the tool calls
  ack          time until each launched xApp/rApp showed its E2/rApp acknowledgement
  total        orchestration latency (intent in -> plan deployed), the paper's latency
LLM tokens per record: prompt / completion tokens reported by the server (batches from 1af53fb2 on).
Host resources: monitor samples whose timestamp falls inside a record's
[record_started_at, record_ended_at] window are attributed to that record's method (CPU-seconds and
mean RSS per component). Batches without record windows get batch-level totals only.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

METHODS = ["manual_rule", "single_xapp", "llm_blind", "llm_only", "agentcard_no_repair", "langgraph_agentcard"]
STAGES = ["planner", "validate", "dryrun", "lease_wait", "deploy", "ack", "total"]


def load_records(run: Path) -> List[Dict[str, Any]]:
    path = run / "records.jsonl"
    if not path.exists():
        path = run / "records.partial.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _task_seconds(task: Any) -> float:
    if isinstance(task, dict) and task.get("started_at") and task.get("ended_at"):
        return float(task["ended_at"]) - float(task["started_at"])
    return 0.0


def _usage(task: Any) -> Dict[str, int]:
    usage = (task or {}).get("usage") if isinstance(task, dict) else None
    usage = usage or {}
    return {"prompt": int(usage.get("prompt_tokens") or 0), "completion": int(usage.get("completion_tokens") or 0)}


def record_times(r: Dict[str, Any]) -> Dict[str, Any]:
    art = r.get("execution_artifacts") or {}
    tasks = [art.get("planner_task"), art.get("recovery_planner_task")]
    validation = r.get("validation_report") or {}
    calls = r.get("tool_calls") or []
    tokens = {"prompt": 0, "completion": 0}
    for task in tasks:
        for key, value in _usage(task).items():
            tokens[key] += value
    return {
        "planner": sum(_task_seconds(t) for t in tasks),
        "validate": float(validation.get("latency_ms") or 0.0) / 1000.0,
        "dryrun": sum(float(d.get("latency_ms") or 0.0) for d in validation.get("dryrun") or []) / 1000.0,
        "lease_wait": float(r.get("lease_wait_s") or 0.0),
        "deploy": sum(float(c.get("latency_ms") or 0.0) for c in calls) / 1000.0,
        "ack": sum(float(c.get("ack_latency_ms") or 0.0) for c in calls) / 1000.0,
        "total": float(r.get("orchestration_latency_ms") or 0.0) / 1000.0,
        "tokens": tokens,
        "has_usage": any(isinstance(t, dict) and "usage" in t for t in tasks),
    }


def load_samples(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="") as handle:
        return [{"t": float(row["t"]), "component": row["component"], "cpu_pct": float(row["cpu_pct"]),
                 "rss_mib": float(row["rss_mib"])} for row in csv.DictReader(handle)]


def summarize(run: Path, samples_path: Path, interval_s: float) -> Dict[str, Any]:
    records = [r for r in load_records(run) if r.get("method_available") is not False]
    out: Dict[str, Any] = {"run": run.name, "records": len(records), "methods": {}}
    by_method: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_method[str(r.get("method"))].append(r)
    for method in [m for m in METHODS if m in by_method] + sorted(set(by_method) - set(METHODS)):
        rows = [record_times(r) for r in by_method[method]]
        stats = {}
        for stage in STAGES:
            values = [row[stage] for row in rows]
            stats[stage] = {"mean_s": round(statistics.fmean(values), 3), "median_s": round(statistics.median(values), 3),
                            "p95_s": round(sorted(values)[int(0.95 * (len(values) - 1))], 3)}
        with_usage = [row for row in rows if row["has_usage"]]
        tokens = {
            "records_with_usage": len(with_usage),
            "prompt_tokens_mean": round(statistics.fmean([row["tokens"]["prompt"] for row in with_usage]), 1) if with_usage else None,
            "completion_tokens_mean": round(statistics.fmean([row["tokens"]["completion"] for row in with_usage]), 1) if with_usage else None,
            "total_tokens_sum": sum(row["tokens"]["prompt"] + row["tokens"]["completion"] for row in with_usage),
        }
        out["methods"][method] = {"records": len(rows), "time": stats, "llm_tokens": tokens}

    samples = load_samples(samples_path) if samples_path.exists() else []
    windows = [(float(r["record_started_at"]), float(r["record_ended_at"]), str(r.get("method")))
               for r in records if r.get("record_started_at") and r.get("record_ended_at")]
    if samples:
        t0 = min(float(r.get("record_started_at") or 0) or 0 for r in records) if windows else None
        lo = min(w[0] for w in windows) if windows else min(s["t"] for s in samples)
        hi = max(w[1] for w in windows) if windows else max(s["t"] for s in samples)
        in_batch = [s for s in samples if lo <= s["t"] <= hi] if windows else samples
        comp: Dict[str, Dict[str, float]] = defaultdict(lambda: {"cpu_s": 0.0, "rss_sum": 0.0, "n": 0})
        for s in in_batch:
            if s["component"] == "_host":
                continue
            c = comp[s["component"]]
            c["cpu_s"] += s["cpu_pct"] / 100.0 * interval_s
            c["rss_sum"] += s["rss_mib"]
            c["n"] += 1
        out["batch_resources"] = {
            "window": [lo, hi], "samples": len(in_batch),
            "components": {k: {"cpu_core_seconds": round(v["cpu_s"], 1), "mean_rss_mib": round(v["rss_sum"] / max(1, v["n"]), 1)}
                           for k, v in sorted(comp.items())},
        }
        del t0
        if windows:
            per_method: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"cpu_s": 0.0, "rss_sum": 0.0, "n": 0}))
            windows.sort()
            j = 0
            for s in sorted((s for s in in_batch if s["component"] != "_host"), key=lambda s: s["t"]):
                while j < len(windows) and windows[j][1] < s["t"]:
                    j += 1
                if j < len(windows) and windows[j][0] <= s["t"] <= windows[j][1]:
                    c = per_method[windows[j][2]][s["component"]]
                    c["cpu_s"] += s["cpu_pct"] / 100.0 * interval_s
                    c["rss_sum"] += s["rss_mib"]
                    c["n"] += 1
            for method, comps in per_method.items():
                n_rec = len(by_method.get(method, [])) or 1
                out["methods"].setdefault(method, {})["resources_per_record"] = {
                    k: {"cpu_core_seconds": round(v["cpu_s"] / n_rec, 2), "mean_rss_mib": round(v["rss_sum"] / max(1, v["n"]), 1)}
                    for k, v in sorted(comps.items())}
    return out


def markdown(summary: Dict[str, Any]) -> str:
    lines = [f"# Time and resources - `{summary['run']}` ({summary['records']} records)", "",
             "Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.", "",
             "| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for method, m in summary["methods"].items():
        if "time" not in m:
            continue
        t = m["time"]
        cell = lambda s: f"{t[s]['median_s']:.1f} ({t[s]['mean_s']:.1f})"
        tok = m["llm_tokens"]
        lines.append(f"| {method} | " + " | ".join(cell(s) for s in STAGES) +
                     f" | {tok['prompt_tokens_mean'] if tok['prompt_tokens_mean'] is not None else '--'} | "
                     f"{tok['completion_tokens_mean'] if tok['completion_tokens_mean'] is not None else '--'} |")
    res = summary.get("batch_resources")
    if res:
        lines += ["", f"Host resources over the batch ({res['samples']} samples):", "",
                  "| Component | CPU core-seconds | Mean RSS (MiB) |", "|---|---|---|"]
        for name, v in res["components"].items():
            lines.append(f"| {name} | {v['cpu_core_seconds']} | {v['mean_rss_mib']} |")
    per = {m: v["resources_per_record"] for m, v in summary["methods"].items() if v.get("resources_per_record")}
    if per:
        comps = sorted({c for v in per.values() for c in v})
        lines += ["", "CPU core-seconds per record, by method and component:", "",
                  "| Method | " + " | ".join(comps) + " |", "|---|" + "---|" * len(comps)]
        for method, v in per.items():
            lines.append(f"| {method} | " + " | ".join(str(v.get(c, {}).get("cpu_core_seconds", 0)) for c in comps) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run")
    parser.add_argument("--samples", default="/tmp/appweaver_batches/resources_v2.csv")
    parser.add_argument("--interval-s", type=float, default=5.0)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    run = Path(args.run)
    summary = summarize(run, Path(args.samples), args.interval_s)
    out = Path(args.out) if args.out else run
    out.mkdir(parents=True, exist_ok=True)
    (out / "resources_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "resources_summary.md").write_text(markdown(summary), encoding="utf-8")
    print(markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
