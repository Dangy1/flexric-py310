from __future__ import annotations

import os
from typing import Any, Dict, List

from ..tools import PortalToolbox


def _task_text(result: Dict[str, Any]) -> str:
    task = result.get("task")
    if isinstance(task, dict):
        return str(task.get("response") or task.get("error") or "").strip()
    return str(result.get("response") or result.get("error") or "").strip()


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _deterministic_recommendation(observations: List[str], unhealthy: List[str], selected: List[Dict[str, Any]], mode: str) -> str:
    parts: List[str] = []
    if unhealthy:
        parts.append(f"Investigate unhealthy platform services: {', '.join(unhealthy)}.")
    else:
        parts.append("All tracked platform services currently report healthy enough for orchestration.")

    if observations:
        parts.append(f"Latest observed signal: {observations[-1]}")

    if selected:
        labels = ", ".join(f"{item['agent_id']}:{item['action_id']}" for item in selected)
        if mode == "enforced":
            parts.append(f"Mapped control actions for this workflow are: {labels}.")
        else:
            parts.append(f"Candidate mapped actions for a future enforced run are: {labels}.")
    else:
        parts.append("No concrete control actions are mapped for this workflow.")

    return " ".join(parts)


def build_diagnose_node(toolbox: PortalToolbox):
    def diagnose(state: Dict[str, Any]) -> Dict[str, Any]:
        observations = list(state.get("observations", []))
        hypotheses: List[str] = list(state.get("hypotheses", []))
        recommendations: List[str] = list(state.get("recommendations", []))
        errors: List[str] = list(state.get("errors", []))
        events = list(state.get("events", []))
        mode = str(state.get("mode", "advisory")).strip().lower() or "advisory"
        selected = list(state.get("selected_actions", []))

        unhealthy = [service["id"] for service in state.get("service_health", []) if not service.get("ok")]
        if unhealthy:
            hypotheses.append(f"Platform instability detected in services: {', '.join(unhealthy)}.")
        else:
            hypotheses.append("Core platform services look healthy enough for an orchestration attempt.")

        if observations:
            hypotheses.append(f"Most recent observation: {observations[-1]}")

        use_llm = _env_truthy("FLEXRIC_GRAPH_USE_LLM_DIAGNOSIS")
        if use_llm and toolbox.run_task is not None:
            prompt = (
                f"Goal: {state.get('goal', 'No goal provided')}\n"
                f"Observations: {' | '.join(observations[-4:])}\n"
                f"Mode: {mode}\n"
                "Use only the explicit observations above. Do not invent components, commands, or failures that are not stated. "
                "If uncertain, say uncertain. Return one short diagnosis paragraph and one short next-action paragraph."
            )
            try:
                task_result = toolbox.run_task("orchestrator", prompt, "auto")
                answer = _task_text(task_result)
                if answer:
                    recommendations.append(answer)
            except Exception as exc:
                errors.append(str(exc))
                hypotheses.append("Provider-backed diagnosis was unavailable; using deterministic fallback.")

        if not recommendations:
            recommendations.append(_deterministic_recommendation(observations, unhealthy, selected, mode))

        events.append(
            toolbox.event(
                "diagnose",
                "analysis",
                f"Built {len(hypotheses)} hypotheses and {len(recommendations)} recommendations.",
            )
        )
        return {
            "active_stage": "diagnose",
            "hypotheses": hypotheses,
            "recommendations": recommendations,
            "errors": errors,
            "events": events,
            "status": "running",
        }

    return diagnose
