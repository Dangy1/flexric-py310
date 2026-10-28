from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .state import AppWeaverDeps, AppWeaverState


def event(deps: AppWeaverDeps, state: AppWeaverState, node: str, kind: str, **detail: Any) -> Dict[str, Any]:
    started = float(state.get("started_at") or deps.clock())
    return {"node": node, "kind": kind, "t_ms": round((deps.clock() - started) * 1000.0, 3), **detail}


def parse_plan(text: str) -> Dict[str, Any]:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in planner response.")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Planner response is not a JSON object.")
    return value


def normalize_chain(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip().upper() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"\s*(?:->|=>|→|,|\|)\s*", value.strip())
        return [part.strip().upper() for part in parts if part.strip()]
    return []


def normalize_steps(value: Any) -> List[Dict[str, str]]:
    steps: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return steps
    for item in value:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("agent_id") or item.get("agent") or "").strip().lower()
        action_id = str(item.get("action_id") or item.get("action") or "").strip()
        if agent_id:
            steps.append({"agent_id": agent_id, **({"action_id": action_id} if action_id else {})})
    return steps


def plan_chain(plan: Dict[str, Any]) -> List[str]:
    chain = normalize_chain(plan.get("generated_workflow"))
    if not chain:
        chain = [step["agent_id"].upper() for step in normalize_steps(plan.get("steps"))]
    return chain


def writes(deps: AppWeaverDeps, agent_id: str, action_id: Optional[str] = None) -> bool:
    from backend.orchestration.validate import writes as step_writes
    return step_writes(deps.registry.get(agent_id), action_id)


def busy_entries(busy: Dict[str, Optional[Dict[str, Any]]], own_run_ids: List[str]) -> List[Dict[str, Any]]:
    """Busy applications held by *another* workflow (our own launches are not a conflict)."""
    out: List[Dict[str, Any]] = []
    own = set(own_run_ids)
    for agent_id, info in (busy or {}).items():
        if not info:
            continue
        if str(info.get("run_id") or "") in own:
            continue
        out.append({"agent_id": agent_id, **{k: v for k, v in info.items() if k != "agent_id"}})
    return out
