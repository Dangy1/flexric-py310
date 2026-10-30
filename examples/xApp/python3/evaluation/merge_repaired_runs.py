#!/usr/bin/env python3
"""Rebuild a repaired + extended batch from committed runs (the merged records.jsonl exceeds GitHub's 100 MB limit).

  base      a batch run whose `degraded_ric_records.json` lists (intent, repeat) pairs that ran on a degraded RIC
  repair    re-runs of exactly those pairs (all methods); `RUN[:REPEAT]` keeps only that repeat of a repair run
  extra     runs that add further methods under the same settings (e.g. the AppWeaver learning variants)

The base records of the degraded pairs are replaced by the repair records; extra runs are appended. Every
(method, intent, repeat) key must be unique and the repaired pairs must equal the degraded list.

  python merge_repaired_runs.py --base runs/<B k=8> --repair runs/<repair r1> --repair runs/<repair r2>:2 \
      --extra runs/<variants> --out runs/20261030T134800Z_B_k8_final_repaired_with_variants_gptoss120b_spark1
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load(run: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in (run / "records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def split_spec(spec: str) -> Tuple[Path, Optional[int]]:
    path, _, repeat = spec.rpartition(":") if spec.rsplit(":", 1)[-1].isdigit() else (spec, "", "")
    return Path(path), (int(repeat) if repeat else None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True)
    parser.add_argument("--repair", action="append", default=[], help="RUN[:REPEAT]")
    parser.add_argument("--extra", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--records-only", action="store_true", help="only (re)write records.jsonl (manifest etc. are committed)")
    args = parser.parse_args()

    base = Path(args.base)
    degraded = {(i, r) for i, r in json.loads((base / "degraded_ric_records.json").read_text())["degraded_pairs"]}
    repaired: List[Dict[str, Any]] = []
    repair_names = []
    for spec in args.repair:
        run, repeat = split_spec(spec)
        repaired += [r for r in load(run) if repeat is None or r.get("repeat_index") == repeat]
        repair_names.append(run.name + (f" (repeat {repeat} only)" if repeat else ""))
    pairs = {(r["intent_id"], r.get("repeat_index")) for r in repaired}
    if pairs != degraded:
        raise SystemExit(f"repair pairs {len(pairs)} != degraded pairs {len(degraded)}")
    merged = [r for r in load(base) if (r["intent_id"], r.get("repeat_index")) not in degraded] + repaired
    for run in args.extra:
        merged += load(Path(run))
    keys = [(r["method"], r["intent_id"], r.get("repeat_index")) for r in merged]
    if len(set(keys)) != len(keys):
        raise SystemExit("duplicate (method, intent, repeat) keys")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in merged), encoding="utf-8")
    if not args.records_only:
        shutil.copy(base / "intents.json", out / "intents.json")
        shutil.copy(base / "degraded_ric_records.json", out / "degraded_ric_records.json")
        manifest = json.loads((base / "manifest.json").read_text())
        manifest["merged_from"] = {
            "base": base.name, "repair": repair_names, "extra": [Path(r).name for r in args.extra],
            "note": "Base records of the (intent, repeat) pairs that ran on a degraded nearRT-RIC (degraded_ric_records.json) "
                    "are replaced by clean re-runs for all methods; extra runs add methods under the same settings. "
                    "records.jsonl is rebuilt by evaluation/merge_repaired_runs.py (too large for git).",
        }
        manifest["methods"] = sorted({r["method"] for r in merged})
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "records": len(merged), "methods": collections.Counter(r["method"] for r in merged)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
