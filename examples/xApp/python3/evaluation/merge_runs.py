#!/usr/bin/env python3
"""Merge evaluation runs into one batch, keeping only the repeats each source contributes.

Used when part of a batch is invalid (e.g. the nearRT-RIC wedged after ~700 records and every later
control call went unacknowledged): keep the clean repeats of the first run and add the repeats that
were re-run. The merged `manifest.json` lists every source run, its repeats and why it was cut.

  python merge_runs.py --out runs/<id>_merged \
      --source runs/<A1>:1-2 --source runs/<A2>:3-5 --note "RIC wedged from record ~700 in <A1>"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from analyze_results import build_markdown, build_summary


def load_records(run: Path) -> List[Dict[str, Any]]:
    path = run / "records.jsonl"
    if not path.exists():
        path = run / "records.partial.jsonl"  # an interrupted run keeps its finished records here
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--source", action="append", required=True, help="RUN_DIR:FIRST-LAST repeats to keep")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []
    sources = []
    manifest: Dict[str, Any] = {}
    for spec in args.source:
        run_str, repeats = spec.rsplit(":", 1)
        run = Path(run_str).resolve()
        first, last = (int(x) for x in repeats.split("-"))
        kept = [r for r in load_records(run) if first <= int(r.get("repeat_index") or 0) <= last]
        records.extend(kept)
        source_manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        manifest = manifest or dict(source_manifest)
        sources.append({"run": run.name, "repeats": [first, last], "records": len(kept),
                        "complete": (run / "records.jsonl").exists(), "manifest": source_manifest})
    seen = set()
    for record in records:
        key = (record.get("method"), record.get("intent_id"), record.get("repeat_index"))
        if key in seen:
            raise SystemExit(f"duplicate record {key}: overlapping repeat ranges")
        seen.add(key)
    manifest.update({"merged_from": sources, "merge_note": args.note, "repeat_count": len({r.get("repeat_index") for r in records})})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (out / "records.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    first_intents = sources and (Path(args.source[0].rsplit(":", 1)[0]) / "intents.json")
    if first_intents and first_intents.exists():
        (out / "intents.json").write_text(first_intents.read_text(encoding="utf-8"), encoding="utf-8")
    summary = build_summary(records)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "analysis.md").write_text(build_markdown(summary), encoding="utf-8")
    print(f"{out}: {len(records)} records from {len(sources)} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
