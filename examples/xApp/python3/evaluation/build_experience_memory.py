#!/usr/bin/env python3
"""Build AppWeaver's experience memory (method `appweaver_mem`) from a *training* batch.

One JSONL entry per intent of the training intents file:

    {"id": <intent id>, "intent": <operator sentence>,
     "accepted_workflows": [[...], ...],          # operator feedback = the intent's labelled accepted chains
     "rejected": [{"workflow": [...], "reasons": [...], "count": n}, ...],   # <= 2 AppWeaver proposals
     "provenance": {"run": ..., "method": ..., "proposals": n, "rejected_distinct": m}}

Rejected proposals are AppWeaver's own chains in the training run that fail the pre-registered label
rule (`evaluation/label_rules.rule_match`), with the rule's reasons (the record's
`workflow_rule_reasons`, recomputed with `rule_match` against the run's registry when the record
predates that field). Distinct chains are ranked by how often AppWeaver proposed them (ties: chain
text), so the output is deterministic. Empty plans are not proposals and are skipped.

No `notes`, `category`, `label_rule`, tags or source annotations enter the memory (checked).
The id and provenance are kept for the record (`memory_retrieved`); the prompt shows only the
sentence, the chains and the reasons (backend/appweaver/learning_prompts.py).

    python evaluation/build_experience_memory.py --run evaluation/runs/<A run> \
        --intents evaluation/intents_50.json --out evaluation/memory/experience_A.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.appweaver.learning import validate_entry  # noqa: E402
from evaluation.label_rules import rule_match  # noqa: E402

DEFAULT_METHOD = "langgraph_agentcard"
MAX_REJECTED = 2


def _upper_chain(chain: Sequence[Any]) -> List[str]:
    return [str(item).strip().upper() for item in chain or [] if str(item).strip()]


def load_records(run: Path, allow_partial: bool = False) -> List[Dict[str, Any]]:
    path = run / "records.jsonl"
    if not path.exists():
        partial = run / "records.partial.jsonl"
        if not (allow_partial and partial.exists()):
            raise SystemExit(f"{path} not found (unfinished batch? pass --allow-partial to use records.partial.jsonl)")
        path = partial
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_planner_only(spec: str, method: str) -> Tuple[List[Dict[str, Any]], str]:
    """Extra training proposals from a planner-only check (evaluation/devcheck/*.jsonl rows: intent_id, chain, rule,
    reasons), given as PATH[:LABEL]; returned as records of `method` so they are judged like a live run's."""
    path_text, _, label = spec.partition(":")
    path = Path(path_text).expanduser()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [{"method": method, "intent_id": row["intent_id"], "generated_workflow": row.get("chain") or [],
                "workflow_match_rule": row.get("rule"), "workflow_rule_reasons": row.get("reasons"),
                "repeat_index": index, "record_id": f"{label or path.stem}:{row['intent_id']}"}
               for index, row in enumerate(rows) if row.get("status") != "failed"]
    return records, (label or path.stem)


def run_registry(run: Path) -> Dict[str, Any]:
    """The Agent Registry of the training run, exactly as the paper scoring rebuilds it
    (evaluation/analyze_results.run_registry: current cards restricted to the manifest's card ids)."""
    from evaluation.analyze_results import run_registry as scoring_registry

    return scoring_registry(run)


def accepted_chains(intent: Dict[str, Any]) -> List[List[str]]:
    chains = [_upper_chain(c) for c in (intent.get("accepted_workflows") or [])] or [_upper_chain(intent.get("expected_workflow") or [])]
    return [c for c in chains if c]


def judge(record: Dict[str, Any], intent: Dict[str, Any], registry: Dict[str, Any]) -> Tuple[bool, List[str], str]:
    """(correct, reasons, source) for a record's chain under the pre-registered rule."""
    chain = _upper_chain(record.get("generated_workflow") or [])
    if record.get("workflow_match_rule") is not None and record.get("workflow_rule_reasons") is not None:
        return bool(record["workflow_match_rule"]), [str(r) for r in record["workflow_rule_reasons"]], "record"
    ok, reasons = rule_match(chain, intent, registry)
    return bool(ok), [str(r) for r in reasons], "rule_match"


def build_entries(intents: List[Dict[str, Any]], records: List[Dict[str, Any]], registry: Dict[str, Any],
                  run_name: str, method: str = DEFAULT_METHOD, max_rejected: int = MAX_REJECTED) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    by_intent: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        if record.get("method") != method or record.get("method_available") is False:
            continue
        by_intent.setdefault(str(record.get("intent_id")), []).append(record)

    entries: List[Dict[str, Any]] = []
    stats = Counter()
    for intent in intents:
        intent_id = str(intent["id"])
        accepted = accepted_chains(intent)
        counts: Counter = Counter()
        reasons_of: Dict[Tuple[str, ...], List[str]] = {}
        proposals = 0
        for record in sorted(by_intent.get(intent_id, []), key=lambda r: (int(r.get("repeat_index") or 0), str(r.get("record_id")))):
            chain = tuple(_upper_chain(record.get("generated_workflow") or []))
            if not chain:
                stats["empty_plans_skipped"] += 1
                continue
            proposals += 1
            ok, reasons, source = judge(record, intent, registry)
            stats[f"judged_by_{source}"] += 1
            if ok:
                continue
            if list(chain) in accepted:
                stats["rejected_equal_to_accepted_skipped"] += 1
                continue
            counts[chain] += 1
            reasons_of.setdefault(chain, reasons)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], " -> ".join(item[0])))[:max_rejected]
        entry = {
            "id": intent_id,
            "intent": str(intent["intent"]).strip(),
            "accepted_workflows": accepted,
            "rejected": [{"workflow": list(chain), "reasons": reasons_of[chain], "count": n} for chain, n in ranked],
            "provenance": {"run": run_name, "method": method, "proposals": proposals, "rejected_distinct": len(counts)},
        }
        validate_entry(entry)
        entries.append(entry)
        stats["entries"] += 1
        stats["entries_with_rejected"] += bool(entry["rejected"])
        stats["records"] += len(by_intent.get(intent_id, []))
    return entries, dict(stats)


def check_label_free(entries: List[Dict[str, Any]], intents: List[Dict[str, Any]]) -> None:
    """No intent's notes (or other free-text annotation) may appear anywhere in the memory."""
    text = json.dumps(entries)
    for intent in intents:
        for key in ("notes", "source"):
            value = str(intent.get(key) or "").strip()
            if len(value) >= 12 and value in text:
                raise SystemExit(f"memory carries the `{key}` annotation of intent {intent.get('id')!r}")


def dumps_entries(entries: List[Dict[str, Any]]) -> str:
    return "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", required=True, help="training batch directory (records.jsonl + manifest.json)")
    parser.add_argument("--intents", required=True, help="the training intents file of that batch (e.g. intents_50.json)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--method", default=DEFAULT_METHOD, help="whose proposals become the rejected examples (AppWeaver)")
    parser.add_argument("--max-rejected", type=int, default=MAX_REJECTED)
    parser.add_argument("--allow-partial", action="store_true", help="use records.partial.jsonl of an unfinished batch (previews only)")
    parser.add_argument("--planner-only", action="append", default=[], metavar="PATH[:LABEL]",
                        help="add AppWeaver proposals from a planner-only check on the same training intents (e.g. a second planner model)")
    args = parser.parse_args(argv)

    run = Path(args.run).expanduser().resolve()
    intents = json.loads(Path(args.intents).expanduser().read_text(encoding="utf-8"))
    records = load_records(run, allow_partial=args.allow_partial)
    sources = [run.name]
    for spec in args.planner_only:
        extra, label = load_planner_only(spec, args.method)
        records += extra
        sources.append(label)
    entries, stats = build_entries(intents, records, run_registry(run), " + ".join(dict.fromkeys(sources)),
                                   method=args.method, max_rejected=args.max_rejected)
    check_label_free(entries, intents)
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dumps_entries(entries), encoding="utf-8")
    print(json.dumps({"out": str(out), "run": run.name, **stats}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
