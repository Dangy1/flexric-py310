"""Compose-prompt sections of the AppWeaver learning variants (hashed into the batch manifest).

`compose_prompt_with_context` is AppWeaver's Compose prompt (`prompts.compose_prompt`, unchanged
byte for byte) followed by up to two extra sections:

* operator workflow templates (`appweaver_tpl`, `appweaver_mem`);
* similar past intents with the accepted workflow and rejected proposals (`appweaver_mem`).

A memory entry is rendered from its sentence, chains and rejection reasons only; its id and
provenance stay in the record, never in the prompt. Benchmark annotations (`notes`, `category`,
labels of the current intent) never enter a prompt; the harness asserts this at runtime.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .needs import needs_section
from .prompts import compose_prompt

TEMPLATE_HEADER = (
    "Operator workflow templates: reuse one unchanged (its generated_workflow and steps) when the intent asks\n"
    "for that operator procedure; otherwise compose a workflow from the agent cards.\n"
)
MEMORY_HEADER = (
    "Operator experience: similar past intents and the workflow the operator accepted; and proposals the\n"
    "operator rejected with the reason. Use them as guidance for the current intent.\n"
)


def serialize_workflow_cards(cards: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "workflow_id": str(card.get("workflow_id")),
            "name": str(card.get("name") or ""),
            "description": str(card.get("description") or ""),
            "generated_workflow": list(card.get("generated_workflow") or []),
            "steps": [dict(step) for step in card.get("steps") or []],
        }
        for card in cards
    ]


def serialize_memory(entries: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in entries:
        out.append(
            {
                "past_intent": str(entry.get("intent") or ""),
                "accepted_workflows": [list(chain) for chain in entry.get("accepted_workflows") or []],
                "rejected_proposals": [
                    {"workflow": list(item.get("workflow") or []), "reason": list(item.get("reasons") or [])}
                    for item in entry.get("rejected") or []
                ],
            }
        )
    return out


def template_section(cards: Sequence[Mapping[str, Any]]) -> str:
    if not cards:
        return ""
    return TEMPLATE_HEADER + f"Workflow templates: {json.dumps(serialize_workflow_cards(cards))}\n"


def memory_section(entries: Sequence[Mapping[str, Any]]) -> str:
    if not entries:
        return ""
    return MEMORY_HEADER + f"Past intents: {json.dumps(serialize_memory(entries))}\n"


# Planning guidance (`appweaver_guided`, `appweaver_v2`). Written 2026-10-29 from AppWeaver's failure
# classes on the development batches A and B k=8 only (docs/APPWEAVER_FAILURE_ANALYSIS.md); Batch C
# (held out) had not been run or read. Each rule is a general orchestration principle stated over card
# fields, never an intent id, label or chain.
GUIDANCE_SECTION = (
    "Planning guidance:\n"
    "- Select applications by what the intent needs. Never leave out or replace an application because the\n"
    "  intent says it is busy or held by another workflow: the orchestrator handles a busy application by\n"
    "  waiting, bounded, for its lease.\n"
    "- Least privilege: include an application that writes network state (a control_scopes entry with mode\n"
    "  \"write\") only when the intent asks to change, protect, repair, mitigate, enforce or optimise something.\n"
    "  An intent that only asks to detect, investigate, screen, assess or report uses observation and\n"
    "  analytics applications only.\n"
    "- Direct conflicts: never put two applications that write the same control resource\n"
    "  (control_scopes.resource) in one workflow; choose the one whose description fits the intent best.\n"
    "- Cover every control domain the intent affects (for example radio or slice resources and transport or\n"
    "  traffic-class queues) with an application that controls it.\n"
)
FEEDBACK_HEADER = (
    "Validation feedback on your previous plan (the orchestrator's checks over the agent cards).\n"
    "Return a revised plan in the same JSON format that resolves every finding; keep what was correct.\n"
)


def guidance_section(enabled: bool) -> str:
    return GUIDANCE_SECTION if enabled else ""


def compose_prompt_with_context(
    intent_text: str,
    card_dicts: List[Dict[str, Any]],
    workflow_cards: Optional[Sequence[Mapping[str, Any]]] = None,
    memory_entries: Optional[Sequence[Mapping[str, Any]]] = None,
    guidance: bool = False,
    needs: Optional[Mapping[str, Any]] = None,
) -> str:
    return (compose_prompt(intent_text, card_dicts) + guidance_section(guidance) + needs_section(needs or {})
            + template_section(workflow_cards or []) + memory_section(memory_entries or []))


def feedback_prompt(base_prompt: str, plan: Mapping[str, Any], findings: Sequence[str]) -> str:
    """Compose prompt + the rejected plan + the deterministic findings (one bounded re-plan)."""
    previous = {"generated_workflow": list(plan.get("generated_workflow") or []), "steps": list(plan.get("steps") or [])}
    return base_prompt + FEEDBACK_HEADER + f"Previous plan: {json.dumps(previous)}\nFindings: {json.dumps(list(findings))}\n"
