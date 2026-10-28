"""Recover: wait for the lease or re-plan around the busy application. Never pre-empts.

Triggered by Validate (lease pre-check found a busy application, before any control) or by
Deploy (a step was still refused after the shared bounded wait). The LLM recovery planner
gets the busy resources and decides:
  * "replan" -> a chain without any busy application goes back through Compose (repair may
                not re-insert a busy app) and Validate;
  * "wait"   -> after a pre-check, wait for the busy applications up to the same lease budget
                every method gets, then deploy; after a deploy refusal the budget is already
                spent, so the workflow finishes refused.
An unavailable/unparseable recovery planner defaults to "wait" (the safe, non-pre-emptive
choice). Bounded to `max_recoveries` (1). The runtime is never reset.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from ..prompts import recovery_prompt, serialize_cards
from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event, normalize_steps, parse_plan, plan_chain


def build_recover_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    registry = deps.registry

    def recover_node(state: AppWeaverState) -> Dict[str, Any]:
        trigger = str(state.get("recover_trigger") or "precheck_busy")
        busy = list(state.get("busy_resources") or [])
        busy_ids = list(dict.fromkeys(str(b.get("agent_id")) for b in busy if b.get("agent_id")))
        recoveries = int(state.get("recoveries") or 0) + 1
        cards = [registry[i] for i in (state.get("card_ids") or []) if i in registry]
        summary = {
            "trigger": trigger,
            "chain": list(state.get("generated_workflow") or []),
            "already_running": sorted((state.get("deployed") or {}).keys()),
            "refusal": state.get("deploy_refusal"),
        }
        prompt = recovery_prompt(state["intent_text"], summary, serialize_cards(cards), busy)
        task = dict(deps.planner(prompt) or {})
        decision, plan, note = "wait", {}, ""
        if task.get("status") == "completed":
            try:
                plan = parse_plan(str(task.get("response") or ""))
                decision = str(plan.get("decision") or "").strip().lower()
                if decision not in {"wait", "replan"}:
                    note = f"unknown decision {decision!r}; defaulting to wait"
                    decision = "wait"
            except Exception as exc:
                note = f"unparseable recovery plan ({exc}); defaulting to wait"
        else:
            note = "recovery planner failed; defaulting to wait"

        new_chain: List[str] = []
        stripped: List[str] = []
        if decision == "replan":
            chain = plan_chain(plan)
            stripped = [c for c in chain if c.lower() in busy_ids]
            new_chain = [c for c in chain if c.lower() not in busy_ids]
            if not new_chain:
                decision, note = "wait", "re-plan was empty without the busy applications; defaulting to wait"

        record: Dict[str, Any] = {
            "trigger": trigger,
            "busy": busy_ids,
            "decision": decision,
            "note": note,
            "planner_task": task,
            "planner_plan": plan,
            "prompt_chars": len(prompt),
        }
        base: Dict[str, Any] = {"recoveries": recoveries, "prompts": [{"node": "recover", "chars": len(prompt)}]}

        if decision == "replan":
            steps = [s for s in normalize_steps(plan.get("steps")) if s["agent_id"] not in busy_ids]
            record.update({"replan_chain": new_chain, "stripped_busy": stripped})
            excluded = list(dict.fromkeys(list(state.get("excluded_agents") or []) + busy_ids))
            return {
                **base,
                "recovery": record,
                "pending_plan": {"generated_workflow": new_chain, "steps": steps, "rationale": plan.get("rationale", "")},
                "excluded_agents": excluded,
                "replanned_around_resource": True,
                "recovery_route": "compose",
                "events": [event(deps, state, "recover", "replan", busy=busy_ids, chain=new_chain, stripped=stripped)],
            }

        if trigger == "deploy_refused":
            record["outcome"] = "wait_budget_spent"
            return {
                **base,
                "recovery": record,
                "recovery_route": "finish",
                "events": [event(deps, state, "recover", "wait_budget_spent", busy=busy_ids, note=note)],
            }

        waited = deps.wait_until_free(busy_ids, float(cfg.lease_wait_s)) or {}
        waited_s = float(waited.get("waited_s") or 0.0)
        free = bool(waited.get("free"))
        record.update({"outcome": "free" if free else "timeout", "waited_s": round(waited_s, 3)})
        out: Dict[str, Any] = {
            **base,
            "recovery": record,
            "lease_wait_s": float(state.get("lease_wait_s") or 0.0) + waited_s,
            "waited_for_lease": True,
            "recovery_route": "deploy" if free else "finish",
            "events": [event(deps, state, "recover", "wait", busy=busy_ids, free=free, waited_s=round(waited_s, 3), note=note)],
        }
        if not free:
            out.update({
                "status": "queued",
                "failure_reason": "lease_wait_timeout",
                "blocked_reason": f"Busy after {cfg.lease_wait_s:.0f}s lease wait: {', '.join(busy_ids)}",
            })
        return out

    return recover_node
