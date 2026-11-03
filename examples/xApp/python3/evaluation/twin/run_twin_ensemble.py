#!/usr/bin/env python3
"""Ensemble twin and uncertainty-aware deploy gate (T6v4).

The D2S study showed that a twin rehearsing the live decision predicts the KPI change within 3-7 pp, that
its own re-runs agree to < 1 pp, and that the remaining error comes from the mobility and fading the twin
cannot know (its seed). That error is as large as the gate's 5 % margins, so a single twin run gives a
verdict that flips near the threshold. Revision: rehearse each decision on K twin seeds (same layout, same
UE-level RC commands) and accept only if the ensemble clears the thresholds by one standard deviation.

Input: D2S batches (run_twin_validation.py --layout --sync state). Every distinct decision (layout, seed
pair, UE-level commands) that issued a control is rehearsed again on twin seeds pair+200 and pair+300; with
the existing twin run (seed pair) this gives K = 3. Live outcomes are the existing live runs.

Gate rules, declared in the manifest before any run (thresholds are those of run_twin_validation.GATE):
  single   the existing D2S verdict of twin seed `pair` alone
  mean     the GATE rule on the ensemble mean of each gate quantity
  margin   (primary) the GATE rule with every quantity moved against acceptance by one sample sd:
           steering: mean(hot_prb_reduction) - sd >= 5 AND mean(throughput_loss) + sd <= 5
           energy:   mean(energy_saving) - sd >= 5 AND mean(remaining_prb_increase) + sd <= 30
Each is compared with the live verdict under the plain GATE rule.

  python run_twin_ensemble.py --out <dir> --batches <D2S dir> [<D2S dir> ...] [--offsets 200 300] [--parallel 4]
"""
from __future__ import annotations

import argparse
import json
import math
import queue
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

import run_twin_validation as T

RULES = {
    "single": "D2S verdict of twin seed `pair` alone (GATE)",
    "mean": "GATE on the ensemble mean of each gate quantity",
    "margin": "primary: GATE with each quantity moved against acceptance by one sample sd "
              "(steering: mean(hot_prb_reduction)-sd >= 5 AND mean(throughput_loss)+sd <= 5; "
              "energy: mean(energy_saving)-sd >= 5 AND mean(remaining_prb_increase)+sd <= 30)",
}
QUANT = {"energy_saving": [("energy_saving_pct", "min", "energy_saving_min_pct"), ("remaining_prb_increase_pct", "max", "remaining_prb_increase_max_pct")],
         "traffic_steering": [("hot_prb_reduction_pct", "min", "hot_prb_reduction_min_pct"), ("throughput_loss_pct", "max", "throughput_loss_max_pct")],
         "qoe_steering": [("hot_prb_reduction_pct", "min", "hot_prb_reduction_min_pct"), ("throughput_loss_pct", "max", "throughput_loss_max_pct")]}


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def distinct_decisions(batches: List[Path]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for b in batches:
        man = load(b / "manifest.json")
        layout = Path(man["layout"])
        for wf in man["workflows"]:
            if wf == "noop":
                continue
            for p in man["pairs"]:
                tdir, ldir = b / "runs" / f"twin_s{p}_{wf}", b / "runs" / f"live_s{p + 100}_{wf}"
                if not ((tdir / "result.json").exists() and (ldir / "result.json").exists()):
                    continue
                tw, lv = load(tdir / "result.json"), load(ldir / "result.json")
                if not (tw.get("ok") and lv.get("ok")) or not (tw.get("commands") or lv.get("commands")):
                    continue
                key = (layout.name, p, tuple(sorted(tw.get("commands") or [])))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"id": f"d{len(out):02d}", "layout": str(layout), "layout_name": layout.stem, "pair": p, "workflow": wf,
                            "batch": str(b), "commands": sorted(tw.get("commands") or []), "policy": tw["policy"],
                            "twin_run": str(tdir), "twin_noop": str(b / "runs" / f"twin_s{p}_noop"),
                            "live_run": str(ldir), "live_noop": str(b / "runs" / f"live_s{p + 100}_noop")})
    return out


def verdict(workflow: str, vals: Dict[str, List[float]], margin: float) -> bool:
    th = T.GATE[workflow]
    for q, kind, key in QUANT[workflow]:
        v = [x for x in vals[q] if x is not None]
        if not v:
            return False
        m = statistics.fmean(v)
        s = statistics.stdev(v) if len(v) > 1 else 0.0
        if kind == "min" and m - margin * s < th[key]:
            return False
        if kind == "max" and m + margin * s > th[key]:
            return False
    return True


def wilson(k: int, n: int, z: float = 1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def analyse(out: Path, decisions: List[Dict[str, Any]], offsets: List[int]) -> Dict[str, Any]:
    rows = []
    for d in decisions:
        wf = d["workflow"]
        live = T.gate_metrics(wf, load(Path(d["live_run"]) / "result.json"), load(Path(d["live_noop"]) / "result.json"), d["policy"])
        members = [T.gate_metrics(wf, load(Path(d["twin_run"]) / "result.json"), load(Path(d["twin_noop"]) / "result.json"), d["policy"])]
        for off in offsets:
            seed = d["pair"] + off
            wr = out / d["layout_name"] / d["id"] / "runs" / T.run_name("twin", seed, wf) / "result.json"
            nr = out / d["layout_name"] / "noops" / "runs" / T.run_name("twin", seed, "noop") / "result.json"
            if wr.exists() and nr.exists() and load(wr).get("ok") and load(nr).get("ok"):
                members.append(T.gate_metrics(wf, load(wr), load(nr), d["policy"]))
        vals = {q: [m.get(q) for m in members] for q, *_ in QUANT[wf]}
        rows.append({"id": d["id"], "layout": d["layout_name"], "pair": d["pair"], "workflow": wf, "commands": d["commands"], "k": len(members),
                     "twin_members": vals, "live": {q: live.get(q) for q, *_ in QUANT[wf]}, "live_accept": live["accept"],
                     "single": members[0]["accept"], "mean": verdict(wf, vals, 0.0), "margin": verdict(wf, vals, 1.0)})
    summary: Dict[str, Any] = {"decisions": len(rows), "complete_k3": sum(r["k"] == 1 + len(offsets) for r in rows)}
    for group, sel in (("steering", lambda r: r["workflow"] != "energy_saving"), ("energy", lambda r: r["workflow"] == "energy_saving"), ("all", lambda r: True)):
        rs = [r for r in rows if sel(r) and r["k"] == 1 + len(offsets)]
        g: Dict[str, Any] = {"n": len(rs), "live_accept": sum(r["live_accept"] for r in rs)}
        for rule in RULES:
            tp = sum(r[rule] and r["live_accept"] for r in rs)
            fp = sum(r[rule] and not r["live_accept"] for r in rs)
            fn = sum(not r[rule] and r["live_accept"] for r in rs)
            tn = sum(not r[rule] and not r["live_accept"] for r in rs)
            g[rule] = {"agree": tp + tn, "agree_ci95": wilson(tp + tn, len(rs)), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                       "accepted": tp + fp, "precision": round(tp / (tp + fp), 3) if tp + fp else None}
        summary[group] = g
    (out / "ensemble.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    lines = ["# Ensemble twin and uncertainty-aware gate (T6v4)", "", f"Decisions: {len(rows)} distinct; K = {1 + len(offsets)} twin seeds each.", "",
             "| Group | n | live accepts | rule | agreement | 95% CI | accepted | false accepts | missed accepts |", "|---|---|---|---|---|---|---|---|---|"]
    for group in ("steering", "energy", "all"):
        g = summary[group]
        for rule in RULES:
            r = g[rule]
            lines.append(f"| {group} | {g['n']} | {g['live_accept']} | {rule} | {r['agree']}/{g['n']} | {r['agree_ci95']} | {r['accepted']} | {r['fp']} | {r['fn']} |")
    lines += ["", "| id | layout | pair | workflow | commands | twin members (gate quantities) | live | live | single | mean | margin |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tm = "; ".join(f"{q}: " + ", ".join("--" if x is None else f"{x:.1f}" for x in v) for q, v in r["twin_members"].items())
        lv = "; ".join(f"{q}: {'--' if v is None else f'{v:.1f}'}" for q, v in r["live"].items())
        lines.append(f"| {r['id']} | {r['layout']} | {r['pair']} | {r['workflow']} | {' '.join(r['commands'])} | {tm} | {lv} | "
                     f"{'accept' if r['live_accept'] else 'reject'} | {r['single']} | {r['mean']} | {r['margin']} |")
    (out / "ensemble.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batches", nargs="+", required=True)
    ap.add_argument("--offsets", nargs="+", type=int, default=[200, 300])
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    decisions = distinct_decisions([Path(b).resolve() for b in args.batches])
    if args.report_only:
        print(json.dumps(analyse(out, decisions, args.offsets), indent=1))
        return 0
    manifest_path = out / "manifest.json"
    if not manifest_path.exists():  # declared before any run
        manifest_path.write_text(json.dumps({
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "batches": [str(Path(b).resolve()) for b in args.batches],
            "offsets": args.offsets, "k": 1 + len(args.offsets), "gate_thresholds": T.GATE, "rules": RULES,
            "primary_rule": "margin", "decisions": decisions, "parallel": args.parallel,
            "ns3_bin_sha256": T._sha256(T.NS3_BIN), "host_at_start": T.host_snapshot(),
            "protocol": "each distinct decision's UE-level RC commands re-executed on twin seeds pair+offset with the same layout; "
                        "no-ops of those seeds run once per layout; live outcomes reused from the D2S batches"}, indent=2))
    jobs = []
    for layout_name in sorted({d["layout_name"] for d in decisions}):
        d0 = next(d for d in decisions if d["layout_name"] == layout_name)
        n_ues = sum(1 for line in Path(d0["layout"]).read_text().splitlines()[1:] if line.strip())
        for p in sorted({d["pair"] for d in decisions if d["layout_name"] == layout_name}):
            for off in args.offsets:
                jobs.append((p + off, n_ues, "noop", out / layout_name / "noops", None, Path(d0["layout"])))
        for d in (d for d in decisions if d["layout_name"] == layout_name):
            for off in args.offsets:
                assert d["policy"].get("commands") is not None, f"{d['id']}: policy without UE-level commands"
                jobs.append((d["pair"] + off, n_ues, d["workflow"], out / layout_name / d["id"], d["policy"], Path(d["layout"])))
    slots: "queue.Queue[int]" = queue.Queue()
    for s in range(args.parallel):
        slots.put(s)
    done = [0]

    def run(job):
        seed, n_ues, wf, root, policy, layout = job
        slot = slots.get()
        try:
            res = T.run_with_retry("twin", seed, n_ues, wf, slot=slot, out_root=root, policy=policy, ue_position_file=layout)
        finally:
            slots.put(slot)
        done[0] += 1
        print(f"[{done[0]}/{len(jobs)}] {time.strftime('%H:%M:%S')} {root.name} twin s{seed} {wf} ok={res.get('ok')} "
              f"wall={res.get('wall_s')}s cmds={res.get('commands', [])} {res.get('error', '')}", flush=True)
        return res

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        list(pool.map(run, jobs))
    print(json.dumps(analyse(out, decisions, args.offsets), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
