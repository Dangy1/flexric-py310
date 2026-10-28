#!/usr/bin/env python3
"""Summarise a CSV written by xapp_kpm_capture and check that KPIs vary over time.

Usage: python3 analyze_kpm_capture.py kpm.csv [--out summary.txt]

For each (cell, metric) of interest it aggregates the per-UE rows of every
indication (sum for PRB/throughput), then prints the per-cell time series
statistics. The time axis is collect_start_us: simulated time in microseconds
for captures made after the 2026-10-28 fixes (APPWEAVER_SETUP.md §11); older
captures carry the wall clock there, which still orders the indications.
"""
import argparse
import csv
import statistics
from collections import defaultdict

KEY_METRICS = ["RRU.PrbUsedDl.UEID", "DRB.UEThpDl.UEID", "DRB.BufferSize.Qos.UEID",
               "QosFlow.PdcpPduVolumeDL_Filter.UEID", "TB.TotNbrDl.1.UEID"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out")
    a = ap.parse_args()

    names = defaultdict(int)
    # (nb_id, meas) -> collect_start_us -> summed value over UEs
    series = defaultdict(lambda: defaultdict(float))
    rows = 0
    wall = []
    with open(a.csv) as f:
        for r in csv.DictReader(f):
            if not r["wall_us"].isdigit() or r["value"] == "":
                continue
            rows += 1
            wall.append(int(r["wall_us"]))
            names[r["meas"]] += 1
            if r["meas"] in KEY_METRICS and r["idx"] == "0":
                series[(int(r["nb_id"]), r["meas"])][int(r["collect_start_us"])] += float(r["value"])

    out = []
    out.append(f"rows: {rows}, wall span: {(max(wall) - min(wall)) / 1e6:.1f} s")
    out.append("measurement names seen (rows):")
    for n in sorted(names):
        out.append(f"  {n}: {names[n]}")
    out.append("")
    out.append("per-cell time series (sum over UEs per indication):")
    out.append(f"  {'cell':>4} {'metric':<38} {'n_ind':>6} {'distinct':>8} {'min':>10} {'mean':>10} {'max':>10} {'stdev':>10}")
    for (nb, m) in sorted(series):
        vals = [v for _, v in sorted(series[(nb, m)].items())]
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(f"  {nb:>4} {m:<38} {len(vals):>6} {len(set(vals)):>8} {min(vals):>10.1f} "
                   f"{statistics.mean(vals):>10.1f} {max(vals):>10.1f} {sd:>10.1f}")
    out.append("")
    out.append("first/last 10 indications of RRU.PrbUsedDl and DRB.UEThpDl per cell:")
    for (nb, m) in sorted(series):
        if m not in ("RRU.PrbUsedDl.UEID", "DRB.UEThpDl.UEID"):
            continue
        vals = [v for _, v in sorted(series[(nb, m)].items())]
        out.append(f"  cell {nb} {m}: first {vals[:10]} ... last {vals[-10:]}")
    text = "\n".join(out)
    print(text)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
