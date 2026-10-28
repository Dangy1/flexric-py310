#!/usr/bin/env python3
"""Re-analysis of the pre-fix T6 batches (2026-10-27, wall-clock KPM stamps, gated reporting) with the
T6v2 gate and KPI sources.

The pre-fix result.json files carry only all-gNB E2 KPI totals; the gate needs per-cell PRB. This script
re-reads each pre-fix run's kpm.csv with the clock logic those runs used (DU indications counted per node,
window = the run's own `kpi_window_indications`) for the E2 view, computes the ns-3 trace KPIs
(run_twin_validation.KPI_SOURCE) over the run's own `kpi_window_sim_s`, and runs analyse() on in-memory
copies (the archived runs are not modified). Writes <out_dir>/summary.{json,md} (trace KPIs) and
summary_e2kpm.{json,md}.

  python prefix_gate.py <full pre-fix batch dir with runs/*/kpm.csv and ns3_out/> <out_dir> [--live-noop-from <dir>]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_twin_validation as tv  # noqa: E402


def legacy_per_cell(kpm_csv: Path, k0: int, k1: int) -> dict:
    index = defaultdict(dict)  # nb -> collect_start -> k (order of first DU appearance)
    per = defaultdict(lambda: defaultdict(float))
    with kpm_csv.open(errors="replace") as handle:
        next(handle, None)
        for line in handle:
            row = line.rstrip("\n").split(",")
            if len(row) < 8 or not row[7]:
                continue
            try:
                start, nb, value = int(row[1]), int(row[3]), float(row[7])
            except ValueError:
                continue
            if nb < 2:
                continue
            meas = row[5]
            if meas in tv.DU_MEAS and start not in index[nb]:
                index[nb][start] = len(index[nb])
            k = index[nb].get(start, -1)
            field = {"RRU.PrbUsedDl.UEID": "prb", "DRB.UEThpDl.UEID": "thp", "DRB.BufferSize.Qos.UEID": "buf"}.get(meas)
            if field:
                per[(nb, k)][field] += value
    n = max(1, k1 - k0)
    return {str(g): {"prb_used_dl": sum(per[(g, k)]["prb"] for k in range(k0, k1)) / n,
                     "dl_throughput_mbps": sum(per[(g, k)]["thp"] for k in range(k0, k1)) / n / 1000.0,
                     "dl_buffer_kbytes": sum(per[(g, k)]["buf"] for k in range(k0, k1)) / n / 1000.0} for g in tv.GNBS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("out")
    ap.add_argument("--live-noop-from", default="", help="batch dir holding the live no-op runs if not in `batch`")
    args = ap.parse_args()
    batch = Path(args.batch)
    run_dirs = sorted((batch / "runs").glob("*"))
    if args.live_noop_from:
        names = {d.name for d in run_dirs}
        run_dirs += [d for d in sorted((Path(args.live_noop_from) / "runs").glob("live_*_noop")) if d.name not in names]
    results = []
    for d in run_dirs:
        res = json.loads((d / "result.json").read_text())
        if res.get("ok") and (d / "kpm.csv").exists():
            k0, k1 = res["kpi_window_indications"]
            res["kpi_per_cell"] = legacy_per_cell(d / "kpm.csv", k0, k1)
            t0, t1 = res["kpi_window_sim_s"]
            _, energy_cells = tv.energy_window(d / "ns3_out", tv.GNBS, t0, t1, per_cell=True)
            for c, e in energy_cells.items():
                res["kpi_per_cell"][c]["energy_j_per_s"] = e
            try:
                tv.apply_trace_kpis(d, res)
            except Exception as exc:
                res["ok"], res["error"] = False, f"trace KPIs: {exc}"
        results.append(res)
    manifest = json.loads((batch / "manifest.json").read_text())
    excluded = {int(p) for p in (manifest.get("excluded_pairs") or {})}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "SOURCE.txt").write_text(f"Re-analysis of the pre-fix batch {batch.resolve()} (archived copy unchanged) by "
                                    f"evaluation/twin/prefix_gate.py: T6v2 gate thresholds and KPI sources applied post hoc.\n")
    tv.write_summaries(out, results, excluded)
    summary = json.loads((out / "summary.json").read_text())
    for name, c in list(summary["gate"]["by_workflow"].items()) + [("pooled", summary["gate"]["pooled"])]:
        print(name, {k: c[k] for k in ("n", "tp", "fp", "fn", "tn", "accuracy", "precision", "recall", "specificity", "live_accept_rate")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
