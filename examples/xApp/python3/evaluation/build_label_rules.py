#!/usr/bin/env python3
"""Write the pre-registered `label_rule` into every intent of intents_50.json and intents_v2.json.

Deterministic: the rule of each intent is derived by `evaluation.label_rules.derive_rule` from the
intent's labelled chain(s) (`expected_workflow`, `accepted_workflows`) and the Agent Cards of the
full registry (portal cards + rApp Directory, i.e. FLEXRIC_RAPP_DIRECTORY=1). No method output is
read. `expected_workflow`, `accepted_workflows`, `notes` and `category` are left unchanged (`notes`
and `category` are annotations; methods must not see them).

Run (flexric-py310):
  python evaluation/build_label_rules.py           # rewrite both files
  python evaluation/build_label_rules.py --check   # exit 1 if a file is out of date
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from evaluation.label_rules import build_registry, derive_rule  # noqa: E402

FILES = {
    # file -> JSON layout of the hand-written file (compact: scalar lists on one line)
    "intents_50.json": "compact",
    "intents_v2.json": "indent2",
    "intents_c.json": "compact",  # Batch C: held-out intents, written blind to results
}


def _compact(obj: Any, depth: int = 0) -> str:
    pad = "  " * depth
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        return "{\n" + ",\n".join(f"{pad}  {json.dumps(k)}: {_compact(v, depth + 1)}" for k, v in obj.items()) + "\n" + pad + "}"
    if isinstance(obj, list):
        if all(not isinstance(item, (dict, list)) for item in obj):
            return "[" + ", ".join(json.dumps(item) for item in obj) + "]"
        return "[\n" + ",\n".join(f"{pad}  {_compact(item, depth + 1)}" for item in obj) + "\n" + pad + "]"
    return json.dumps(obj)


def dump(intents: List[Dict[str, Any]], layout: str) -> str:
    if layout == "compact":
        return _compact(intents) + "\n"
    return json.dumps(intents, indent=2)


def annotate(intents: List[Dict[str, Any]], registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for intent in intents:
        entry = {k: v for k, v in intent.items() if k != "label_rule"}
        entry["label_rule"] = derive_rule(entry, registry)
        out.append(entry)
    return out


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify that the files are up to date")
    args = parser.parse_args(argv)
    registry = build_registry(rapp_directory=True)
    stale = []
    for name, layout in FILES.items():
        path = HERE / name
        intents = json.loads(path.read_text(encoding="utf-8"))
        text = dump(annotate(intents, registry), layout)
        if path.read_text(encoding="utf-8") == text:
            print(f"{name}: up to date ({len(intents)} intents)")
            continue
        if args.check:
            stale.append(name)
            print(f"{name}: OUT OF DATE")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"{name}: wrote label_rule for {len(intents)} intents")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
