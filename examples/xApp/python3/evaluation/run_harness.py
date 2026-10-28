#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.analyze_results import build_markdown, build_summary, is_lease_refusal
from backend.orchestration.discovery import discover_with_report, pinned_xapp_ids  # type: ignore
from backend.orchestration.validate import live_e2_ran_functions, resolve_dryrun  # type: ignore
from backend.orchestration.validate import writes as step_writes  # type: ignore
# AppWeaver runs on LangGraph; an import failure must stop the harness, not fall back silently.
from backend.appweaver import (  # type: ignore
    AppWeaverConfig,
    AppWeaverDeps,
    compose_prompt,
    recovery_prompt,
    run_appweaver,
    serialize_cards,
)
from backend.appweaver import prompts as appweaver_prompts  # type: ignore
import flexric_agent_portal  # type: ignore
from flexric_agent_portal import (  # type: ignore
    AGENTS,
    WORKFLOW_ACTIONS,
    WORKFLOW_TEMPLATES,
    AgentTaskRequest,
    RuntimeResetRequest,
    WorkflowApprovalRequest,
    WorkflowRequest,
    api_agent_figures,
    api_run,
    api_run_action,
    api_run_task,
    api_runs,
    api_runtime_leases,
    api_runtime_reset,
    api_workflow_approve,
    api_workflow_run,
    api_workflow_status,
    llm_sampling_settings,
    _provider_statuses,
    _service_health,
)

METHODS = [
    "manual_rule",
    "single_xapp",
    "llm_blind",
    "llm_only",
    "langgraph_override",
    "langgraph_enforced",
    "langgraph_llm",
    "agentcard_no_repair",
    "langgraph_agentcard",
]

# Paper-facing names. `llm_only` keeps its historical id but is the
# catalog-aware LLM baseline (its prompt lists the workflow templates and its
# plan is repaired against them); `llm_blind` is the genuinely ungrounded one.
METHOD_LABELS = {
    "manual_rule": "Rule router",
    "single_xapp": "Single app",
    "llm_blind": "LLM (no catalog)",
    "llm_only": "LLM (catalog-aware)",
    "langgraph_override": "LangGraph + human approval",
    "langgraph_enforced": "LangGraph enforced",
    "langgraph_llm": "LangGraph + LLM recovery",
    "agentcard_no_repair": "AppWeaver (no repair)",
    "langgraph_agentcard": "AppWeaver",
}

# A launched action only counts as a successful tool call once its log shows
# the xApp actually did its job (observation records or a control/subscription
# acknowledgement). Until then it is merely a successful *launch*.
# Acks must come from an E2 exchange, checked against the full run log (see _log_acknowledges_full).
# In this Release build the E2 library prints "[xApp]: Successfully received CONTROL-ACK" even when
# the 6 s wait times out or the RAN answers CONTROL FAILURE; "[xApp]: CONTROL ACK rx" is printed only
# on a real CONTROL ACKNOWLEDGE, so it is the only control ack for SLICE and TC.
E2_CONTROL_ACK = "[xApp]: CONTROL ACK rx"
TOOL_ACK_MARKERS = {
    "kpm": ["RRU.", "DRB.", "\"meas\"", "indication"],
    "slice": [E2_CONTROL_ACK],
    "tc": [E2_CONTROL_ACK],
    # RC xApp (xapp_rc_ctrl.py): rc-control -> E2 RC CONTROL-ACK, rc-report -> RC REPORT indication.
    "rc": ["RC CONTROL-ACK received", "RC indication received"],
    # L2 monitor xApps (xapp_l2_monitor.py): acknowledged by the E2 indication they subscribe to.
    "mac": ["MAC ind tstamp="],
    "rlc": ["RLC ind tstamp="],
    "pdcp": ["PDCP ind tstamp="],
    "gtp": ["GTP ind tstamp="],
}
# Read-only actions are acknowledged by the E2 indication they subscribe to, not by a control ack.
TOOL_ACK_MARKERS_BY_ACTION = {
    ("slice", "monitor"): ["SLICE ind tstamp="],
}
# Printed by the suites but not an E2 acknowledgement: recorded as `ack_hint`, never counted.
TOOL_ACK_HINTS = {
    "tc": ["Applied TC profile"],
    "slice": ["Applied STATIC", "Applied NVS", "Applied EDF", "Successfully received CONTROL-ACK"],
}
TOOL_ACK_NEGATIVE_MARKERS = ["No KPM bus records were received", "Traceback", "Error", "refused", "RC CONTROL-FAILED", "RC REPORT-FAILED"]


def _ack_markers(agent_id: str, action_id: Optional[str] = None) -> List[str]:
    if action_id and (agent_id, action_id) in TOOL_ACK_MARKERS_BY_ACTION:
        return TOOL_ACK_MARKERS_BY_ACTION[(agent_id, action_id)]
    return TOOL_ACK_MARKERS.get(agent_id) or (["rApp ack:"] if agent_id.startswith("rapp.") else [])

OBSERVATION_AGENTS = {"kpm", "mac", "rlc", "pdcp", "gtp"}
VALIDATION_AGENTS = {"rc"}
CONTROL_AGENTS = {"slice", "tc"}
WORKFLOW_TRANSITIONAL_STATUSES = {"pending", "starting", "launching", "admitted", "running"}

EVAL_RUNTIME_CONFIG: Dict[str, Any] = {
    "metrics_mode": "cached",
    "metrics_min_interval_s": 15.0,
    "observation_cache_ttl_s": 20.0,
    "planner_cache_ttl_s": 600.0,
    "workflow_poll_timeout_s": 0.6,
    "tool_ack_timeout_s": 10.0,
    "workflow_poll_interval_s": 0.05,
    # Bounded lease wait every method gets when a step is refused because the agent is busy
    # (seed actions run 30 s): poll until free for up to this long, then retry once.
    "lease_wait_s": 45.0,
    "lease_poll_interval_s": 0.5,
    "validate_mode": "checks",
    "dryrun_duration_s": 5,
    "retrieval_pin_xapps": True,
    "retrieval_include_deprecated": True,
}

# Per-record guard state (set by run_record). `reset_runtime` must never run while a
# method executes: recovery is wait or re-plan, never pre-emption of another workflow.
_RECORD_STATE: Dict[str, Any] = {"active": False, "notes": "", "own_run_ids": set(), "reset_calls": 0, "lease_wait_s": 0.0}

_METRICS_SNAPSHOT_CACHE: Optional[Dict[str, Any]] = None
_OBSERVATION_ACTION_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_PLANNER_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}
_RECOVERY_PLANNER_CACHE: Dict[str, Dict[str, Any]] = {}

WORKFLOW_PROXY_METRICS = {
    "latency_ms": "DRB.RlcSduDelayDl",
    "throughput_mbps": "DRB.UEThpDl",
    "prb_utilization": "RRU.PrbTotDl",
}


def load_intents(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_action_chain(workflow_id: str) -> List[str]:
    mapping = WORKFLOW_ACTIONS.get(workflow_id, {})
    return [str(agent_id).upper() for agent_id in mapping.keys()]


def actions_for_workflow(workflow_id: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for agent_id, action_id in WORKFLOW_ACTIONS.get(workflow_id, {}).items():
        agent = AGENTS.get(str(agent_id))
        # A template may still name an action the card no longer has (e.g. rc-scaffold after the
        # RC xApp got real rc-control/rc-report actions): use the card's default action instead.
        if agent is not None and agent.actions and not any(action.id == str(action_id) for action in agent.actions):
            action_id = default_action_for_agent(str(agent_id), {}) or agent.actions[0].id
        pairs.append((str(agent_id), str(action_id)))
    return pairs


def route_intent(intent: Dict[str, Any]) -> str:
    """Keyword rule router over the intent sentence only (no category/notes labels)."""
    text = _intent_text(intent)
    if any(token in text for token in ["slice fairness", "slice isolation", "slice assurance", "reserved prbs"]):
        return "slice-assurance"
    if any(token in text for token in ["transport", "bufferbloat", "tunnel", "backhaul", "tc control", "qos"]):
        return "transport-qos"
    return "observe-diagnose-optimize"


def workflow_id_from_chain(chain: List[str]) -> Optional[str]:
    normalized = [str(item).strip().upper() for item in chain if str(item).strip()]
    for workflow_id in WORKFLOW_TEMPLATES:
        if normalize_action_chain(str(workflow_id)) == normalized:
            return str(workflow_id)
    return None


def custom_workflow_id_from_chain(chain: List[str]) -> str:
    normalized = [str(item).strip().lower() for item in chain if str(item).strip()]
    if not normalized:
        return "custom:empty"
    return "custom:" + "-".join(normalized)


def discover_for_text(intent_text: str, exclude: Optional[List[str]] = None) -> Tuple[List[Any], Dict[str, Any]]:
    """Discover step over the Agent Registry for an intent *sentence* (no labels).

    BM25 over card text. The executable FlexRIC xApps (kpm, slice, tc, rc) are pinned into
    every result (--retrieval-pin-xapps, default on); k bounds the rApp families only
    (k == 0: every card). Deprecated cards stay visible, marked by status, and are rejected
    at compose/validate time.
    """
    k = int(EVAL_RUNTIME_CONFIG.get("retrieval_k") or 0)
    pin = pinned_xapp_ids(AGENTS) if EVAL_RUNTIME_CONFIG.get("retrieval_pin_xapps", True) else []
    ranked, report = discover_with_report(
        AGENTS,
        intent_text,
        k=k,
        executable_only=True,
        include_deprecated=bool(EVAL_RUNTIME_CONFIG.get("retrieval_include_deprecated", True)),
        pin=pin,
        exclude=exclude,
    )
    cards = [card for card, _ in ranked]
    report = dict(report)
    report.update(
        {
            "registry_executable_count": sum(1 for card in AGENTS.values() if card.actions),
            "retrieved": [card.id for card in cards],
            "scores": {card.id: round(score, 3) for card, score in ranked[:30]},
            "pin_enabled": bool(pin),
        }
    )
    return cards, report


def annotate_retrieval(report: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    """Scoring only (after the method ran): did retrieval surface the labelled agents?"""
    report = dict(report or {})
    expected = [str(item).lower() for item in list(intent.get("expected_workflow") or [])]
    retrieved = list(report.get("retrieved") or [])
    report["expected_agents"] = expected
    report["expected_retrieved"] = all(agent in retrieved for agent in expected) if expected else None
    k = int(report.get("k") or 0)
    if k > 0:
        unpinned, _ = discover_with_report(
            AGENTS, _intent_text(intent), k=k, executable_only=True,
            include_deprecated=bool(EVAL_RUNTIME_CONFIG.get("retrieval_include_deprecated", True)), pin=[],
        )
        unpinned_ids = [card.id for card, _ in unpinned]
    else:
        unpinned_ids = retrieved
    report["expected_retrieved_unpinned"] = all(agent in unpinned_ids for agent in expected) if expected else None
    return report


def discover_cards(intent: Optional[Dict[str, Any]]) -> Tuple[List[Any], Dict[str, Any]]:
    """Backward-compatible wrapper: discovery for an intent record, annotated for scoring."""
    cards, report = discover_for_text(_intent_text(intent) if intent else "")
    return cards, annotate_retrieval(report, intent or {})


def executable_agent_cards(intent: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    selected = discover_for_text(_intent_text(intent))[0] if intent is not None else list(AGENTS.values())
    return serialize_cards(selected)


def _intent_text(intent: Dict[str, Any]) -> str:
    # Methods see the operator's sentence only; `notes`/`category` are benchmark annotations.
    return str((intent or {}).get("intent") or "").strip().lower()


def _intent_has_any(intent: Dict[str, Any], tokens: List[str]) -> bool:
    text = _intent_text(intent)
    return any(token in text for token in tokens)


# RC action choice from the intent sentence: a report subscription for observe-only intents, else control.
RC_READ_ONLY_TOKENS = ["monitor", "observe", "audit", "report", "investigate", "diagnose", "triage", "inspect", "screen"]
RC_CONTROL_TOKENS = ["reduce", "protect", "guarantee", "apply", "enforce", "mitigate", "improve", "optimize", "optimise",
                     "recover", "repair", "rebalance", "prioritize", "prioritise", "limit", "switch", "steer", "boost", "fix"]


def default_action_for_agent(agent_id: str, intent: Dict[str, Any]) -> Optional[str]:
    text = _intent_text(intent)
    if agent_id == "kpm":
        if any(token in text for token in ["rru", "prb", "capacity", "radio", "cell-edge", "headroom"]):
            return "observe-rru"
        return "observe-ue"
    if agent_id == "slice":
        if any(token in text for token in ["validate", "verify", "audit", "monitor", "observe", "check"]):
            return "monitor"
        return "apply-static"
    if agent_id == "tc":
        if any(token in text for token in ["tunnel", "backhaul", "bearer", "partition", "rlc", "full", "end-to-end"]):
            return "apply-all"
        return "apply-codel"
    if agent_id == "rc":
        card = AGENTS.get("rc")
        action_ids = [action.id for action in (card.actions if card is not None else [])]
        read_only = any(token in text for token in RC_READ_ONLY_TOKENS) and not any(token in text for token in RC_CONTROL_TOKENS)
        if read_only and "rc-report" in action_ids:
            return "rc-report"
        if "rc-control" in action_ids:
            return "rc-control"
        return action_ids[0] if action_ids else None
    return None


def summarize_figure_payload(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    figures = list(payload.get("figures") or [])
    metrics: Dict[str, Dict[str, Any]] = {}
    for figure in figures:
        for series in list(figure.get("series") or []):
            points = list(series.get("points") or [])
            latest_point = points[-1] if points else None
            values = [float(point.get("y")) for point in points if point.get("y") is not None]
            average = (sum(values) / len(values)) if values else None
            measurement = str(series.get("measurement") or series.get("id"))
            metrics[measurement] = {
                "measurement": measurement,
                "latest": float(latest_point.get("y")) if latest_point and latest_point.get("y") is not None else None,
                "average": average,
                "sample_count": len(points),
            }
    return metrics


def capture_metrics_snapshot() -> Dict[str, Any]:
    mode = str(EVAL_RUNTIME_CONFIG.get("metrics_mode") or "cached").strip().lower()
    if mode == "off":
        return _metrics_unavailable_snapshot("Metrics capture disabled by evaluation harness configuration.")

    cache_age = _metrics_cache_age_s()
    if mode == "cached" and _METRICS_SNAPSHOT_CACHE is not None and cache_age is not None:
        min_interval = float(EVAL_RUNTIME_CONFIG.get("metrics_min_interval_s") or 0.0)
        if cache_age < max(0.0, min_interval):
            cached = copy.deepcopy(_METRICS_SNAPSHOT_CACHE["snapshot"])
            cached["cache"] = {
                "mode": mode,
                "reused": True,
                "age_s": round(cache_age, 3),
                "reason": "min-interval",
            }
            return cached

    try:
        payload = api_agent_figures("kpm")
    except Exception as exc:  # pragma: no cover - depends on runtime stack
        if mode == "cached" and _METRICS_SNAPSHOT_CACHE is not None:
            cached = copy.deepcopy(_METRICS_SNAPSHOT_CACHE["snapshot"])
            cached["cache"] = {
                "mode": mode,
                "reused": True,
                "age_s": round(_metrics_cache_age_s() or 0.0, 3),
                "reason": "fetch-failed",
            }
            cached["detail"] = f"{cached.get('detail', '')} | Reused cached metrics after fetch failure: {exc}".strip(" |")
            return cached
        payload = {
            "ok": False,
            "status": "error",
            "detail": str(exc),
            "source": {"service": "kpm_bus", "record_count": 0, "indication_count": 0, "last_ts": None},
            "figures": [],
            "recent_measurements": [],
        }
    metrics = summarize_figure_payload(payload)
    snapshot = {
        "latency_ms": _metric_value(metrics, WORKFLOW_PROXY_METRICS["latency_ms"]),
        "throughput_mbps": _metric_value(metrics, WORKFLOW_PROXY_METRICS["throughput_mbps"]),
        "prb_utilization": _metric_value(metrics, WORKFLOW_PROXY_METRICS["prb_utilization"]),
        "sla_violation_rate": None,
    }
    result = {
        "available": bool(payload.get("ok")) and any(value is not None for value in snapshot.values()),
        "detail": payload.get("detail", ""),
        "source": payload.get("source", {}),
        "metrics": snapshot,
        "series_summary": metrics,
        "raw_payload": payload,
        "cache": {"mode": mode, "reused": False, "age_s": 0.0, "reason": "fresh"},
    }
    _remember_metrics_snapshot(result)
    return result


def _metrics_unavailable_snapshot(detail: str) -> Dict[str, Any]:
    return {
        "available": False,
        "detail": detail,
        "source": {"service": "kpm_bus", "record_count": 0, "indication_count": 0, "last_ts": None},
        "metrics": {
            "latency_ms": None,
            "throughput_mbps": None,
            "prb_utilization": None,
            "sla_violation_rate": None,
        },
        "series_summary": {},
        "raw_payload": {"ok": False, "status": "disabled", "detail": detail, "figures": []},
        "cache": {"mode": str(EVAL_RUNTIME_CONFIG.get("metrics_mode") or "cached"), "reused": False, "age_s": None, "reason": "disabled"},
    }


def _metrics_cache_age_s() -> float | None:
    if _METRICS_SNAPSHOT_CACHE is None:
        return None
    captured_at = float(_METRICS_SNAPSHOT_CACHE.get("captured_at") or 0.0)
    if captured_at <= 0.0:
        return None
    return max(0.0, time.time() - captured_at)


def _remember_metrics_snapshot(snapshot: Dict[str, Any]) -> None:
    global _METRICS_SNAPSHOT_CACHE
    _METRICS_SNAPSHOT_CACHE = {"captured_at": time.time(), "snapshot": copy.deepcopy(snapshot)}


def agent_role(agent_id: str) -> str:
    if agent_id in OBSERVATION_AGENTS:
        return "observation"
    if agent_id in VALIDATION_AGENTS:
        return "validation"
    if agent_id in CONTROL_AGENTS:
        return "control"
    return "other"


def _is_cacheable_observation(agent_id: str, action_id: str) -> bool:
    return agent_id in OBSERVATION_AGENTS and bool(action_id)


def _cached_observation_tool_call(agent_id: str, action_id: str, cache_entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    tool_call = copy.deepcopy(cache_entry["tool_call"])
    run_payload = copy.deepcopy(cache_entry.get("run_payload"))
    age_s = max(0.0, time.time() - float(cache_entry.get("captured_at") or time.time()))
    tool_call.update(
        {
            "status": "success",
            "raw_status": "cached",
            "latency_ms": 0.0,
            "detail": f"Reused cached observation result from evaluation harness to reduce KPM load ({age_s:.2f}s old).",
            "cached_result": True,
            "cache_age_s": round(age_s, 3),
        }
    )
    if run_payload is not None:
        run_payload["status"] = "cached"
        run_payload["detail"] = tool_call["detail"]
    return tool_call, run_payload, None


def _metric_value(metrics: Dict[str, Dict[str, Any]], measurement: str) -> float | None:
    metric = metrics.get(measurement)
    if not metric:
        return None
    latest = metric.get("latest")
    if latest is not None:
        return float(latest)
    average = metric.get("average")
    return float(average) if average is not None else None


def reset_runtime() -> Dict[str, Any]:
    """Harness housekeeping between records only.

    Resetting terminates every running action, i.e. it would pre-empt the other operator's
    (seeded) workflow. No method may call it while a record runs (review P0-2).
    """
    if _RECORD_STATE.get("active"):
        _RECORD_STATE["reset_calls"] = int(_RECORD_STATE.get("reset_calls") or 0) + 1
        raise AssertionError("reset_runtime() called while a record is running: methods may wait or re-plan, never pre-empt.")
    return api_runtime_reset(RuntimeResetRequest(clear_saved_workflows=False))


def _agent_writes(agent_id: str) -> bool:
    """Card-level write scope = the agent holds an exclusive lease class (used for seeding)."""
    card = AGENTS.get(str(agent_id or ""))
    return card is not None and any(scope.mode == "write" for scope in card.control_scopes)


def _step_writes(agent_id: str, action_id: Optional[str]) -> bool:
    """Does this launched step issue control (per-action scope when the card declares one)?"""
    return step_writes(AGENTS.get(str(agent_id or "")), action_id)


def active_runs_by_agent(agent_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Lease query: for each agent, the active run (or scheduler lease) that makes it busy, else None."""
    wanted = [str(agent_id) for agent_id in agent_ids]
    out: Dict[str, Optional[Dict[str, Any]]] = {agent_id: None for agent_id in wanted}
    if not wanted:
        return out
    own = set(_RECORD_STATE.get("own_run_ids") or set())
    for run in api_runs():
        agent_id = str(run.get("agent_id") or "")
        if agent_id in out and out[agent_id] is None and str(run.get("status") or "") in {"starting", "running"}:
            card = AGENTS.get(agent_id)
            out[agent_id] = {
                "run_id": run.get("id"),
                "action_id": run.get("action_id"),
                "started_at": run.get("started_at"),
                "resource": next((sc.resource for sc in (card.control_scopes if card else []) if sc.resource), ""),
                "source": "agent_run",
                "own": str(run.get("id") or "") in own,
            }
    try:
        leases = list((api_runtime_leases() or {}).get("leases") or [])
    except Exception:  # pragma: no cover - runtime dependent
        leases = []
    for lease in leases:
        resource = str(lease.get("resource_id") or lease.get("id") or "")
        for agent_id in wanted:
            card = AGENTS.get(agent_id)
            if out[agent_id] is None and card is not None and any(sc.resource == resource and sc.mode == "write" for sc in card.control_scopes):
                out[agent_id] = {"run_id": lease.get("run_id"), "resource": resource, "workflow_id": lease.get("workflow_id"), "source": "scheduler_lease", "own": False}
    return out


def _foreign_busy(agent_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    return {agent_id: info for agent_id, info in active_runs_by_agent(agent_ids).items() if info and not info.get("own")}


def wait_until_free(agent_ids: List[str], budget_s: float) -> Dict[str, Any]:
    """Bounded lease wait: poll until no *other* workflow holds the agents, at most budget_s."""
    started = time.perf_counter()
    interval = max(0.05, float(EVAL_RUNTIME_CONFIG.get("lease_poll_interval_s") or 0.5))
    busy = _foreign_busy(agent_ids)
    while busy and (time.perf_counter() - started) < max(0.0, float(budget_s)):
        time.sleep(interval)
        busy = _foreign_busy(agent_ids)
    waited = time.perf_counter() - started
    return {"free": not busy, "waited_s": round(waited, 3), "still_busy": sorted(busy)}


def invoke_with_lease_wait(agent_id: str, action_id: str) -> Dict[str, Any]:
    """Launch one step with the lease wait every method gets.

    If the portal refuses the launch because the agent is busy (409 "already has an active
    action"), the refused attempt is kept as a tool call (status "conflict"), the harness waits
    until the agent is free for up to --lease-wait-s and retries once.
    """
    tool_call, run_payload, error = invoke_action(agent_id, action_id)
    calls = [tool_call]
    payloads = [run_payload] if run_payload is not None else []
    waited_s = 0.0
    refused = False
    if is_lease_refusal(tool_call):
        tool_call["status"] = "conflict"
        tool_call["lease_refusal"] = True
        blocking = active_runs_by_agent([agent_id]).get(agent_id) or {}
        self_conflict = bool(blocking.get("own"))
        tool_call["blocking_run"] = blocking or None
        budget = float(EVAL_RUNTIME_CONFIG.get("lease_wait_s") or 0.0)
        if self_conflict or budget <= 0.0:
            refused = True
            tool_call["self_conflict"] = self_conflict
        else:
            waited = wait_until_free([agent_id], budget)
            waited_s = float(waited.get("waited_s") or 0.0)
            retry_call, retry_payload, error = invoke_action(agent_id, action_id)
            retry_call["retry_after_lease_wait"] = True
            retry_call["lease_wait_s"] = round(waited_s, 3)
            if is_lease_refusal(retry_call):
                retry_call["status"] = "conflict"
                retry_call["lease_refusal"] = True
                refused = True
            calls.append(retry_call)
            if retry_payload is not None:
                payloads.append(retry_payload)
    final = calls[-1]
    if final.get("status") == "success" and final.get("run_id"):
        _RECORD_STATE.setdefault("own_run_ids", set()).add(str(final["run_id"]))
    _RECORD_STATE["lease_wait_s"] = float(_RECORD_STATE.get("lease_wait_s") or 0.0) + waited_s
    return {"tool_calls": calls, "run_payloads": payloads, "error": error, "lease_wait_s": waited_s, "refused": refused}


def run_action_pairs(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Baseline executor: launch every pair in order (with the shared lease wait)."""
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []
    refusals: List[str] = []
    for agent_id, action_id in pairs:
        result = invoke_with_lease_wait(agent_id, action_id)
        tool_calls += list(result.get("tool_calls") or [])
        raw_runs += list(result.get("run_payloads") or [])
        if result.get("refused"):
            refusals.append(str((result.get("tool_calls") or [{}])[-1].get("detail") or ""))
    if any(call.get("status") == "failed" for call in tool_calls):
        status = "completed_with_issues"
    elif refusals:
        status = "queued"
    else:
        status = "completed"
    return {"tool_calls": tool_calls, "raw_runs": raw_runs, "status": status, "blocked_reason": "; ".join(refusals)}


def classify_tool_status(raw_status: str) -> str:
    status = str(raw_status or "").lower()
    if status in {"running", "starting", "launching", "completed", "success", "exited"}:
        return "success"
    if status in {"queued"}:
        return "queued"
    if status in {"blocked_by_conflict"}:
        return "conflict"
    if status in {"cancelled", "timed_out", "failed"}:
        return "failed"
    return status or "unknown"


def build_tool_call(agent_id: str, action_id: str, latency_ms: float, run_payload: Optional[Dict[str, Any]], error: Optional[str] = None) -> Dict[str, Any]:
    raw_status = str((run_payload or {}).get("status") or "")
    run_id = str((run_payload or {}).get("id") or (run_payload or {}).get("run_id") or "")
    detail = error or str((run_payload or {}).get("detail", ""))
    cached_result = run_id.startswith("cached-") or "Reused cached observation result" in detail
    status = "failed" if error else classify_tool_status(raw_status)
    return {
        "xapp": agent_id.upper(),
        "agent_id": agent_id,
        "action_id": action_id,
        "role": agent_role(agent_id),
        "status": status,
        "raw_status": raw_status or ("failed" if error else "unknown"),
        "latency_ms": round(latency_ms, 3),
        "run_id": run_id or None,
        "detail": detail,
        "returncode": (run_payload or {}).get("returncode"),
        "cached_result": cached_result,
    }


def invoke_action(agent_id: str, action_id: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    if _is_cacheable_observation(agent_id, action_id):
        cache_entry = _OBSERVATION_ACTION_CACHE.get((agent_id, action_id))
        ttl_s = float(EVAL_RUNTIME_CONFIG.get("observation_cache_ttl_s") or 0.0)
        if cache_entry is not None and ttl_s > 0.0:
            age_s = max(0.0, time.time() - float(cache_entry.get("captured_at") or time.time()))
            if age_s < ttl_s:
                return _cached_observation_tool_call(agent_id, action_id, cache_entry)

    started = time.perf_counter()
    try:
        payload = api_run_action(agent_id, action_id)
        latency_ms = (time.perf_counter() - started) * 1000.0
        run_payload = dict(payload.get("run") or {})
        tool_call = build_tool_call(agent_id, action_id, latency_ms, run_payload)
        if _is_cacheable_observation(agent_id, action_id) and tool_call.get("status") == "success":
            _OBSERVATION_ACTION_CACHE[(agent_id, action_id)] = {
                "captured_at": time.time(),
                "tool_call": copy.deepcopy(tool_call),
                "run_payload": copy.deepcopy(run_payload),
            }
        return tool_call, run_payload, None
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return build_tool_call(agent_id, action_id, latency_ms, None, error=str(exc)), None, str(exc)


def _log_acknowledges(agent_id: str, tail: List[str], action_id: Optional[str] = None) -> Optional[bool]:
    text = "\n".join(str(line) for line in tail)
    markers = _ack_markers(agent_id, action_id)
    if any(marker in text for marker in markers):
        return True
    if agent_id.startswith("rapp.") and "rApp error:" in text:
        return False
    if any(marker in text for marker in TOOL_ACK_NEGATIVE_MARKERS):
        return False
    return None


ACK_LOG_MAX_BYTES = 16 * 1024 * 1024


def _log_ack_hint(agent_id: str, log_path: Optional[str]) -> Optional[str]:
    hints = TOOL_ACK_HINTS.get(agent_id) or []
    if not hints or not log_path:
        return None
    try:
        with open(log_path, "rb") as handle:
            text = handle.read(ACK_LOG_MAX_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return None
    return next((hint for hint in hints if hint in text), None)


def _log_acknowledges_full(agent_id: str, log_path: Optional[str], action_id: Optional[str] = None) -> Optional[bool]:
    """Ack verdict from the run's *full* log (the portal tail is only 20 lines).

    `tc apply-all` subscribes RLC at 5 ms and floods `RLC len=...` lines, so the CONTROL-ACK /
    `Applied TC profile` markers scroll out of the tail within a second. A positive marker anywhere
    in the log acknowledges the call; negative markers count only in the text before the first
    positive marker (a later line cannot flip it). `RLC len=` is not an ack: it precedes the control.
    Returns None when the log is unreadable or shows neither.
    """
    if not log_path:
        return None
    try:
        with open(log_path, "rb") as handle:
            text = handle.read(ACK_LOG_MAX_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return None
    markers = _ack_markers(agent_id, action_id)
    positions = [pos for pos in (text.find(marker) for marker in markers) if pos >= 0]
    if positions:
        return True
    if agent_id.startswith("rapp.") and "rApp error:" in text:
        return False
    if any(marker in text for marker in TOOL_ACK_NEGATIVE_MARKERS):
        return False
    return None


def acknowledge_tool_calls(tool_calls: List[Dict[str, Any]], timeout_s: float) -> None:
    """Poll each launched run's log until it shows evidence of real work.

    Sets `acknowledged` (True/False) and `ack_latency_ms` on every tool call.
    Cached observation results inherit the acknowledgement of the run they
    were copied from. This wait is deliberately excluded from orchestration
    latency: it measures the xApp, not the planner.
    """
    deadline = time.time() + max(0.0, float(timeout_s))
    pending = [call for call in tool_calls if call.get("run_id") and not str(call.get("run_id")).startswith("cached-")]
    for call in tool_calls:
        call.setdefault("acknowledged", None)
        call.setdefault("ack_latency_ms", None)
        if call.get("status") in {"failed", "conflict", "queued"}:
            call["acknowledged"] = False
    started = time.time()
    while pending and time.time() < deadline:
        for call in list(pending):
            try:
                run = api_run(str(call["run_id"]))
            except Exception as exc:  # pragma: no cover - runtime dependent
                call["acknowledged"] = False
                call["ack_detail"] = str(exc)
                pending.remove(call)
                continue
            verdict = _log_acknowledges_full(str(call.get("agent_id")), run.get("log_path"), call.get("action_id"))
            if verdict is None:
                verdict = _log_acknowledges(str(call.get("agent_id")), list(run.get("tail") or []), call.get("action_id"))
            call["ack_source"] = "full_log" if run.get("log_path") else "tail"
            call["ack_hint"] = _log_ack_hint(str(call.get("agent_id")), run.get("log_path"))
            if verdict is False and str(run.get("status")) in WORKFLOW_TRANSITIONAL_STATUSES:
                # A negative line while the xApp is still running is not final: keep polling for a
                # positive marker until the deadline (the 20-line tail scrolls).
                verdict = None
            if verdict is None and str(run.get("status")) in {"completed", "exited"} and run.get("returncode") == 0:
                verdict = True
            if verdict is None and str(run.get("status")) in {"failed", "cancelled", "timed_out"}:
                verdict = False
            if verdict is not None:
                call["acknowledged"] = verdict
                call["ack_latency_ms"] = round((time.time() - started) * 1000.0, 3)
                pending.remove(call)
        if pending:
            time.sleep(0.5)
    for call in pending:
        call["acknowledged"] = False
        call["ack_detail"] = f"No acknowledgement within {timeout_s:.0f}s."
    by_key = {(c.get("agent_id"), c.get("action_id")): c.get("acknowledged") for c in tool_calls if not c.get("cached_result")}
    for call in tool_calls:
        if call.get("cached_result") and call.get("acknowledged") is None:
            call["acknowledged"] = by_key.get((call.get("agent_id"), call.get("action_id")))


def seed_conflict_if_needed(intent: Dict[str, Any], method: str, duration_s: int) -> Dict[str, Any]:
    """Start the seeded "other operator" workload, identically for every method (P1-8).

    The seed is the lease-holding action of the seed workflow (its first write-scope action:
    TC apply-codel for transport-qos, SLICE monitor for slice-assurance) launched as a plain
    action, so the agent is busy for the action's 30 s run whatever method follows.
    """
    del method, duration_s
    seed_workflow = intent.get("conflict_seed")
    if not seed_workflow:
        return {"applied": False}
    action_pairs = actions_for_workflow(str(seed_workflow))
    writers = [pair for pair in action_pairs if _agent_writes(pair[0])]
    if not (writers or action_pairs):
        return {"applied": False}
    agent_id, action_id = (writers or action_pairs)[0]
    tool_call, run_payload, error = invoke_action(agent_id, action_id)
    return {
        "applied": True,
        "type": "action",
        "workflow_id": seed_workflow,
        "agent_id": agent_id,
        "action_id": action_id,
        "run_id": (run_payload or {}).get("id"),
        "status": tool_call.get("status"),
        "error": error,
        "started_at": time.time(),
    }


def detect_conflict(execution: Dict[str, Any], tool_calls: List[Dict[str, Any]]) -> bool:
    if str(execution.get("status") or "") == "queued":
        return True
    if execution.get("blocked_reason"):
        return True
    # A lease refusal (409) inside a template workflow is the same event as `blocked_reason` on a custom chain.
    return any(call.get("status") in {"conflict", "queued"} or is_lease_refusal(call) for call in tool_calls)


def detect_failure(execution: Dict[str, Any], tool_calls: List[Dict[str, Any]]) -> bool:
    status = str(execution.get("status") or "")
    if status in {"failed", "completed_with_issues", "cancelled", "expired"}:
        return True
    return any(call.get("status") == "failed" for call in tool_calls)


def policy_validation(generated_workflow_id: Optional[str], generated_workflow: List[str], tool_calls: List[Dict[str, Any]]) -> Tuple[bool, bool, List[str]]:
    notes: List[str] = []
    if not generated_workflow_id and not generated_workflow and not tool_calls:
        notes.append("No workflow or tool calls were generated.")
    workflow_id_text = str(generated_workflow_id or "").strip()
    if workflow_id_text and workflow_id_text not in WORKFLOW_TEMPLATES and not workflow_id_text.startswith("custom:"):
        notes.append(f"Unknown workflow id: {generated_workflow_id}")
    known_agents = {str(agent_id).upper() for agent_id in AGENTS.keys()}
    hallucinated = False
    for xapp in generated_workflow:
        if str(xapp).upper() not in known_agents:
            hallucinated = True
            notes.append(f"Unknown generated xApp: {xapp}")
    for call in tool_calls:
        agent_id = str(call.get("agent_id") or "")
        action_id = str(call.get("action_id") or "")
        agent = AGENTS.get(agent_id)
        if agent is None:
            hallucinated = True
            notes.append(f"Unknown tool-call agent: {agent_id}")
            continue
        if not any(action.id == action_id for action in agent.actions):
            hallucinated = True
            notes.append(f"Unknown action '{action_id}' for agent '{agent_id}'")
    return len(notes) == 0, hallucinated, notes


def parse_llm_plan(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(match.group(0))


def normalize_generated_workflow(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip().upper() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"\s*(?:->|=>|→|,|\|)\s*", value.strip())
        return [part.strip().upper() for part in parts if part.strip()]
    return []


def normalize_discovery_steps(value: Any) -> List[Dict[str, str]]:
    steps: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return steps
    for item in value:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("agent_id") or item.get("agent") or "").strip().lower()
        action_id = str(item.get("action_id") or item.get("action") or "").strip()
        if not agent_id:
            continue
        step = {"agent_id": agent_id}
        if action_id:
            step["action_id"] = action_id
        steps.append(step)
    return steps


def llm_prompt(intent: Dict[str, Any]) -> str:
    workflows = []
    for workflow_id, template in WORKFLOW_TEMPLATES.items():
        workflows.append(
            {
                "workflow_id": workflow_id,
                "description": template.get("description", ""),
                "action_chain": normalize_action_chain(workflow_id),
            }
        )
    return (
        "You are selecting exactly one workflow for the current FlexRIC portal.\n"
        "Return only JSON with keys workflow_id, generated_workflow, and rationale.\n"
        "Rules:\n"
        "- workflow_id must be one of the provided workflow_id values.\n"
        "- generated_workflow must exactly match the selected workflow action_chain.\n"
        "- Do not invent new xApps or reorder the selected workflow.\n"
        "- If uncertain, choose the closest valid workflow instead of returning an empty plan.\n"
        f"Intent: {intent.get('intent')}\n"
        f"Available workflows: {json.dumps(workflows)}\n"
    )


def llm_blind_prompt(intent: Dict[str, Any]) -> str:
    # No catalog, no agent cards: the model must name applications from its
    # own knowledge, which is what an ungrounded baseline actually looks like.
    return (
        "You are the orchestrator of an O-RAN Non-RT RIC. Compose an ordered workflow of\n"
        "xApps/rApps that realizes the operator intent below.\n"
        "Return only JSON with keys generated_workflow and rationale.\n"
        "- generated_workflow is a list of application names in execution order (1 to 4 items).\n"
        "- Use short upper-case application identifiers.\n"
        f"Intent: {intent.get('intent')}\n"
    )


def assert_prompt_label_free(prompt: str) -> None:
    """P0-1: no planner prompt may carry the intent's `notes` annotation."""
    notes = str(_RECORD_STATE.get("notes") or "").strip()
    if notes and notes in prompt:
        raise AssertionError("Planner prompt contains the intent's `notes` annotation (label leakage).")
    if "\nNotes: " in prompt or "\nCategory: " in prompt:
        raise AssertionError("Planner prompt carries a Notes:/Category: line (label leakage).")


def planner_task(prompt: str) -> Dict[str, Any]:
    """Every planner call of every method goes through here (label-leakage assert)."""
    assert_prompt_label_free(prompt)
    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=prompt, provider="auto"))
    return dict(task_payload.get("task") or {})


def plan_blind(intent: Dict[str, Any]) -> Dict[str, Any]:
    task = planner_task(llm_blind_prompt(intent))
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        return {
            "ok": False,
            "planner_task": task,
            "planner_error": response_text or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
            "generated_workflow": [],
            "rationale": "",
        }
    try:
        plan = parse_llm_plan(response_text)
    except Exception as exc:
        plan = {"generated_workflow": [], "rationale": f"unparseable: {exc}"}
    return {
        "ok": True,
        "planner_task": task,
        "planner_plan": plan,
        "planner_error": "",
        "planner_unavailable": False,
        "method_available": True,
        "generated_workflow": normalize_generated_workflow(plan.get("generated_workflow")),
        "rationale": str(plan.get("rationale") or ""),
    }


def _planner_cache_key(intent: Dict[str, Any]) -> str:
    return str(intent.get("id") or intent.get("intent") or uuid.uuid4().hex)


def plan_with_llm(intent: Dict[str, Any]) -> Dict[str, Any]:
    key = _planner_cache_key(intent)
    cache_ttl_s = float(EVAL_RUNTIME_CONFIG.get("planner_cache_ttl_s") or 0.0)
    cached = _PLANNER_RESULT_CACHE.get(key)
    if cached is not None and cache_ttl_s > 0.0:
        age_s = max(0.0, time.time() - float(cached.get("captured_at") or time.time()))
        if age_s < cache_ttl_s:
            result = copy.deepcopy(cached["result"])
            result["planner_cached"] = True
            result["planner_cache_age_s"] = round(age_s, 3)
            return result

    task = planner_task(llm_prompt(intent))
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        result = {
            "ok": False,
            "planner_cached": False,
            "planner_cache_age_s": 0.0,
            "planner_task": task,
            "planner_error": response_text or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
            "workflow_id": None,
            "generated_workflow": [],
            "rationale": "",
        }
        _PLANNER_RESULT_CACHE[key] = {"captured_at": time.time(), "result": copy.deepcopy(result)}
        return result

    plan = parse_llm_plan(response_text)
    result = {
        "ok": True,
        "planner_cached": False,
        "planner_cache_age_s": 0.0,
        "planner_task": task,
        "planner_plan": plan,
        "planner_error": "",
        "planner_unavailable": False,
        "method_available": True,
        "workflow_id": plan.get("workflow_id"),
        "generated_workflow": normalize_generated_workflow(plan.get("generated_workflow")),
        "rationale": str(plan.get("rationale") or ""),
    }
    _PLANNER_RESULT_CACHE[key] = {"captured_at": time.time(), "result": copy.deepcopy(result)}
    return result


def validate_or_repair_plan(intent: Dict[str, Any], planned_workflow_id: Any, generated_workflow: List[str]) -> Dict[str, Any]:
    requested_id = str(planned_workflow_id or "").strip()
    normalized_chain = [str(item).strip().upper() for item in generated_workflow if str(item).strip()]
    policy_workflow_id = route_intent(intent)

    if requested_id in WORKFLOW_TEMPLATES and requested_id != policy_workflow_id:
        return {
            "workflow_id": policy_workflow_id,
            "generated_workflow": normalize_action_chain(policy_workflow_id),
            "planner_repaired": True,
            "repair_reason": "Policy-catalog validation corrected the LLM-selected workflow family for this intent.",
        }

    if requested_id in WORKFLOW_TEMPLATES:
        expected_chain = normalize_action_chain(requested_id)
        if normalized_chain == expected_chain:
            return {
                "workflow_id": requested_id,
                "generated_workflow": expected_chain,
                "planner_repaired": False,
                "repair_reason": "",
            }
        return {
            "workflow_id": requested_id,
            "generated_workflow": expected_chain,
            "planner_repaired": True,
            "repair_reason": "Normalized the action chain to the selected valid workflow template.",
        }

    inferred_workflow_id = workflow_id_from_chain(normalized_chain)
    if inferred_workflow_id and inferred_workflow_id == policy_workflow_id:
        return {
            "workflow_id": inferred_workflow_id,
            "generated_workflow": normalize_action_chain(inferred_workflow_id),
            "planner_repaired": True,
            "repair_reason": "Inferred the workflow from a valid generated action chain.",
        }

    fallback_workflow_id = route_intent(intent)
    return {
        "workflow_id": fallback_workflow_id,
        "generated_workflow": normalize_action_chain(fallback_workflow_id),
        "planner_repaired": True,
        "repair_reason": "Fell back to the validated workflow catalog route because the LLM plan was incomplete or invalid.",
    }


def agentcard_prompt(intent: Dict[str, Any]) -> str:
    """AppWeaver's Compose prompt for an intent record (the graph builds the same prompt)."""
    return compose_prompt(str(intent.get("intent") or ""), executable_agent_cards(intent))


def prompt_builders_sha256() -> Dict[str, str]:
    """Hash of each planner prompt builder's source, so a batch pins the exact prompts it used."""
    builders = [
        llm_prompt, llm_blind_prompt, agentcard_prompt, agentcard_recovery_prompt, llm_recovery_prompt,
        appweaver_prompts.compose_prompt, appweaver_prompts.recovery_prompt, appweaver_prompts.serialize_cards,
        _intent_text, route_intent, default_action_for_agent,
    ]
    hashes = {f"{fn.__module__.split('.')[-1]}.{fn.__name__}": hashlib.sha256(inspect.getsource(fn).encode("utf-8")).hexdigest()[:16] for fn in builders}
    hashes["appweaver.prompts_module"] = hashlib.sha256(inspect.getsource(appweaver_prompts).encode("utf-8")).hexdigest()[:16]
    return hashes


def agentcard_recovery_prompt(intent: Dict[str, Any], execution: Dict[str, Any], busy_resources: Optional[List[Dict[str, Any]]] = None) -> str:
    """AppWeaver's Recover prompt for an intent record (the graph builds the same prompt)."""
    failure_summary = {
        "trigger": execution.get("recover_trigger", "precheck_busy"),
        "chain": execution.get("generated_workflow"),
        "already_running": [],
        "refusal": execution.get("blocked_reason") or None,
    }
    return recovery_prompt(str(intent.get("intent") or ""), failure_summary, executable_agent_cards(intent), list(busy_resources or []))


def llm_recovery_prompt(intent: Dict[str, Any], execution: Dict[str, Any]) -> str:
    failure_summary = {
        "status": execution.get("status"),
        "blocked_reason": execution.get("blocked_reason", ""),
        "generated_workflow_id": execution.get("generated_workflow_id"),
        "generated_workflow": execution.get("generated_workflow"),
        "tool_calls": [
            {
                "xapp": call.get("xapp"),
                "status": call.get("status"),
                "detail": call.get("detail", ""),
            }
            for call in list(execution.get("tool_calls") or [])
        ],
    }
    workflows = []
    for workflow_id, template in WORKFLOW_TEMPLATES.items():
        workflows.append(
            {
                "workflow_id": workflow_id,
                "description": template.get("description", ""),
                "action_chain": normalize_action_chain(workflow_id),
            }
        )
    return (
        "You are repairing a LangGraph orchestration attempt in the current FlexRIC portal.\n"
        "Return only JSON with keys workflow_id, generated_workflow, mode, approve, and rationale.\n"
        "Rules:\n"
        "- workflow_id must be one of the provided workflow_id values.\n"
        "- generated_workflow must exactly match that workflow's action_chain.\n"
        "- mode must be either 'enforced' or 'advisory'.\n"
        "- approve must be true only when advisory mode should be manually approved immediately.\n"
        "- Never cancel or reset another workflow; busy applications are waited for, bounded.\n"
        "- Prefer the safest valid recovery that preserves the intent.\n"
        f"Intent: {intent.get('intent')}\n"
        f"Failure summary: {json.dumps(failure_summary)}\n"
        f"Available workflows: {json.dumps(workflows)}\n"
    )


def _recovery_cache_key(intent: Dict[str, Any], execution: Dict[str, Any]) -> str:
    base = _planner_cache_key(intent)
    signature = {
        "status": execution.get("status"),
        "blocked_reason": execution.get("blocked_reason", ""),
        "tool_statuses": [
            (call.get("xapp"), call.get("status"))
            for call in list(execution.get("tool_calls") or [])
        ],
    }
    return f"{base}:{json.dumps(signature, sort_keys=True)}"


def plan_recovery_with_llm(intent: Dict[str, Any], execution: Dict[str, Any]) -> Dict[str, Any]:
    key = _recovery_cache_key(intent, execution)
    cache_ttl_s = float(EVAL_RUNTIME_CONFIG.get("planner_cache_ttl_s") or 0.0)
    cached = _RECOVERY_PLANNER_CACHE.get(key)
    if cached is not None and cache_ttl_s > 0.0:
        age_s = max(0.0, time.time() - float(cached.get("captured_at") or time.time()))
        if age_s < cache_ttl_s:
            result = copy.deepcopy(cached["result"])
            result["planner_cached"] = True
            result["planner_cache_age_s"] = round(age_s, 3)
            return result

    task = planner_task(llm_recovery_prompt(intent, execution))
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        fallback_mode = "advisory" if (detect_conflict(execution, list(execution.get("tool_calls") or [])) or detect_failure(execution, list(execution.get("tool_calls") or []))) else "enforced"
        fallback = {
            "workflow_id": execution.get("generated_workflow_id") or route_intent(intent),
            "generated_workflow": list(execution.get("generated_workflow") or normalize_action_chain(str(execution.get("generated_workflow_id") or route_intent(intent)))),
            "mode": fallback_mode,
            "approve": fallback_mode == "advisory",
            "reset_runtime": False,
            "rationale": "Used deterministic recovery fallback because the LLM recovery planner was unavailable.",
            "planner_repaired": True,
            "repair_reason": "Deterministic fallback recovery plan.",
            "planner_task": task,
            "planner_error": response_text or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
            "planner_cached": False,
        }
        _RECOVERY_PLANNER_CACHE[key] = {"captured_at": time.time(), "result": copy.deepcopy(fallback)}
        return fallback

    plan = parse_llm_plan(response_text)
    repaired = validate_or_repair_plan(intent, plan.get("workflow_id"), normalize_generated_workflow(plan.get("generated_workflow")))
    mode = str(plan.get("mode") or "advisory").strip().lower()
    if mode not in {"enforced", "advisory"}:
        mode = "advisory"
    result = {
        "workflow_id": repaired.get("workflow_id"),
        "generated_workflow": list(repaired.get("generated_workflow") or []),
        "mode": mode,
        "approve": bool(plan.get("approve")) or mode == "advisory",
        "reset_runtime": False,
        "rationale": str(plan.get("rationale") or ""),
        "planner_repaired": bool(repaired.get("planner_repaired")),
        "repair_reason": str(repaired.get("repair_reason") or ""),
        "planner_task": task,
        "planner_plan": plan,
        "planner_error": "",
        "planner_unavailable": False,
        "method_available": True,
        "planner_cached": False,
    }
    _RECOVERY_PLANNER_CACHE[key] = {"captured_at": time.time(), "result": copy.deepcopy(result)}
    return result


def execute_manual_rule(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    del duration_s
    workflow_id = route_intent(intent)
    result = run_action_pairs(actions_for_workflow(workflow_id))
    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": normalize_action_chain(workflow_id),
        **result,
        "manual_override": False,
    }


def execute_single_xapp(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    del duration_s
    workflow_id = route_intent(intent)
    action_pairs = actions_for_workflow(workflow_id)[:1]
    result = run_action_pairs(action_pairs)
    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": [agent_id.upper() for agent_id, _ in action_pairs],
        **result,
        "manual_override": False,
    }


def execute_langgraph_workflow(intent: Dict[str, Any], workflow_id: str, generated_workflow: List[str], duration_s: int, mode: str, manual_override: bool) -> Dict[str, Any]:
    workflow = api_workflow_run(
        workflow_id,
        WorkflowRequest(goal=str(intent.get("intent")), mode=mode, duration_s=duration_s),
    )["run"]

    if manual_override and (workflow.get("selected_actions") or workflow.get("approval_required")):
        workflow = api_workflow_approve(
            str(workflow["id"]),
            WorkflowApprovalRequest(reason="Evaluation baseline manual override."),
        )["run"]

    workflow = poll_workflow_until_stable(str(workflow["id"]), workflow)
    result_workflow = [str(item.get("agent_id")).upper() for item in list(workflow.get("selected_actions") or [])]
    tool_calls = [
        build_tool_call(
            str(item.get("agent_id") or ""),
            str(item.get("action_id") or ""),
            0.0,
            item,
        )
        for item in list(workflow.get("run_results") or [])
    ]
    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": generated_workflow or result_workflow,
        "tool_calls": tool_calls,
        "workflow_run": workflow,
        "raw_runs": list(workflow.get("run_results") or []),
        "status": workflow.get("status"),
        "blocked_reason": workflow.get("blocked_reason", ""),
        "manual_override": manual_override,
        "method_available": True,
    }


def execute_langgraph(intent: Dict[str, Any], duration_s: int, mode: str, manual_override: bool) -> Dict[str, Any]:
    planner = plan_with_llm(intent)
    if not planner.get("ok"):
        return {
            "generated_workflow_id": None,
            "generated_workflow": [],
            "tool_calls": [],
            "raw_runs": [],
            "workflow_run": None,
            "status": "unavailable" if planner.get("planner_unavailable") else "failed",
            "blocked_reason": "",
            "manual_override": manual_override,
            "method_available": bool(planner.get("method_available", True)),
            "planner_task": planner.get("planner_task"),
            "planner_error": planner.get("planner_error", ""),
            "planner_unavailable": planner.get("planner_unavailable", False),
            "planner_cached": planner.get("planner_cached", False),
        }

    repaired = validate_or_repair_plan(intent, planner.get("workflow_id"), list(planner.get("generated_workflow") or []))
    workflow_id = str(repaired["workflow_id"])
    execution = execute_langgraph_workflow(
        intent=intent,
        workflow_id=workflow_id,
        generated_workflow=list(repaired.get("generated_workflow") or []),
        duration_s=duration_s,
        mode=mode,
        manual_override=manual_override,
    )
    execution.update(
        {
            "method_available": True,
            "planner_task": planner.get("planner_task"),
            "planner_plan": planner.get("planner_plan"),
            "planner_cached": planner.get("planner_cached", False),
            "planner_repaired": repaired.get("planner_repaired", False),
            "planner_repair_reason": repaired.get("repair_reason", ""),
            "planner_workflow_id": planner.get("workflow_id"),
            "planner_generated_workflow": planner.get("generated_workflow"),
        }
    )
    return execution


def execute_langgraph_llm(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    initial = execute_langgraph(intent, duration_s, mode="enforced", manual_override=False)
    if initial.get("method_available") is False:
        return initial

    tool_calls = list(initial.get("tool_calls") or [])
    initial_conflict = detect_conflict(initial, tool_calls)
    initial_failure = detect_failure(initial, tool_calls)
    if not (initial_conflict or initial_failure):
        initial["internal_recovery_attempted"] = False
        initial["internal_recovery_succeeded"] = False
        return initial

    recovery_plan = plan_recovery_with_llm(intent, initial)
    if recovery_plan.get("method_available") is False:
        initial["internal_recovery_attempted"] = True
        initial["internal_recovery_succeeded"] = False
        initial["recovery_planner_task"] = recovery_plan.get("planner_task")
        initial["recovery_planner_error"] = recovery_plan.get("planner_error", "")
        return initial

    # No runtime reset (that would pre-empt the other workflow): wait, bounded, for the agents the
    # first attempt found busy, then run the recovery plan.
    busy_agents = sorted({str(call.get("agent_id")) for call in tool_calls if is_lease_refusal(call) and call.get("agent_id")})
    recovery_wait = wait_until_free(busy_agents, float(EVAL_RUNTIME_CONFIG.get("lease_wait_s") or 0.0)) if busy_agents else {"free": True, "waited_s": 0.0}
    _RECORD_STATE["lease_wait_s"] = float(_RECORD_STATE.get("lease_wait_s") or 0.0) + float(recovery_wait.get("waited_s") or 0.0)
    recovery_reset_applied = False

    recovery_execution = execute_langgraph_workflow(
        intent=intent,
        workflow_id=str(recovery_plan.get("workflow_id") or route_intent(intent)),
        generated_workflow=list(recovery_plan.get("generated_workflow") or normalize_action_chain(str(recovery_plan.get("workflow_id") or route_intent(intent)))),
        duration_s=duration_s,
        mode=str(recovery_plan.get("mode") or "advisory"),
        manual_override=bool(recovery_plan.get("approve")),
    )
    recovery_tool_calls = list(recovery_execution.get("tool_calls") or [])
    recovery_conflict = detect_conflict(recovery_execution, recovery_tool_calls)
    recovery_failure = detect_failure(recovery_execution, recovery_tool_calls)
    recovery_success = not recovery_conflict and not recovery_failure

    initial_snapshot = copy.deepcopy(initial)
    recovery_snapshot = copy.deepcopy(recovery_execution)
    final_execution = copy.deepcopy(recovery_execution if recovery_success else initial)
    final_execution.update(
        {
            "method_available": True,
            "planner_task": initial.get("planner_task"),
            "planner_plan": initial.get("planner_plan"),
            "planner_cached": initial.get("planner_cached", False),
            "planner_repaired": initial.get("planner_repaired", False),
            "planner_repair_reason": initial.get("planner_repair_reason", ""),
            "planner_workflow_id": initial.get("planner_workflow_id"),
            "planner_generated_workflow": initial.get("planner_generated_workflow"),
            "internal_recovery_attempted": True,
            "internal_recovery_succeeded": recovery_success,
            "initial_execution": initial_snapshot,
            "recovery_planner_task": recovery_plan.get("planner_task"),
            "recovery_planner_plan": recovery_plan.get("planner_plan"),
            "recovery_planner_cached": recovery_plan.get("planner_cached", False),
            "recovery_planner_repaired": recovery_plan.get("planner_repaired", False),
            "recovery_planner_reason": recovery_plan.get("repair_reason", ""),
            "recovery_mode": recovery_plan.get("mode"),
            "recovery_manual_override": recovery_plan.get("approve"),
            "recovery_reset_runtime": recovery_reset_applied,
            "recovery_execution": recovery_snapshot,
        }
    )
    return final_execution


def _appweaver_deps() -> AppWeaverDeps:
    """Inject the harness side effects into the AppWeaver graph."""
    dryrun_fn, dryrun_reason = (None, "")
    if str(EVAL_RUNTIME_CONFIG.get("validate_mode") or "checks") == "dryrun":
        dryrun_fn, dryrun_reason = resolve_dryrun()
    return AppWeaverDeps(
        registry=AGENTS,
        discover=lambda text, exclude: discover_for_text(text, exclude),
        planner=planner_task,
        invoke=invoke_with_lease_wait,
        lease_query=active_runs_by_agent,
        wait_until_free=wait_until_free,
        resolve_action=lambda agent_id, text: default_action_for_agent(agent_id, {"intent": text}),
        is_unavailable=_is_provider_unavailable,
        e2_functions=live_e2_ran_functions,
        dryrun_fn=dryrun_fn,
        dryrun_reason=dryrun_reason,
    )


def execute_langgraph_agentcard(intent: Dict[str, Any], duration_s: int, repair: bool = True, recover: bool = True) -> Dict[str, Any]:
    """AppWeaver (repair=recover=True) or its ablation agentcard_no_repair (both False).

    Runs the LangGraph StateGraph in backend/appweaver: Discover -> Compose -> Validate ->
    Deploy (-> Recover) -> Finish. The graph only sees the intent sentence.
    """
    del duration_s
    cfg = AppWeaverConfig(
        variant="appweaver" if (repair and recover) else ("no_repair" if not (repair or recover) else f"repair={repair},recover={recover}"),
        repair=repair,
        recover=recover,
        validate_mode=str(EVAL_RUNTIME_CONFIG.get("validate_mode") or "checks"),
        lease_wait_s=float(EVAL_RUNTIME_CONFIG.get("lease_wait_s") or 0.0),
        dryrun_duration_s=int(EVAL_RUNTIME_CONFIG.get("dryrun_duration_s") or 5),
    )
    final = run_appweaver(str(intent.get("intent") or ""), _appweaver_deps(), cfg)
    chain = list(final.get("generated_workflow") or [])
    task = final.get("planner_task") or {}
    repair_events = list(final.get("repair_events") or [])
    moves = [str(event.get("move")) for event in repair_events]
    recovery = final.get("recovery") or {}
    status = str(final.get("status") or "failed")
    unavailable = bool(final.get("planner_unavailable"))
    validation = final.get("validation_report") or {}
    return {
        "generated_workflow_id": (workflow_id_from_chain(chain) or custom_workflow_id_from_chain(chain)) if chain else None,
        "generated_workflow": chain,
        "tool_calls": list(final.get("tool_calls") or []),
        "raw_runs": list(final.get("run_payloads") or []),
        "workflow_run": None,
        "status": status,
        "blocked_reason": str(final.get("blocked_reason") or ""),
        "manual_override": False,
        "method_available": not unavailable,
        "planner_task": task,
        "planner_plan": final.get("planner_plan"),
        "planner_error": "" if task.get("status") == "completed" else str(task.get("response") or task.get("error") or ""),
        "planner_unavailable": unavailable,
        "planner_repaired": bool(moves),
        "planner_repair_reason": ", ".join(moves),
        "failure_reason": final.get("failure_reason", ""),
        "raw_chain": final.get("raw_chain"),
        "selected_steps": list(final.get("steps") or []),
        "compat_report": final.get("compat_report"),
        "repair_events": repair_events,
        "retrieval": {**annotate_retrieval(final.get("retrieval") or {}, intent),
                      # planner prompt size of the Compose call (registry-scale cost of k)
                      "prompt_chars": next((p.get("chars") for p in final.get("prompts") or [] if p.get("node") == "compose"), None)},
        "validation_report": validation,
        "validation_history": list(final.get("validation_history") or []),
        "validate_mode": validation.get("mode") or cfg.validate_mode,
        "graph_backend": final.get("graph_backend"),
        "graph_variant": final.get("graph_variant"),
        "graph_nodes": final.get("graph_nodes"),
        "workflow_events": list(final.get("events") or []),
        "prompt_sizes": list(final.get("prompts") or []),
        "conflict_detected_before_control": bool(final.get("conflict_detected_before_control")),
        "partial_deployment": bool(final.get("partial_deployment")),
        "replanned_around_resource": bool(final.get("replanned_around_resource")),
        "waited_for_lease": bool(final.get("waited_for_lease")),
        "graph_lease_wait_s": round(float(final.get("lease_wait_s") or 0.0), 3),
        "internal_recovery_attempted": int(final.get("recoveries") or 0) > 0,
        "internal_recovery_succeeded": int(final.get("recoveries") or 0) > 0 and status == "completed",
        "recovery": recovery,
        "recovery_planner_task": recovery.get("planner_task"),
        "recovery_planner_plan": recovery.get("planner_plan"),
        "recovery_reset_runtime": False,
    }


def poll_workflow_until_stable(run_id: str, initial_workflow: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    workflow = dict(initial_workflow or api_workflow_status(run_id))
    timeout_s = float(EVAL_RUNTIME_CONFIG.get("workflow_poll_timeout_s") or 0.0)
    interval_s = max(0.01, float(EVAL_RUNTIME_CONFIG.get("workflow_poll_interval_s") or 0.05))
    if timeout_s <= 0.0:
        return workflow

    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        status = str(workflow.get("status") or "")
        run_results = list(workflow.get("run_results") or [])
        if run_results:
            break
        if status == "waiting_for_approval":
            break
        if status == "queued":
            break
        if status not in WORKFLOW_TRANSITIONAL_STATUSES:
            break
        time.sleep(interval_s)
        workflow = dict(api_workflow_status(run_id))
    return workflow


def execute_llm_only(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    planner = plan_with_llm(intent)
    if not planner.get("ok"):
        planner_unavailable = bool(planner.get("planner_unavailable"))
        return {
            "generated_workflow_id": None,
            "generated_workflow": [],
            "tool_calls": [],
            "raw_runs": [],
            "workflow_run": None,
            "status": "unavailable" if planner_unavailable else "failed",
            "blocked_reason": "",
            "manual_override": False,
            "planner_task": planner.get("planner_task"),
            "planner_error": planner.get("planner_error", "") or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
            "planner_cached": planner.get("planner_cached", False),
        }
    workflow_id = planner.get("workflow_id")
    generated_workflow = list(planner.get("generated_workflow") or [])
    if workflow_id in WORKFLOW_TEMPLATES:
        action_pairs = actions_for_workflow(str(workflow_id))
    else:
        action_pairs = []
        known_by_label = {agent_id.upper(): agent_id for agent_id in AGENTS.keys()}
        for name in generated_workflow:
            agent_id = known_by_label.get(name)
            if not agent_id:
                continue
            actions = AGENTS[agent_id].actions
            if actions:
                action_pairs.append((agent_id, actions[0].id))

    result = run_action_pairs(action_pairs)

    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": generated_workflow,
        **result,
        "workflow_run": None,
        "manual_override": False,
        "planner_task": planner.get("planner_task"),
        "planner_plan": planner.get("planner_plan"),
        "method_available": True,
        "planner_cached": planner.get("planner_cached", False),
    }


def _is_provider_unavailable(detail: str) -> bool:
    text = str(detail or "").lower()
    if not text:
        return False
    markers = [
        "max retries exceeded",
        "failed to establish a new connection",
        "connection refused",
        "connectionerror",
        "name or service not known",
        "temporarily unavailable",
        "is not configured",      # LLM_PROVIDER pinned to a provider without its env vars
        "returned http 401",      # vLLM/OpenAI: wrong or missing API key
        "returned http 403",
        "returned http 404",      # wrong base URL or served model id
        "returned http 503",
    ]
    return any(marker in text for marker in markers)


def execute_llm_blind(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    del duration_s
    planner = plan_blind(intent)
    if not planner.get("ok"):
        planner_unavailable = bool(planner.get("planner_unavailable"))
        return {
            "generated_workflow_id": None,
            "generated_workflow": [],
            "tool_calls": [],
            "raw_runs": [],
            "workflow_run": None,
            "status": "unavailable" if planner_unavailable else "failed",
            "blocked_reason": "",
            "manual_override": False,
            "planner_task": planner.get("planner_task"),
            "planner_error": planner.get("planner_error", ""),
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
        }
    generated_workflow = list(planner.get("generated_workflow") or [])
    known_by_label = {agent_id.upper(): agent_id for agent_id in AGENTS.keys()}
    action_pairs: List[Tuple[str, str]] = []
    for name in generated_workflow:
        agent_id = known_by_label.get(name)
        if not agent_id or not AGENTS[agent_id].actions:
            # Unknown application: nothing to launch, policy_validation records
            # the hallucinated reference from generated_workflow.
            continue
        action_id = default_action_for_agent(agent_id, intent) or AGENTS[agent_id].actions[0].id
        action_pairs.append((agent_id, action_id))
    result = run_action_pairs(action_pairs)
    return {
        "generated_workflow_id": workflow_id_from_chain(generated_workflow) or custom_workflow_id_from_chain(generated_workflow),
        "generated_workflow": generated_workflow,
        **result,
        "workflow_run": None,
        "manual_override": False,
        "planner_task": planner.get("planner_task"),
        "planner_plan": planner.get("planner_plan"),
        "method_available": True,
    }


def execute_method(method: str, intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    if method == "manual_rule":
        return execute_manual_rule(intent, duration_s)
    if method == "llm_blind":
        return execute_llm_blind(intent, duration_s)
    if method == "agentcard_no_repair":
        return execute_langgraph_agentcard(intent, duration_s, repair=False, recover=False)
    if method == "single_xapp":
        return execute_single_xapp(intent, duration_s)
    if method == "langgraph_override":
        return execute_langgraph(intent, duration_s, mode="advisory", manual_override=True)
    if method == "langgraph_enforced":
        return execute_langgraph(intent, duration_s, mode="enforced", manual_override=False)
    if method == "langgraph_llm":
        return execute_langgraph_llm(intent, duration_s)
    if method == "langgraph_agentcard":
        return execute_langgraph_agentcard(intent, duration_s)
    if method == "llm_only":
        return execute_llm_only(intent, duration_s)
    raise ValueError(f"Unsupported method: {method}")


def conflict_outcome(execution: Dict[str, Any], tool_calls: List[Dict[str, Any]], failure_detected: bool) -> Dict[str, Any]:
    """Seeded-conflict fields, computed the same way for every method (P0-2).

    conflict_detected_before_control: the busy application was noticed before a control to it
      was issued -- AppWeaver's Validate lease pre-check, or a lease refusal (409) by the portal.
    partial_deployment: some control (write-scope) step had already been launched when the first
      refusal happened (the chain was half-deployed when the conflict surfaced).
    completed_after_wait: the record ended with every step launched after a bounded lease wait.
    replanned_around_resource: AppWeaver's Recover re-planned without the busy application.
    preempted_other_workflow: a reset ran during the record (must never happen; asserted).
    """
    writes_done = 0
    partial = False
    refused_seen = False
    for call in tool_calls:
        if is_lease_refusal(call) or call.get("lease_refusal"):
            partial = writes_done > 0
            refused_seen = True
            break
        if call.get("status") == "success" and _step_writes(str(call.get("agent_id") or ""), call.get("action_id")):
            writes_done += 1
    if "partial_deployment" in execution:
        partial = bool(execution.get("partial_deployment")) or partial
    precheck = bool(execution.get("conflict_detected_before_control"))
    # AppWeaver's graph accounts its own waits (Recover + Deploy); baselines' waits are in _RECORD_STATE.
    lease_wait = round(float(execution["graph_lease_wait_s"] if "graph_lease_wait_s" in execution else (_RECORD_STATE.get("lease_wait_s") or 0.0)), 3)
    unresolved = str(execution.get("status") or "") in {"queued", "blocked_by_conflict"} or any(
        (call.get("lease_refusal") and not any(
            later.get("retry_after_lease_wait") and later.get("agent_id") == call.get("agent_id") and later.get("status") == "success"
            for later in tool_calls))
        for call in tool_calls
    )
    waited = lease_wait > 0.0 or bool(execution.get("waited_for_lease"))
    preempted = int(_RECORD_STATE.get("reset_calls") or 0) > 0
    return {
        "lease_wait_s": lease_wait,
        "conflict_detected_before_control": precheck or refused_seen,
        "partial_deployment": partial,
        "completed_after_wait": waited and not unresolved and not failure_detected and str(execution.get("status") or "") == "completed",
        "replanned_around_resource": bool(execution.get("replanned_around_resource")),
        "lease_refusal_unresolved": unresolved,
        "preempted_other_workflow": preempted,
    }


def score_with_label_rules(chain: List[str], intent: Dict[str, Any]) -> Tuple[Optional[bool], Optional[List[str]]]:
    """Pre-registered partial-order label rule (evaluation/label_rules.py, separate workstream)."""
    try:
        from evaluation import label_rules  # type: ignore
    except Exception:
        return None, None
    try:
        matched, reasons = label_rules.rule_match(list(chain), intent, AGENTS)
        return bool(matched), [str(reason) for reason in (reasons or [])]
    except Exception as exc:  # scoring must never kill a record
        return None, [f"label_rules error: {exc!r}"]


def build_record(
    *,
    intent: Dict[str, Any],
    method: str,
    repeat_index: int,
    duration_s: int,
    before_snapshot: Dict[str, Any],
    after_snapshot: Dict[str, Any],
    execution: Dict[str, Any],
    orchestration_latency_ms: float,
    recovery_attempted: bool,
    recovered_from_failure: bool,
    recovery_result: Optional[Dict[str, Any]],
    conflict_seed: Dict[str, Any],
    method_error: Optional[str] = None,
) -> Dict[str, Any]:
    expected_workflow = list(intent.get("expected_workflow") or [])
    generated_workflow = list(execution.get("generated_workflow") or [])
    tool_calls = list(execution.get("tool_calls") or [])
    execution_artifacts = {
        key: value
        for key, value in execution.items()
        if key
        not in {
            "generated_workflow_id",
            "generated_workflow",
            "tool_calls",
            "raw_runs",
            "workflow_run",
            "status",
            "blocked_reason",
            "manual_override",
        }
    }
    policy_valid, hallucinated_api, policy_notes = policy_validation(
        execution.get("generated_workflow_id"),
        generated_workflow,
        tool_calls,
    )
    # With internal recovery `execution` is the clean re-run; a conflict hit on the first execution
    # (refused before control) still counts as detected.
    initial_execution = execution.get("initial_execution")
    conflict_detected = detect_conflict(execution, tool_calls) or (
        isinstance(initial_execution, dict)
        and detect_conflict(initial_execution, list(initial_execution.get("tool_calls") or []))
    )
    failure_detected = bool(method_error) or detect_failure(execution, tool_calls)
    conflict_label = intent.get("expects_conflict")
    workflow_run = execution.get("workflow_run")
    tool_launch_success = sum(1 for call in tool_calls if call.get("status") == "success")
    tool_success = sum(1 for call in tool_calls if call.get("acknowledged") is True)
    hallucinated_call_count = sum(
        1 for call in tool_calls
        if AGENTS.get(str(call.get("agent_id") or "")) is None
        or not any(action.id == str(call.get("action_id") or "") for action in AGENTS[str(call.get("agent_id"))].actions)
    )
    known_agent_ids = {str(agent_id).upper() for agent_id in AGENTS.keys()}
    hallucinated_reference_count = hallucinated_call_count + sum(1 for xapp in generated_workflow if str(xapp).upper() not in known_agent_ids)

    # Some intents admit more than one valid chain; the benchmark lists them
    # under accepted_workflows. Set match ignores order.
    accepted = [list(item) for item in (intent.get("accepted_workflows") or [])] or [expected_workflow]
    workflow_match_any = any(generated_workflow == candidate for candidate in accepted)
    workflow_set_match = any(set(generated_workflow) == set(candidate) for candidate in accepted) and bool(generated_workflow)

    planner_task = (execution.get("planner_task") or {}) if isinstance(execution.get("planner_task"), dict) else {}
    providers = {item.get("id"): item for item in _provider_statuses()}
    conflict_fields = conflict_outcome(execution, tool_calls, failure_detected)
    conflict_detected = conflict_detected or conflict_fields["conflict_detected_before_control"]
    rule_match, rule_reasons = score_with_label_rules(generated_workflow, intent)
    retrieval = execution.get("retrieval") or None
    planner_provider = planner_task.get("provider_id")
    planner_model = (providers.get(planner_provider) or {}).get("model") if planner_provider else None

    record = {
        "record_id": uuid.uuid4().hex,
        "intent_id": intent.get("id"),
        "intent": intent.get("intent"),
        "intent_category": intent.get("category"),
        "intent_open_world": bool(intent.get("open_world")),
        "intent_split": str(intent.get("split") or ("open_world" if intent.get("open_world") else "known")),
        "intent_tags": list(intent.get("tags") or []),
        "method": method,
        "repeat_index": repeat_index,
        "duration_s": duration_s,
        "expected_workflow_id": intent.get("expected_workflow_id"),
        "expected_workflow": expected_workflow,
        "generated_workflow_id": execution.get("generated_workflow_id"),
        "generated_workflow": generated_workflow,
        "workflow_match": generated_workflow == expected_workflow,
        "workflow_match_any_accepted": workflow_match_any,
        "workflow_match_rule": rule_match,
        "workflow_match_rule_reasons": rule_reasons,
        "workflow_rule_reasons": rule_reasons,
        "workflow_set_match": workflow_set_match,
        "accepted_workflows": accepted,
        "planner_provider": planner_provider,
        "planner_model": planner_model,
        "planner_cached": bool(execution.get("planner_cached", False)),
        "compat_ok": (execution.get("compat_report") or {}).get("ok") if execution.get("compat_report") else None,
        "compat_report": execution.get("compat_report"),
        "retrieval": retrieval,
        "retrieval_hit": (retrieval or {}).get("expected_retrieved") if retrieval else None,
        "retrieval_hit_unpinned": (retrieval or {}).get("expected_retrieved_unpinned") if retrieval else None,
        "graph_backend": execution.get("graph_backend"),
        "validate_mode": execution.get("validate_mode"),
        "validation_report": execution.get("validation_report"),
        **conflict_fields,
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
        "tool_call_launch_success_count": tool_launch_success,
        "tool_call_success_count": tool_success,
        "policy_valid": policy_valid,
        "policy_notes": policy_notes,
        "hallucinated_api": hallucinated_api,
        "hallucinated_reference_count": hallucinated_reference_count,
        "conflict_label": conflict_label,
        "conflict_detected": conflict_detected,
        "conflict_detection_correct": (conflict_detected == conflict_label) if conflict_label is not None else None,
        "failure_detected": failure_detected,
        "recovery_attempted": recovery_attempted,
        "recovered_from_failure": recovered_from_failure,
        "human_intervention_required": bool(execution.get("manual_override")),
        "method_available": bool(execution.get("method_available", True)),
        "orchestration_latency_ms": round(orchestration_latency_ms, 3),
        "before": before_snapshot["metrics"],
        "after": after_snapshot["metrics"],
        "metrics_available": bool(before_snapshot.get("available")) and bool(after_snapshot.get("available")),
        "metrics_detail": {
            "before": {
                "available": before_snapshot.get("available"),
                "detail": before_snapshot.get("detail"),
                "source": before_snapshot.get("source"),
                "series_summary": before_snapshot.get("series_summary"),
            },
            "after": {
                "available": after_snapshot.get("available"),
                "detail": after_snapshot.get("detail"),
                "source": after_snapshot.get("source"),
                "series_summary": after_snapshot.get("series_summary"),
            },
        },
        "execution_status": execution.get("status"),
        "workflow_status": (workflow_run or {}).get("status"),
        "workflow_run_id": (workflow_run or {}).get("id"),
        "workflow_summary": (workflow_run or {}).get("summary"),
        "workflow_events": list((workflow_run or {}).get("events") or execution.get("workflow_events") or []),
        "selected_actions": list((workflow_run or {}).get("selected_actions") or []),
        "blocked_reason": execution.get("blocked_reason", ""),
        "execution_artifacts": execution_artifacts,
        "conflict_seed": conflict_seed,
        "method_error": method_error,
        "recovery_result": recovery_result,
        "notes": [
            "Current platform does not expose native intent-to-workflow planning; this harness wraps the existing workflows with repeatable planners.",
            "Open-world intents may require agent-card planning and custom workflow chains that do not map to the portal's three predefined workflow templates.",
            "KPM before/after values are proxy metrics from the portal figure payload. SLA violation rate is currently unavailable and recorded as null.",
            "Observation-heavy paths may reuse cached KPM snapshots/results to reduce platform load during evaluation.",
            "No method resets the runtime during a record: a busy application is waited for (bounded, same budget for every method) or re-planned around (AppWeaver Recover). recovered_from_failure = completed after such a wait/re-plan.",
            "Internal recovery (AppWeaver Recover node) is reported in execution_artifacts.internal_recovery_*.",
        ],
    }
    return record


def run_record(method: str, intent: Dict[str, Any], repeat_index: int, duration_s: int, enable_recovery: bool) -> Dict[str, Any]:
    """One (intent, method, repeat). Runtime resets happen only before and after the record.

    `enable_recovery` is kept for CLI compatibility and ignored: the old external recovery
    (reset the runtime, re-run without the seed) pre-empted the seeded workflow and is gone.
    Recovery is now the in-method bounded lease wait (all methods) and AppWeaver's Recover node.
    """
    del enable_recovery
    reset_runtime()
    _RECORD_STATE.update({"active": True, "notes": str(intent.get("notes") or ""), "own_run_ids": set(), "reset_calls": 0, "lease_wait_s": 0.0})
    try:
        before_snapshot = capture_metrics_snapshot()
        conflict_seed = seed_conflict_if_needed(intent, method, duration_s)
        method_error: Optional[str] = None
        started = time.perf_counter()
        try:
            execution = execute_method(method, intent, duration_s)
        except AssertionError:
            raise  # label leakage or a pre-emptive reset: stop the batch loudly
        except Exception as exc:
            execution = {
                "generated_workflow_id": None,
                "generated_workflow": [],
                "tool_calls": [],
                "raw_runs": [],
                "workflow_run": None,
                "status": "failed",
                "blocked_reason": "",
                "manual_override": False,
            }
            method_error = str(exc)
        orchestration_latency_ms = (time.perf_counter() - started) * 1000.0
        acknowledge_tool_calls(list(execution.get("tool_calls") or []), float(EVAL_RUNTIME_CONFIG.get("tool_ack_timeout_s") or 0.0))
        after_snapshot = capture_metrics_snapshot()

        tool_calls = list(execution.get("tool_calls") or [])
        failure_detected = bool(method_error) or detect_failure(execution, tool_calls)
        waited = float(_RECORD_STATE.get("lease_wait_s") or 0.0) > 0.0 or bool(execution.get("waited_for_lease"))
        recovery_attempted = waited or bool(execution.get("replanned_around_resource"))
        recovered_from_failure = recovery_attempted and not failure_detected and str(execution.get("status") or "") == "completed"

        record = build_record(
            intent=intent,
            method=method,
            repeat_index=repeat_index,
            duration_s=duration_s,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            execution=execution,
            orchestration_latency_ms=orchestration_latency_ms,
            recovery_attempted=recovery_attempted,
            recovered_from_failure=recovered_from_failure,
            recovery_result=None,
            conflict_seed=conflict_seed,
            method_error=method_error,
        )
        assert record["preempted_other_workflow"] is False, "a method pre-empted another workflow"
    finally:
        _RECORD_STATE["active"] = False
    reset_runtime()
    return record


def _sha256_file(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def code_provenance() -> Dict[str, Any]:
    """Git commit of the repo plus sha256 of the files this batch actually executed.

    The harness usually runs from the (git-ignored) build tree, so the commit alone does not
    pin the code: the per-file hashes do.
    """
    files = [
        Path(__file__).resolve(),
        ROOT / "backend" / "orchestration" / "discovery.py",
        ROOT / "backend" / "orchestration" / "compat.py",
        ROOT / "backend" / "orchestration" / "validate.py",
        ROOT / "evaluation" / "label_rules.py",
        ROOT / "flexric_agent_portal.py",
    ] + sorted((ROOT / "backend" / "appweaver").rglob("*.py")) + sorted((ROOT / "backend" / "agents").glob("*.py"))
    source_dir = Path.home() / "flexric" / "examples" / "xApp" / "python3"
    dirty = None
    if source_dir.exists():
        try:
            out = subprocess.run(["git", "-C", str(source_dir), "status", "--porcelain", "--", "."], capture_output=True, text=True, timeout=10)
            dirty = bool(out.stdout.strip()) if out.returncode == 0 else None
        except Exception:
            dirty = None
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_source_dirty": dirty,
        "harness_root": str(ROOT),
        "code_sha256": {str(path.relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path): _sha256_file(path) for path in files if path.exists()},
    }


def manifest(methods: List[str], intents: List[Dict[str, Any]], repeats: int, duration_s: int, intents_path: Optional[Path] = None) -> Dict[str, Any]:
    prompt_hashes = prompt_builders_sha256()
    provenance = code_provenance()
    return {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "intents_file": str(intents_path) if intents_path else None,
        "intents_sha256": _sha256_file(intents_path) if intents_path else None,
        "git_commit": provenance.get("git_commit"),
        "code_provenance": provenance,
        "prompt_builders_sha256": prompt_hashes,
        "LLM_SERVER_HARDWARE": os.getenv("LLM_SERVER_HARDWARE", "unrecorded"),
        "max_prompt_chars": EVAL_RUNTIME_CONFIG.get("max_prompt_chars"),
        "lease_wait_s": EVAL_RUNTIME_CONFIG.get("lease_wait_s"),
        "validate_mode": EVAL_RUNTIME_CONFIG.get("validate_mode"),
        "validate_mode_effective": EVAL_RUNTIME_CONFIG.get("validate_mode_effective"),
        "graph_backend": "langgraph",
        "external_recovery": "removed (no runtime reset during a record)",
        "methods": methods,
        "intent_count": len(intents),
        "repeat_count": repeats,
        "duration_s": duration_s,
        "evaluation_runtime_config": copy.deepcopy(EVAL_RUNTIME_CONFIG),
        "method_labels": {method: METHOD_LABELS.get(method, method) for method in methods},
        "planner_inference_settings": llm_sampling_settings(),
        "planner_prompt_sha256": prompt_hashes,
        "hardware": {
            "orchestration_host": platform.node(),
            "orchestration_platform": platform.platform(),
            "orchestration_cpu": platform.processor() or platform.machine(),
            "orchestration_python": platform.python_version(),
            # Set LLM_SERVER_HARDWARE to e.g. "NVIDIA RTX 6000 Ada 48GB x1" on the GPU host.
            "llm_server": os.getenv("LLM_SERVER_HARDWARE", "unrecorded"),
        },
        "registry": {
            "agent_count": len(AGENTS),
            "executable_agent_count": sum(1 for agent in AGENTS.values() if agent.actions),
            "action_count": sum(len(agent.actions) for agent in AGENTS.values()),
            "agent_ids": sorted(AGENTS.keys()),
        },
        "service_health": _service_health(),
        "providers": _provider_statuses(),
        "workflow_templates": WORKFLOW_TEMPLATES,
        "workflow_actions": WORKFLOW_ACTIONS,
        "notes": [
            "This manifest captures the platform state observed by the harness at batch start.",
            "The current environment may not expose live RPC, MCP, or KPM services. Those limits are recorded in the result files rather than hidden.",
            "Metrics snapshots and KPM observation actions can be cached by the harness to reduce platform load and avoid punishing planners for telemetry polling frequency.",
            "Agent-card discovery methods can generate custom workflow chains when an intent does not align with the predefined workflow catalog.",
        ],
    }


def write_artifacts(output_dir: Path, intents: List[Dict[str, Any]], records: List[Dict[str, Any]], batch_manifest: Dict[str, Any]) -> None:
    records_dir = output_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(batch_manifest, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "intents.json").write_text(json.dumps(intents, indent=2), encoding="utf-8")

    jsonl_lines: List[str] = []
    for index, record in enumerate(records, start=1):
        name = f"{index:04d}_{record['method']}_{record['intent_id']}_r{record['repeat_index']}.json"
        (records_dir / name).write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        jsonl_lines.append(json.dumps(record, sort_keys=True))

    (output_dir / "records.jsonl").write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")

    summary = build_summary(records)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "analysis.md").write_text(build_markdown(summary), encoding="utf-8")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FlexRIC workflow evaluation harness.")
    parser.add_argument("--intents", default=str(Path(__file__).resolve().parent / "intents.json"))
    parser.add_argument("--output-root", default=str(Path(__file__).resolve().parent / "runs"))
    parser.add_argument("--methods", nargs="+", default=list(METHODS))
    # Defaults are the headline-run settings: every record pays full planning
    # cost (no planner or observation cache), five repeats, live telemetry.
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--duration-s", type=int, default=45)
    parser.add_argument("--max-intents", type=int, default=0)
    parser.add_argument("--disable-recovery", action="store_true", help="Deprecated no-op: the external reset-and-rerun recovery was removed (it pre-empted the seeded workflow).")
    parser.add_argument("--lease-wait-s", type=float, default=45.0, help="Bounded wait every method gets when a step is refused because the agent is busy (then one retry); seed actions run 30 s. 0 disables waiting.")
    parser.add_argument("--validate-mode", choices=["checks", "dryrun"], default="checks", help="AppWeaver Validate: tier-1 checks only, or checks + dry run of each control step on the E2 emulator twin (backend.orchestration.emu_twin; degrades to checks if unavailable).")
    parser.add_argument("--dryrun-duration-s", type=int, default=5)
    parser.add_argument("--only-intents", default="", help="Comma-separated intent ids to run (applied before --max-intents).")
    parser.add_argument("--metrics-mode", choices=["off", "cached", "live"], default="live")
    parser.add_argument("--metrics-min-interval-s", type=float, default=15.0)
    parser.add_argument("--observation-cache-ttl-s", type=float, default=0.0)
    parser.add_argument("--planner-cache-ttl-s", type=float, default=0.0)
    parser.add_argument("--workflow-poll-timeout-s", type=float, default=2.0)
    parser.add_argument("--workflow-poll-interval-s", type=float, default=0.05)
    parser.add_argument("--tool-ack-timeout-s", type=float, default=10.0, help="How long to wait for launched xApps to show real work in their logs before marking the tool call unacknowledged.")
    parser.add_argument("--retrieval-k", type=int, default=0, help="Agent-card retrieval depth for the planner prompt; 0 = include every executable card (small-registry mode).")
    parser.add_argument("--retrieval-include-deprecated", action="store_true", help="Deprecated: deprecated cards are now visible by default (see --retrieval-hide-deprecated).")
    parser.add_argument("--retrieval-hide-deprecated", action="store_true", help="Filter deprecated cards out before the prompt (old behaviour; the deprecated-card trap is then untested).")
    parser.add_argument("--no-retrieval-pin-xapps", action="store_true", help="Ablation: do not pin the executable FlexRIC xApps into the retrieval result (k then bounds every card).")
    parser.add_argument("--label", default="", help="Optional suffix for the run directory name.")
    parser.add_argument("--repeat-start", type=int, default=1, help="First repeat index (continue a batch whose later repeats were invalid).")
    parser.add_argument("--maintenance-cmd", default="", help="Shell command run between records every --maintenance-every records (e.g. scripts/restart_agent_portal_stack.sh); outside every timed path, logged in the manifest.")
    parser.add_argument("--maintenance-every", type=int, default=0)
    parser.add_argument("--health-cmd", default="", help="Shell command run after every record (e.g. scripts/probe_e42.sh); on failure the record is discarded, --maintenance-cmd runs and the record is re-run.")
    parser.add_argument("--health-retries", type=int, default=2)
    parser.add_argument("--max-prompt-chars", type=int, default=0, help="Raise the portal's task-prompt cap (a UI input guard, 8000 chars) for in-process planner calls; 0 keeps the portal value. Needed when every directory card is in the prompt (--retrieval-k 0 with FLEXRIC_RAPP_DIRECTORY=1).")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    EVAL_RUNTIME_CONFIG.update(
        {
            "metrics_mode": str(args.metrics_mode),
            "metrics_min_interval_s": float(args.metrics_min_interval_s),
            "observation_cache_ttl_s": float(args.observation_cache_ttl_s),
            "planner_cache_ttl_s": float(args.planner_cache_ttl_s),
            "workflow_poll_timeout_s": float(args.workflow_poll_timeout_s),
            "workflow_poll_interval_s": float(args.workflow_poll_interval_s),
            "tool_ack_timeout_s": float(args.tool_ack_timeout_s),
            "retrieval_k": int(args.retrieval_k),
            "retrieval_include_deprecated": not bool(args.retrieval_hide_deprecated),
            "retrieval_pin_xapps": not bool(args.no_retrieval_pin_xapps),
            "lease_wait_s": float(args.lease_wait_s),
            "validate_mode": str(args.validate_mode),
            "dryrun_duration_s": int(args.dryrun_duration_s),
            "max_prompt_chars": int(args.max_prompt_chars) or flexric_agent_portal.MAX_PROMPT_CHARS,
            "rapp_directory_enabled": os.getenv("FLEXRIC_RAPP_DIRECTORY", "").strip().lower() in {"1", "true", "yes", "on"},
        }
    )
    if args.max_prompt_chars > 0:
        flexric_agent_portal.MAX_PROMPT_CHARS = int(args.max_prompt_chars)
    intent_path = Path(args.intents).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    methods = [method for method in args.methods if method in METHODS]
    if not methods:
        raise SystemExit("No supported methods were selected.")

    if args.validate_mode == "dryrun":
        dryrun_fn, dryrun_reason = resolve_dryrun()
        EVAL_RUNTIME_CONFIG["validate_mode_effective"] = "dryrun" if dryrun_fn is not None else "checks"
        EVAL_RUNTIME_CONFIG["validate_mode_degraded_reason"] = dryrun_reason
    else:
        EVAL_RUNTIME_CONFIG["validate_mode_effective"] = "checks"
    intents = load_intents(intent_path)
    if args.only_intents.strip():
        wanted = [item.strip() for item in args.only_intents.split(",") if item.strip()]
        by_id = {str(intent.get("id")): intent for intent in intents}
        missing = [item for item in wanted if item not in by_id]
        if missing:
            raise SystemExit(f"Unknown intent ids: {missing}")
        intents = [by_id[item] for item in wanted]
    if args.max_intents > 0:
        intents = intents[: args.max_intents]

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S_%fZ")
    output_dir = output_root / (f"{timestamp}_{args.label}" if args.label else timestamp)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_manifest = manifest(methods, intents, args.repeat, args.duration_s, intents_path=intent_path)
    batch_manifest["only_intents"] = args.only_intents or None
    (output_dir / "manifest.json").write_text(json.dumps(batch_manifest, indent=2, sort_keys=True), encoding="utf-8")
    # Records are appended as they finish so a long batch can be watched and survives a crash.
    partial_path = output_dir / "records.partial.jsonl"
    first_repeat = max(1, int(args.repeat_start))
    total = max(1, int(args.repeat)) * len(intents) * len(methods)
    batch_manifest["repeat_start"] = first_repeat
    batch_manifest["maintenance"] = {"cmd": args.maintenance_cmd, "every": args.maintenance_every, "runs": [],
                                     "health_cmd": args.health_cmd, "health_retries": args.health_retries,
                                     "health_failures": []}
    records: List[Dict[str, Any]] = []
    for repeat_index in range(first_repeat, first_repeat + max(1, int(args.repeat))):
        for intent in intents:
            for method in methods:
                for attempt in range(1 + max(0, int(args.health_retries))):
                    record = run_record(
                        method=method,
                        intent=intent,
                        repeat_index=repeat_index,
                        duration_s=int(args.duration_s),
                        enable_recovery=not args.disable_recovery,
                    )
                    # A record run while the RIC was wedged says nothing about the method: discard it
                    # (kept in records.discarded.jsonl), restart the stack and run the record again.
                    if not args.health_cmd or subprocess.call(args.health_cmd, shell=True) == 0:
                        break
                    with (output_dir / "records.discarded.jsonl").open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, sort_keys=True) + "\n")
                    rc = subprocess.call(args.maintenance_cmd, shell=True) if args.maintenance_cmd else None
                    batch_manifest["maintenance"]["health_failures"].append(
                        {"after_record": len(records), "intent_id": intent.get("id"), "method": method,
                         "repeat_index": repeat_index, "attempt": attempt + 1, "restart_returncode": rc})
                    print(f"health check failed after r{repeat_index} {method} {intent.get('id')}: restarted rc={rc}, re-running", flush=True)
                else:
                    record["infra_unhealthy"] = True  # every attempt ended on a wedged RIC; kept and flagged
                record["infra_attempts"] = attempt + 1
                records.append(record)
                with partial_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
                print(f"[{len(records)}/{total}] r{repeat_index} {method} {intent.get('id')}", flush=True)
                if args.maintenance_cmd and args.maintenance_every > 0 and len(records) % args.maintenance_every == 0 and len(records) < total:
                    started_m = time.time()
                    rc = subprocess.call(args.maintenance_cmd, shell=True)
                    batch_manifest["maintenance"]["runs"].append({"after_record": len(records), "returncode": rc, "duration_s": round(time.time() - started_m, 1)})
                    print(f"maintenance after {len(records)} records rc={rc}", flush=True)

    write_artifacts(output_dir, intents, records, batch_manifest)
    partial_path.unlink(missing_ok=True)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
