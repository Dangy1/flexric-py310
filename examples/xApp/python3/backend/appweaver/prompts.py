"""Planner prompts of the AppWeaver graph (hashed into the batch manifest).

Only the operator's intent sentence enters a prompt; benchmark annotations
(`notes`, `category`, labels) never do. The harness asserts this at runtime.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from backend.common.models import AgentCard


def serialize_cards(cards: Iterable[AgentCard]) -> List[Dict[str, Any]]:
    """Agent-Card view given to the planner: the same fields the compat check uses."""
    out: List[Dict[str, Any]] = []
    for card in cards:
        if not card.actions:
            continue
        out.append(
            {
                "agent_id": card.id,
                "label": card.name,
                "app_type": getattr(card, "app_type", "xapp"),
                "ric": getattr(card, "ric", "near-rt"),
                "status": card.status,
                "description": card.description,
                "capabilities": list(card.capabilities),
                "requires": list(card.requires),
                "consumes": list(card.consumes),
                "produces": list(card.produces),
                "conflicts_with": list(card.conflicts_with),
                "control_scopes": [{"target": s.target, "mode": s.mode, "resource": s.resource} for s in card.control_scopes],
                "timescale_s": card.timescale_s,
                "interfaces": list(card.interfaces),
                "actions": [{"id": a.id, "label": a.label, "description": a.description, "kind": a.kind} for a in card.actions],
            }
        )
    return out


def compose_prompt(intent_text: str, card_dicts: List[Dict[str, Any]]) -> str:
    return (
        "You are planning an adaptive LangGraph-style workflow from executable agent cards for the FlexRIC portal.\n"
        "Return only JSON with keys generated_workflow, steps, and rationale.\n"
        "Rules:\n"
        "- generated_workflow must be a list of executable agent ids in execution order.\n"
        "- steps must be a list of objects with agent_id and optional action_id.\n"
        "- Use only executable agents and actions from the provided agent cards.\n"
        "- Cards with status \"deprecated\" are retired releases and must not be selected.\n"
        "- A card's requires (capabilities) and consumes (data) must be provided by an earlier step.\n"
        "- Prefer 1 to 4 steps.\n"
        "- Use KPM first when the task requires observation, diagnosis, anomaly detection, or root-cause triage.\n"
        "- Use RC last when the task applies or validates a control decision.\n"
        "- You may produce a novel workflow chain instead of forcing a predefined template.\n"
        f"Intent: {intent_text}\n"
        f"Executable agent cards: {json.dumps(card_dicts)}\n"
    )


def recovery_prompt(intent_text: str, failure_summary: Dict[str, Any], card_dicts: List[Dict[str, Any]], busy_resources: List[Dict[str, Any]]) -> str:
    return (
        "You are the Recover step of an O-RAN application orchestrator. The workflow below cannot be\n"
        "deployed now because some applications are busy: another operator's workflow holds them.\n"
        "Never pre-empt, cancel or reset the other workflow.\n"
        "Return only JSON with keys decision, generated_workflow, steps, and rationale.\n"
        "Rules:\n"
        "- decision is \"wait\" when the intent needs a busy application (the orchestrator then waits,\n"
        "  bounded, for its lease to be released and deploys the same workflow), or \"replan\" when the\n"
        "  intent can be met by a workflow that uses none of the busy applications.\n"
        "- With \"replan\", generated_workflow (agent ids in execution order) and steps (objects with\n"
        "  agent_id and optional action_id) must not contain any busy application.\n"
        "- Use only executable agents and actions from the provided agent cards; never deprecated cards.\n"
        f"Intent: {intent_text}\n"
        f"Busy resources: {json.dumps(busy_resources)}\n"
        f"Blocked workflow: {json.dumps(failure_summary)}\n"
        f"Executable agent cards: {json.dumps(card_dicts)}\n"
    )
