"""Compose: LLM planner over the discovered Agent Cards, then compat check + repair.

Repair (disabled in the `no_repair` ablation) is registry-driven and never reads the
intent's labels: drop unknown / non-executable ids, collapse immediate duplicates, then
`compat.repair_chain` (insert the missing producer, reorder a late producer, replace a
deprecated card by its family's active release, drop a conflicting writer) with a fixpoint
re-check of `check_chain`. An empty or invalid plan is a failed record: there is no
deterministic fallback chain.

Feedback (`appweaver_guided`, `appweaver_v2`): when the repaired chain is empty or still has
compat findings (errors, or two writers on one control resource), the planner gets one bounded
re-plan with its previous plan and the findings; the revision is adopted only if it is non-empty
and has strictly fewer findings. The findings come from the Agent Cards only, never from labels.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from backend.orchestration.compat import check_chain, lifecycle_findings, repair_chain

from ..learning_prompts import compose_prompt_with_context, feedback_prompt
from ..prompts import compose_prompt, serialize_cards
from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event, normalize_steps, parse_plan, plan_chain


def feedback_findings(compat: Dict[str, Any], ids: List[str]) -> List[str]:
    """Deterministic findings the feedback re-plan resolves: no plan, compat errors, direct write conflicts."""
    if not ids:
        return ["The plan is empty or could not be parsed: return at least one executable agent."]
    out: List[str] = []
    for finding in compat.get("findings") or []:
        message = str(finding.get("detail") or "")
        if finding.get("severity") == "error" or message.startswith("Second writer"):
            out.append(f"{str(finding.get('agent_id') or '').upper()}: {message}")
    return out


def build_compose_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    registry = deps.registry

    def repair(plan: Dict[str, Any], excluded: List[str]) -> Tuple[List[str], Dict[str, str], List[str], List[Dict[str, Any]], Dict[str, Any]]:
        """(raw chain, requested actions, repaired ids, repair events, compat report) for one plan."""
        raw_chain = plan_chain(plan)
        requested = {s["agent_id"]: s["action_id"] for s in normalize_steps(plan.get("steps")) if s.get("action_id")}
        repair_events: List[Dict[str, Any]] = []
        if cfg.repair:
            ids: List[str] = []
            for name in raw_chain:
                agent_id = name.lower()
                card = registry.get(agent_id)
                if card is not None and not card.actions:
                    repair_events.append({"move": "drop_non_executable", "agent_id": agent_id})
                    continue
                if ids and ids[-1] == agent_id:
                    repair_events.append({"move": "collapse_duplicate", "agent_id": agent_id})
                    continue
                ids.append(agent_id)
            ids, moves, report = repair_chain(registry, ids, exclude=excluded)
            repair_events += moves
            compat = report.to_dict()
        else:
            ids = [name.lower() for name in raw_chain]
            report = check_chain(registry, ids)
            report.findings.extend(lifecycle_findings(registry, ids))
            report.checks_run = list(report.checks_run) + ["lifecycle"]
            compat = report.to_dict()
        return raw_chain, requested, ids, repair_events, compat

    def compose_node(state: AppWeaverState) -> Dict[str, Any]:
        intent_text = state["intent_text"]
        excluded = [str(item).lower() for item in (state.get("excluded_agents") or [])]
        updates: Dict[str, Any] = {}
        pending = state.get("pending_plan")
        prompt = ""
        if pending:
            plan = dict(pending)
            source = "recover"
            updates["pending_plan"] = None
        else:
            cards = [registry[i] for i in (state.get("card_ids") or []) if i in registry]
            prompt_meta: Dict[str, Any] = {}
            if cfg.workflow_templates or cfg.memory_path or cfg.guidance:
                workflow_cards = list(state.get("workflow_cards") or []) if cfg.workflow_templates else []
                memory_entries = list(state.get("memory_entries") or []) if cfg.memory_path else []
                prompt = compose_prompt_with_context(intent_text, serialize_cards(cards), workflow_cards, memory_entries,
                                                     guidance=cfg.guidance)
                prompt_meta = {"workflow_cards": [c.get("workflow_id") for c in workflow_cards],
                               "memory_entries": [e.get("id") for e in memory_entries]}
            else:
                prompt = compose_prompt(intent_text, serialize_cards(cards))
            task = dict(deps.planner(prompt) or {})
            updates["planner_task"] = task
            updates["prompts"] = [{"node": "compose", "chars": len(prompt), **prompt_meta}]
            if task.get("status") != "completed":
                text = str(task.get("response") or task.get("error") or "")
                unavailable = bool(deps.is_unavailable(text))
                return {
                    **updates,
                    "planner_unavailable": unavailable,
                    "generated_workflow": [],
                    "steps": [],
                    "status": "unavailable" if unavailable else "failed",
                    "failure_reason": "planner_unavailable" if unavailable else "planner_failed",
                    "events": [event(deps, state, "compose", "planner_failed", unavailable=unavailable, detail=text[:300])],
                }
            try:
                plan = parse_plan(str(task.get("response") or ""))
            except Exception as exc:
                plan = {"generated_workflow": [], "steps": [], "rationale": f"unparseable: {exc}"}
            source = "planner"
            updates["planner_plan"] = plan

        raw_chain, requested, ids, repair_events, compat = repair(plan, excluded)

        if source == "planner" and cfg.feedback:
            findings = feedback_findings(compat, ids)
            if findings:
                revised_prompt = feedback_prompt(prompt, plan, findings)
                task2 = dict(deps.planner(revised_prompt) or {})
                updates["feedback_planner_task"] = task2
                updates["prompts"] = updates["prompts"] + [{"node": "compose_feedback", "chars": len(revised_prompt)}]
                record: Dict[str, Any] = {"findings": findings, "first_chain": [i.upper() for i in ids],
                                          "revised_chain": [], "adopted": False}
                if task2.get("status") == "completed":
                    try:
                        plan2 = parse_plan(str(task2.get("response") or ""))
                    except Exception as exc:
                        plan2 = {"generated_workflow": [], "steps": [], "rationale": f"unparseable: {exc}"}
                    revised = repair(plan2, excluded)
                    record["revised_chain"] = [i.upper() for i in revised[2]]
                    if revised[2] and len(feedback_findings(revised[4], revised[2])) < len(findings):
                        plan = plan2
                        raw_chain, requested, ids, repair_events, compat = revised
                        updates["planner_plan"] = plan2
                        record["adopted"] = True
                updates["feedback"] = record

        steps: List[Dict[str, Any]] = []
        for agent_id in ids:
            card = registry.get(agent_id)
            if card is None or not card.actions:
                steps.append({"agent_id": agent_id, "action_id": None, "executable": False})
                continue
            action_id = requested.get(agent_id)
            if not action_id or not any(action.id == action_id for action in card.actions):
                action_id = deps.resolve_action(agent_id, intent_text)
                if not action_id or not any(action.id == action_id for action in card.actions):
                    action_id = card.actions[0].id
            steps.append({"agent_id": agent_id, "action_id": action_id, "executable": True})

        generated = [agent_id.upper() for agent_id in ids]
        ev = event(
            deps, state, "compose", "composed", source=source, raw_chain=raw_chain, chain=generated,
            repair_moves=[e.get("move") for e in repair_events], compat_ok=compat.get("ok"),
            **({"feedback_adopted": updates["feedback"]["adopted"]} if updates.get("feedback") else {}),
        )
        out: Dict[str, Any] = {
            **updates,
            "raw_chain": raw_chain,
            "generated_workflow": generated,
            "steps": steps,
            "compat_report": compat,
            "repair_events": repair_events,
            "deploy_cursor": 0,
            "events": [ev],
        }
        if not ids:
            out.update({"status": "failed", "failure_reason": "empty_plan"})
        return out

    return compose_node
