#!/usr/bin/env python
"""One planner call through the portal's provider selection, to check an LLM host before a batch.

Reads the same environment the portal and the harness use (`.env` next to the portal, then the
process environment): VLLM_* / OLLAMA_* / OPENAI_* and LLM_PROVIDER. Prints the provider that
answered, its model, the pinned sampling settings and the latency, so a batch manifest can be
trusted before 1,500 records are spent on it.

    LLM_PROVIDER=vllm VLLM_BASE_URL=http://spark1:8000/v1 VLLM_MODEL=openai/gpt-oss-20b \
        VLLM_API_KEY=... scripts/check_llm_provider.py
    scripts/check_llm_provider.py --provider ollama        # ignore LLM_PROVIDER for this call
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PORTAL_DIR = THIS_DIR.parent
sys.path.insert(0, str(PORTAL_DIR))
os.environ.setdefault("FLEXRIC_AUTO_START", "0")

import flexric_agent_portal as portal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="auto", help="vllm | ollama | openai | claude | auto (default: LLM_PROVIDER or first enabled)")
    parser.add_argument("--prompt", default="Reply with the single word READY.", help="task prompt to send")
    args = parser.parse_args()

    print("providers:")
    for item in portal._provider_statuses():
        flag = "enabled " if item["enabled"] else "disabled"
        print(f"  {flag} {item['id']:7s} {item['model']:28s} {item['endpoint']}")
    print("settings:", json.dumps(portal.llm_sampling_settings(), sort_keys=True))

    try:
        provider = portal._enabled_provider(args.provider)
    except Exception as exc:  # HTTPException carries .detail
        print("select failed:", getattr(exc, "detail", exc))
        return 2

    agent = portal.AGENTS.get("orchestrator") or next(iter(portal.AGENTS.values()))
    started = time.perf_counter()
    try:
        text = portal._invoke_provider(provider, agent, args.prompt)
    except Exception as exc:
        print(f"call failed via {provider['id']} ({provider['model']}): {exc}")
        return 1
    latency = time.perf_counter() - started
    print(f"answered by {provider['id']} model={provider['model']} in {latency:.2f}s")
    print("reply:", text[:300].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
