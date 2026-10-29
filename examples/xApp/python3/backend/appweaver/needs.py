"""Needs-first planning (`appweaver_guided`, `appweaver_v2`): decide WHAT the intent needs before HOW.

Failure class F1 (docs/APPWEAVER_FAILURE_ANALYSIS.md): one planner call decided both what the intent
needs and what is available now, and dropped an application the intent called busy. Availability is the
orchestrator's job (Validate's lease pre-check, Recover's bounded wait), so the needs are fixed first:

1. Needs step (one LLM call): which control targets the intent asks to change, and whether it needs
   observation; told to ignore statements about busy applications. The control-target vocabulary is the
   set of `control_scopes` targets with mode "write" among the discovered cards (no labels).
2. Compose sees the needs; after repair, a deterministic coverage check over the Agent Cards finds a
   needed target that no step writes, a step that writes an unneeded target, or a missing observation;
   the findings go to Compose's single feedback re-plan.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from backend.common.models import AgentCard

MAX_APPS_PER_TARGET = 8


def write_targets(cards: Iterable[AgentCard]) -> Dict[str, List[str]]:
    """{control target: ids of the executable cards that write it}, in card order."""
    out: Dict[str, List[str]] = {}
    for card in cards:
        if not card.actions:
            continue
        for scope in card.control_scopes:
            if scope.mode == "write" and scope.target and card.id not in out.setdefault(scope.target, []):
                out[scope.target].append(card.id)
    return out


def _writes(card: AgentCard) -> List[str]:
    return sorted({scope.target for scope in card.control_scopes if scope.mode == "write" and scope.target})


def _observes(card: AgentCard) -> bool:
    return bool(card.control_scopes) and all(scope.mode == "read" for scope in card.control_scopes)


def needs_prompt(intent_text: str, targets: Mapping[str, Sequence[str]]) -> str:
    summary = {target: [app.upper() for app in apps[:MAX_APPS_PER_TARGET]] for target, apps in targets.items()}
    return (
        "You are the Needs step of an O-RAN application orchestrator: decide what the intent needs, not which\n"
        "applications to deploy.\n"
        "Return only JSON with keys observe, control_targets, and rationale.\n"
        "Rules:\n"
        "- control_targets: the control targets (from the list below) whose network state the intent asks to change,\n"
        "  protect, repair, mitigate, enforce or optimise; an empty list when the intent only asks to detect,\n"
        "  investigate, screen, assess or report.\n"
        "- observe: true when the intent needs measurements, diagnosis or evidence.\n"
        "- Ignore any statement about which applications are busy or held by another workflow: availability is\n"
        "  handled by the orchestrator (it waits for a busy application), not by the plan.\n"
        f"Control targets (target: applications that write it): {json.dumps(summary)}\n"
        f"Intent: {intent_text}\n"
    )


def parse_needs(text: str, targets: Iterable[str]) -> Dict[str, Any]:
    """Needs JSON -> {observe, control_targets (known targets only), rationale, ok}; ok False if unparseable."""
    known = set(targets)
    match = re.search(r"\{.*\}", text or "", re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except Exception:
        data = None
    if not isinstance(data, dict):
        return {"observe": None, "control_targets": [], "rationale": "", "ok": False}
    raw = data.get("control_targets") or []
    raw = raw if isinstance(raw, list) else [raw]
    wanted = [str(item).strip().lower() for item in raw]
    return {
        "observe": bool(data.get("observe")),
        "control_targets": sorted({t for t in wanted if t in known}),
        "unknown_targets": sorted({t for t in wanted if t not in known}),
        "rationale": str(data.get("rationale") or "")[:600],
        "ok": True,
    }


def needs_section(needs: Mapping[str, Any]) -> str:
    if not needs or not needs.get("ok"):
        return ""
    return (
        "Needs analysis (a previous step decided what the intent needs; cover it exactly):\n"
        f"- observation needed: {'yes' if needs.get('observe') else 'no'}\n"
        f"- control targets to write: {json.dumps(list(needs.get('control_targets') or []))}\n"
        "Include an application that writes each listed control target, and no application that writes an\n"
        "unlisted control target.\n"
    )


def coverage_findings(registry: Mapping[str, AgentCard], ids: Sequence[str], needs: Mapping[str, Any]) -> List[str]:
    """Deterministic gaps between the chain and the needs (empty when the needs step failed)."""
    if not needs or not needs.get("ok") or not ids:
        return []
    cards = [registry[i] for i in ids if i in registry]
    needed = set(needs.get("control_targets") or [])
    written = {target: card.id for card in cards for target in _writes(card)}
    out = [f"No step writes control target '{t}', which the needs analysis requires." for t in sorted(needed - set(written))]
    for card in cards:
        extra = [t for t in _writes(card) if t not in needed]
        if extra:
            out.append(f"{card.id.upper()}: writes control target(s) {extra}, which the needs analysis does not require.")
    if needs.get("observe") and not any(_observes(card) for card in cards):
        out.append("No observation step, although the needs analysis requires observation.")
    return out
