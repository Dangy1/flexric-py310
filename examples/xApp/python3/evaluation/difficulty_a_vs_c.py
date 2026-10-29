#!/usr/bin/env python3
"""Difficulty comparison of Batch A (intents_50) and Batch C (intents_c): is C easier, and why?

No new runs: reads the two intents files and the records of one run per batch.
Per batch and split:
  * label chain length (expected_workflow) and number of required apps (label_rule.required);
  * explicit naming: share of the required control apps (SLICE / TC) whose domain is named in the sentence
    by a fixed keyword list (below; written before looking at the per-intent results);
  * template-solvable: some operator workflow template (backend.orchestration.config.WORKFLOW_TEMPLATES) passes
    the intent's label rule (same definition for A and C; C's own `template-solvable-under-rule` tag is reported too);
  * per chain shape (the sorted required set), the rule accuracy of every method in A and in C.

  python difficulty_a_vs_c.py --a-run runs/<A> --c-run runs/<C> [--out difficulty_A_vs_C.md]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.config import WORKFLOW_TEMPLATES  # noqa: E402
from evaluation.analyze_results import run_registry  # noqa: E402
from evaluation.label_rules import rule_match  # noqa: E402

# Domain keywords per control app (word-boundary, case-insensitive).
KEYWORDS = {
    "SLICE": [r"slice", r"slices", r"slicing", r"prb", r"tenant", r"partition"],
    "TC": [r"tc", r"traffic[- ]control", r"queue", r"queues", r"queueing", r"queuing", r"codel", r"ecn", r"shaping", r"shaper",
           r"bufferbloat", r"transport", r"backhaul", r"tunnel", r"gtp", r"traffic class(?:es)?", r"pacer", r"pacing"],
}
METHODS = ["manual_rule", "single_xapp", "llm_blind", "llm_only", "agentcard_no_repair", "langgraph_agentcard",
           "appweaver_tpl", "appweaver_mem", "appweaver_guided", "appweaver_v2", "appweaver_mem2"]


def load_records(run: Path) -> List[Dict[str, Any]]:
    path = run / "records.jsonl"
    if not path.exists():
        path = run / "records.partial.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def named(sentence: str, app: str) -> bool:
    return any(re.search(rf"\b{k}\b", sentence, re.I) for k in KEYWORDS.get(app, []))


def template_chains(registry: Dict[str, Any]) -> List[List[str]]:
    """The operator templates as the executable chains the rule router deploys (non-executable steps dropped)."""
    out = []
    for template in WORKFLOW_TEMPLATES.values():
        chain = [step.upper() for step in template["steps"] if getattr(registry.get(step), "actions", None)]
        if chain:
            out.append(chain)
    return out


def template_solvable(intent: Dict[str, Any], registry: Dict[str, Any]) -> bool:
    return any(rule_match(chain, intent, registry)[0] for chain in template_chains(registry))


def describe(intents: List[Dict[str, Any]], registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for split in sorted({i.get("split") or ("open_world" if i.get("open_world") else "known") for i in intents}) + ["all"]:
        xs = [i for i in intents if split == "all" or (i.get("split") or ("open_world" if i.get("open_world") else "known")) == split]
        control = [(i, app) for i in xs for app in (i.get("label_rule") or {}).get("required") or [] if app in KEYWORDS]
        out[split] = {
            "intents": len(xs),
            "chain_len_mean": round(statistics.fmean(len(i.get("expected_workflow") or []) for i in xs), 2),
            "required_mean": round(statistics.fmean(len((i.get("label_rule") or {}).get("required") or []) for i in xs), 2),
            "no_control_needed": sum(1 for i in xs if not any(a in KEYWORDS for a in (i.get("label_rule") or {}).get("required") or [])),
            "control_apps_named": f"{sum(named(i['intent'], a) for i, a in control)}/{len(control)}",
            "control_apps_named_pct": round(100 * sum(named(i["intent"], a) for i, a in control) / max(1, len(control)), 1),
            "template_solvable": sum(template_solvable(i, registry) for i in xs),
            "words_mean": round(statistics.fmean(len(i["intent"].split()) for i in xs), 1),
        }
    return out


def shape(intent: Dict[str, Any]) -> str:
    return "+".join(sorted((intent.get("label_rule") or {}).get("required") or [])) or "(none)"


def accuracy_by_shape(intents: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id = {i["id"]: i for i in intents}
    acc: Dict[str, Dict[str, List[bool]]] = defaultdict(lambda: defaultdict(list))
    count: Dict[str, set] = defaultdict(set)
    for r in records:
        intent = by_id.get(r.get("intent_id"))
        if intent is None or r.get("method_available") is False:
            continue
        acc[shape(intent)][r["method"]].append(bool(r.get("workflow_match_rule")))
        count[shape(intent)].add(intent["id"])
    return {s: {"intents": len(count[s]), **{m: round(100 * sum(v) / len(v), 1) for m, v in ms.items()}} for s, ms in acc.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a-run", required=True)
    parser.add_argument("--c-run", required=True)
    parser.add_argument("--a-intents", default=str(Path(__file__).resolve().parent / "intents_50.json"))
    parser.add_argument("--c-intents", default=str(Path(__file__).resolve().parent / "intents_c.json"))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    a_run, c_run = Path(args.a_run), Path(args.c_run)
    a = json.loads(Path(args.a_intents).read_text(encoding="utf-8"))
    c = json.loads(Path(args.c_intents).read_text(encoding="utf-8"))
    reg_a = run_registry(a_run) if (a_run / "manifest.json").exists() else None
    reg_c = run_registry(c_run) if (c_run / "manifest.json").exists() else reg_a
    da, dc = describe(a, reg_a), describe(c, reg_c)
    sa, sc = accuracy_by_shape(a, load_records(a_run)), accuracy_by_shape(c, load_records(c_run))
    c_tag = sum("template-solvable-under-rule" in (i.get("tags") or []) for i in c)
    print("template chains:", template_chains(reg_a), file=sys.stderr)

    lines = ["# Difficulty: Batch A vs Batch C", "",
             f"A run `{a_run.name}`, C run `{c_run.name}` ({len(load_records(c_run))} records).", "",
             "| Batch / split | Intents | Words | Label chain len | Required apps | No control app needed | Control apps named in sentence | Template-solvable |",
             "|---|---|---|---|---|---|---|---|"]
    for name, d in (("A", da), ("C", dc)):
        for split, v in d.items():
            lines.append(f"| {name} {split} | {v['intents']} | {v['words_mean']} | {v['chain_len_mean']} | {v['required_mean']} | "
                         f"{v['no_control_needed']} | {v['control_apps_named']} ({v['control_apps_named_pct']}%) | {v['template_solvable']} |")
    lines += ["", f"C's own `template-solvable-under-rule` tag: {c_tag} intents.", "",
              "Rule accuracy (%) per chain shape (required apps), same shape in A and C:", ""]
    methods = [m for m in METHODS if any(m in v for v in list(sa.values()) + list(sc.values()))]
    lines += ["| Shape | Batch | Intents | " + " | ".join(methods) + " |", "|---|---|---|" + "---|" * len(methods)]
    for s in sorted(set(sa) | set(sc), key=lambda k: (-(sa.get(k, {}).get("intents", 0) + sc.get(k, {}).get("intents", 0)), k)):
        for name, table in (("A", sa), ("C", sc)):
            if s in table:
                row = table[s]
                lines.append(f"| {s} | {name} | {row['intents']} | " + " | ".join(str(row.get(m, "--")) for m in methods) + " |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
