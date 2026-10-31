#!/usr/bin/env python3
"""Same batch, two planner LLMs: per-method rule accuracy side by side (no new runs).

Every number is recomputed from each run's records.jsonl with the paper-results code
(`paper_results/make_paper_figures.py`: pre-registered label rule, intent-clustered bootstrap CIs,
open-world split without the intents an operator template already solves). Only methods present in
both runs are compared.

  python compare_planners.py --run runs/<gpt-oss C> --run runs/<GLM C> [--out PLANNERS_C.md]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "paper_results"))
from make_paper_figures import LABEL, METHODS, Batch, method_metrics, pct_md, secs  # noqa: E402

COLUMNS = [("rule_accuracy", "Accuracy (rule)"), ("known_rule_accuracy", "Known"), ("open_world_rule_accuracy", "Open-world"),
           ("open_world_nontpl_rule_accuracy", "Open-world, non-template"), ("exact_accuracy", "Exact"), ("ack_rate", "Ack. calls")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="append", required=True, help="run directory; give two or more")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    batches = [Batch(Path(p).resolve(), "C") for p in args.run]
    methods = [m for m, _ in METHODS if all(m in b.methods for b in batches)]

    lines = ["# Planner comparison on one batch", ""]
    lines += [f"- **{b.model}**: {b.describe()}" for b in batches]
    lines += ["", "Rule accuracy is primary; 95% CIs are intent-clustered bootstrap. Latency = intent-to-plan, median.", "",
              "| Method | Planner | " + " | ".join(name for _, name in COLUMNS) + " | Latency med (s) |",
              "|---|---|" + "---|" * len(COLUMNS) + "---|"]
    for method in methods:
        for b in batches:
            m = method_metrics([r for r in b.records if r.get("method") == method])
            lines.append(f"| {LABEL[method].replace(chr(10), ' ')} | {b.model} | "
                         + " | ".join(pct_md(m[key]) for key, _ in COLUMNS) + f" | {secs(m['latency_median_ms'], tex=False)} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
