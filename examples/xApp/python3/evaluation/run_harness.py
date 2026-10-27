#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import re
import shutil
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.analyze_results import build_markdown, build_summary
from backend.orchestration.compat import check_chain  # type: ignore
from backend.orchestration.discovery import discover  # type: ignore
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
TOOL_ACK_MARKERS = {
    "kpm": ["RRU.", "DRB.", "\"meas\"", "indication"],
    "slice": ["Slice monitor subscribed", "Applied STATIC", "Applied NVS", "Applied EDF", "Monitor-only mode", "SLICE ind tstamp=",
              "Successfully received CONTROL-ACK"],
    # The TC suite prints ~30 setup lines before "Applied"; the E2 CONTROL-ACK from the RAN is the
    # actual control acknowledgement and arrives first (the portal only exposes a 20-line tail).
    "tc": ["Applied TC profile", "Successfully received CONTROL-ACK"],
    "rc": ["KPM/RC suite running", "RC profile selected", "RC indication received"],
}
TOOL_ACK_NEGATIVE_MARKERS = ["No KPM bus records were received", "Traceback", "Error", "refused"]

OBSERVATION_AGENTS = {"kpm"}
VALIDATION_AGENTS = {"rc"}
CONTROL_AGENTS = {"slice", "tc", "mac"}
WORKFLOW_TRANSITIONAL_STATUSES = {"pending", "starting", "launching", "admitted", "running"}

EVAL_RUNTIME_CONFIG: Dict[str, Any] = {
    "metrics_mode": "cached",
    "metrics_min_interval_s": 15.0,
    "observation_cache_ttl_s": 20.0,
    "planner_cache_ttl_s": 600.0,
    "workflow_poll_timeout_s": 0.6,
    "tool_ack_timeout_s": 10.0,
    "workflow_poll_interval_s": 0.05,
}

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
    return [(str(agent_id), str(action_id)) for agent_id, action_id in WORKFLOW_ACTIONS.get(workflow_id, {}).items()]


def route_intent(intent: Dict[str, Any]) -> str:
    category = str(intent.get("category") or "").strip().lower()
    if category == "slice":
        return "slice-assurance"
    if category == "transport":
        return "transport-qos"
    if category == "latency":
        return "observe-diagnose-optimize"

    text = f"{intent.get('intent', '')} {intent.get('category', '')}".lower()
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


def discover_cards(intent: Optional[Dict[str, Any]]) -> Tuple[List[Any], Dict[str, Any]]:
    """Discover agent cards for an intent.

    With retrieval_k == 0 (small registry) every executable card is returned.
    Otherwise BM25 over the card text returns the top-k, and the retrieval
    record (ranked ids, whether the ground-truth agents were retrieved) is
    attached to the evaluation record so top-k recall can be reported.
    """
    k = int(EVAL_RUNTIME_CONFIG.get("retrieval_k") or 0)
    query = _intent_text(intent) if intent else ""
    ranked = discover(AGENTS, query, k=k, executable_only=True, include_deprecated=bool(EVAL_RUNTIME_CONFIG.get("retrieval_include_deprecated")))
    cards = [card for card, _ in ranked]
    expected = [str(item).lower() for item in list((intent or {}).get("expected_workflow") or [])]
    retrieved_ids = [card.id for card in cards]
    return cards, {
        "k": k,
        "registry_executable_count": sum(1 for card in AGENTS.values() if card.actions),
        "retrieved": retrieved_ids,
        "scores": {card.id: round(score, 3) for card, score in ranked[:20]},
        "expected_agents": expected,
        "expected_retrieved": all(agent in retrieved_ids for agent in expected) if expected else None,
    }


def executable_agent_cards(intent: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    selected, _ = discover_cards(intent) if intent is not None else (list(AGENTS.values()), {})
    for agent in selected:
        agent_id = agent.id
        actions = []
        for action in agent.actions:
            actions.append(
                {
                    "id": action.id,
                    "label": action.label,
                    "description": action.description,
                    "kind": action.kind,
                }
            )
        if not actions:
            continue
        cards.append(
            {
                "agent_id": agent_id,
                "label": agent.name,
                "app_type": getattr(agent, "app_type", "xapp"),
                "description": getattr(agent, "description", ""),
                "capabilities": list(getattr(agent, "capabilities", [])),
                "requires": list(getattr(agent, "requires", [])),
                "control_scopes": [{"target": s.target, "mode": s.mode, "resource": s.resource} for s in getattr(agent, "control_scopes", [])],
                "status": agent.status,
                "actions": actions,
            }
        )
    return cards


def _intent_text(intent: Dict[str, Any]) -> str:
    parts = [
        str(intent.get("intent") or ""),
        str(intent.get("category") or ""),
        str(intent.get("notes") or ""),
    ]
    return " ".join(parts).strip().lower()


def _intent_has_any(intent: Dict[str, Any], tokens: List[str]) -> bool:
    text = _intent_text(intent)
    return any(token in text for token in tokens)


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
        return "rc-scaffold"
    return None


def deterministic_discovery_chain(intent: Dict[str, Any]) -> List[str]:
    text = _intent_text(intent)
    if any(token in text for token in ["xr", "urllc", "premium qos", "premium traffic", "emergency", "stadium congestion", "composite"]):
        return ["KPM", "SLICE", "TC", "RC"]
    if any(token in text for token in ["slice", "fairness", "isolation", "enterprise", "admission", "reserved prb", "oversubscription", "rebalance", "drift"]):
        if any(token in text for token in ["latency", "slowdown", "queue", "throughput", "congestion"]):
            return ["KPM", "SLICE", "TC", "RC"]
        if any(token in text for token in ["audit", "validate", "verify", "monitor", "check"]):
            return ["SLICE", "KPM", "RC"]
        return ["KPM", "SLICE", "RC"]
    if any(token in text for token in ["transport", "backhaul", "bufferbloat", "qos", "tunnel", "bearer", "queue", "codel", "ecn", "shaping", "jitter"]):
        if any(token in text for token in ["validate", "verify", "sanity check", "rollback"]):
            return ["TC", "RC"]
        return ["KPM", "TC", "RC"]
    if any(token in text for token in ["mobility", "handover", "anomaly", "pdcp", "gtp", "rlc", "diagnose", "investigate", "triage", "root cause", "risk screening"]):
        if any(token in text for token in ["protect", "mitigate", "recover", "optimize", "stabilize"]):
            return ["KPM", "TC", "RC"]
        return ["KPM", "RC"]
    if any(token in text for token in ["capacity", "prb", "radio", "throughput", "latency"]):
        return ["KPM", "SLICE", "RC"] if "slice" in text else ["KPM", "TC", "RC"]
    return ["KPM", "TC", "RC"]


def action_pairs_for_chain(chain: List[str], intent: Dict[str, Any], requested_steps: Optional[List[Dict[str, Any]]] = None) -> List[Tuple[str, str]]:
    requested_by_agent: Dict[str, str] = {}
    for step in list(requested_steps or []):
        agent_id = str(step.get("agent_id") or "").strip().lower()
        action_id = str(step.get("action_id") or "").strip()
        if agent_id and action_id:
            requested_by_agent[agent_id] = action_id

    pairs: List[Tuple[str, str]] = []
    for name in chain:
        agent_id = str(name or "").strip().lower()
        agent = AGENTS.get(agent_id)
        if agent is None or not agent.actions:
            continue
        action_id = requested_by_agent.get(agent_id) or default_action_for_agent(agent_id, intent)
        if action_id and any(action.id == action_id for action in agent.actions):
            pairs.append((agent_id, action_id))
            continue
        pairs.append((agent_id, agent.actions[0].id))
    return pairs


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
    return api_runtime_reset(RuntimeResetRequest(clear_saved_workflows=False))


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


def _log_acknowledges(agent_id: str, tail: List[str]) -> Optional[bool]:
    text = "\n".join(str(line) for line in tail)
    markers = TOOL_ACK_MARKERS.get(agent_id) or (["rApp ack:"] if agent_id.startswith("rapp.") else [])
    if any(marker in text for marker in markers):
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
            verdict = _log_acknowledges(str(call.get("agent_id")), list(run.get("tail") or []))
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
    seed_workflow = intent.get("conflict_seed")
    if not seed_workflow:
        return {"applied": False}

    if method.startswith("langgraph"):
        payload = api_workflow_run(
            str(seed_workflow),
            WorkflowRequest(goal=f"Conflict seed for {intent.get('id')}", mode="enforced", duration_s=duration_s),
        )
        run = dict(payload.get("run") or {})
        return {
            "applied": True,
            "type": "workflow",
            "workflow_id": seed_workflow,
            "run_id": run.get("id"),
            "status": run.get("status"),
        }

    action_pairs = actions_for_workflow(str(seed_workflow))
    if not action_pairs:
        return {"applied": False}
    tool_call, run_payload, error = invoke_action(*action_pairs[0])
    return {
        "applied": True,
        "type": "action",
        "workflow_id": seed_workflow,
        "run_id": (run_payload or {}).get("id"),
        "status": tool_call.get("status"),
        "error": error,
    }


def detect_conflict(execution: Dict[str, Any], tool_calls: List[Dict[str, Any]]) -> bool:
    if str(execution.get("status") or "") == "queued":
        return True
    if execution.get("blocked_reason"):
        return True
    return any(call.get("status") in {"conflict", "queued"} for call in tool_calls)


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
        f"Category: {intent.get('category')}\n"
        f"Notes: {intent.get('notes', '')}\n"
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
        f"Category: {intent.get('category')}\n"
        f"Notes: {intent.get('notes', '')}\n"
    )


def plan_blind(intent: Dict[str, Any]) -> Dict[str, Any]:
    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=llm_blind_prompt(intent), provider="auto"))
    task = dict(task_payload.get("task") or {})
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

    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=llm_prompt(intent), provider="auto"))
    task = dict(task_payload.get("task") or {})
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
    return (
        "You are planning an adaptive LangGraph-style workflow from executable agent cards for the FlexRIC portal.\n"
        "Return only JSON with keys generated_workflow, steps, and rationale.\n"
        "Rules:\n"
        "- generated_workflow must be a list of executable agent ids in execution order.\n"
        "- steps must be a list of objects with agent_id and optional action_id.\n"
        "- Use only executable agents and actions from the provided agent cards.\n"
        "- Prefer 1 to 4 steps.\n"
        "- Use KPM first when the task requires observation, diagnosis, anomaly detection, or root-cause triage.\n"
        "- Use RC last when the task applies or validates a control decision.\n"
        "- You may produce a novel workflow chain instead of forcing a predefined template.\n"
        f"Intent: {intent.get('intent')}\n"
        f"Category: {intent.get('category')}\n"
        f"Notes: {intent.get('notes', '')}\n"
        f"Executable agent cards: {json.dumps(executable_agent_cards(intent))}\n"
    )


def validate_or_repair_agentcard_plan(intent: Dict[str, Any], generated_workflow: List[str], steps: List[Dict[str, str]]) -> Dict[str, Any]:
    requested_chain = [str(item).strip().upper() for item in generated_workflow if str(item).strip()]
    if not requested_chain and steps:
        requested_chain = [str(step.get("agent_id") or "").strip().upper() for step in steps if str(step.get("agent_id") or "").strip()]

    normalized_chain: List[str] = []
    valid_agent_ids = {agent_id.upper() for agent_id, agent in AGENTS.items() if agent.actions}
    for agent_name in requested_chain:
        if agent_name not in valid_agent_ids:
            continue
        if normalized_chain and normalized_chain[-1] == agent_name:
            continue
        normalized_chain.append(agent_name)

    # Repair may only consult the registry. Earlier revisions substituted the
    # intent's ground-truth chain for closed-world intents here, which leaked
    # the benchmark label into the method under test; that path is gone.
    if not normalized_chain:
        normalized_chain = deterministic_discovery_chain(intent)
        planner_repaired = True
        repair_reason = "Applied deterministic agent-card fallback because the adaptive plan was empty or invalid."
    else:
        planner_repaired = False
        repair_reason = ""

    resolved_pairs = action_pairs_for_chain(normalized_chain, intent, requested_steps=steps)
    resolved_chain = [agent_id.upper() for agent_id, _ in resolved_pairs]
    workflow_id = workflow_id_from_chain(resolved_chain) or custom_workflow_id_from_chain(resolved_chain)
    resolved_steps = [{"agent_id": agent_id, "action_id": action_id} for agent_id, action_id in resolved_pairs]
    return {
        "workflow_id": workflow_id,
        "generated_workflow": resolved_chain,
        "resolved_steps": resolved_steps,
        "planner_repaired": planner_repaired,
        "repair_reason": repair_reason,
    }


def plan_with_agent_cards(intent: Dict[str, Any], repair: bool = True) -> Dict[str, Any]:
    _, retrieval = discover_cards(intent)
    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=agentcard_prompt(intent), provider="auto"))
    task = dict(task_payload.get("task") or {})
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        return {
            "ok": False,
            "retrieval": retrieval,
            "planner_task": task,
            "planner_error": response_text or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
            "workflow_id": None,
            "generated_workflow": [],
            "steps": [],
            "rationale": "",
        }

    try:
        plan = parse_llm_plan(response_text)
    except Exception as exc:
        plan = {"generated_workflow": [], "steps": [], "rationale": f"unparseable: {exc}"}
    generated_workflow = normalize_generated_workflow(plan.get("generated_workflow"))
    steps = normalize_discovery_steps(plan.get("steps"))
    if not repair:
        # Execute the raw plan: unknown agents stay in generated_workflow so
        # they are counted as hallucinations, and only real ones are launched.
        raw_pairs = action_pairs_for_chain(generated_workflow, intent, requested_steps=steps)
        return {
            "ok": True,
            "planner_task": task,
            "planner_plan": plan,
            "planner_error": "",
            "planner_unavailable": False,
            "method_available": True,
            "workflow_id": workflow_id_from_chain(generated_workflow) or custom_workflow_id_from_chain(generated_workflow),
            "generated_workflow": generated_workflow,
            "steps": [{"agent_id": agent_id, "action_id": action_id} for agent_id, action_id in raw_pairs],
            "rationale": str(plan.get("rationale") or ""),
            "planner_repaired": False,
            "repair_reason": "",
            "retrieval": retrieval,
            "compat_report": check_chain(AGENTS, generated_workflow).to_dict(),
        }
    repaired = validate_or_repair_agentcard_plan(intent, generated_workflow, steps)
    # Compose-time compatibility check over the Agent Cards (dependency,
    # interface, control scope, timescale). Steps that fail with an error are
    # dropped and the report travels with the record.
    compat = check_chain(AGENTS, list(repaired.get("generated_workflow") or []))
    if not compat.ok:
        bad_indices = {f.step_index for f in compat.findings if f.severity == "error"}
        kept_chain = [name for index, name in enumerate(repaired["generated_workflow"]) if index not in bad_indices]
        kept_steps = [step for index, step in enumerate(repaired.get("resolved_steps") or []) if index not in bad_indices]
        repaired = {
            **repaired,
            "generated_workflow": kept_chain,
            "resolved_steps": kept_steps,
            "workflow_id": workflow_id_from_chain(kept_chain) or custom_workflow_id_from_chain(kept_chain),
            "planner_repaired": True,
            "repair_reason": (repaired.get("repair_reason") or "") + " Compatibility check removed incompatible steps.",
        }
    return {
        "retrieval": retrieval,
        "compat_report": compat.to_dict(),
        "ok": True,
        "planner_task": task,
        "planner_plan": plan,
        "planner_error": "",
        "planner_unavailable": False,
        "method_available": True,
        "workflow_id": repaired.get("workflow_id"),
        "generated_workflow": repaired.get("generated_workflow"),
        "steps": repaired.get("resolved_steps"),
        "rationale": str(plan.get("rationale") or ""),
        "planner_repaired": repaired.get("planner_repaired", False),
        "repair_reason": repaired.get("repair_reason", ""),
    }


def agentcard_recovery_prompt(intent: Dict[str, Any], execution: Dict[str, Any]) -> str:
    failure_summary = {
        "status": execution.get("status"),
        "blocked_reason": execution.get("blocked_reason", ""),
        "generated_workflow_id": execution.get("generated_workflow_id"),
        "generated_workflow": execution.get("generated_workflow"),
        "selected_steps": execution.get("selected_steps"),
        "tool_calls": [
            {
                "xapp": call.get("xapp"),
                "status": call.get("status"),
                "detail": call.get("detail", ""),
            }
            for call in list(execution.get("tool_calls") or [])
        ],
    }
    return (
        "You are repairing an adaptive LangGraph-style agent-card workflow for the FlexRIC portal.\n"
        "Return only JSON with keys generated_workflow, steps, reset_runtime, and rationale.\n"
        "Rules:\n"
        "- Use only executable agents and actions from the provided agent cards.\n"
        "- generated_workflow must match the step order.\n"
        "- steps must be a list of objects with agent_id and optional action_id.\n"
        "- reset_runtime should be true when a busy runtime or conflict should be cleared before retry.\n"
        f"Intent: {intent.get('intent')}\n"
        f"Category: {intent.get('category')}\n"
        f"Failure summary: {json.dumps(failure_summary)}\n"
        f"Executable agent cards: {json.dumps(executable_agent_cards())}\n"
    )


def plan_agentcard_recovery_with_llm(intent: Dict[str, Any], execution: Dict[str, Any]) -> Dict[str, Any]:
    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=agentcard_recovery_prompt(intent, execution), provider="auto"))
    task = dict(task_payload.get("task") or {})
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        repaired = validate_or_repair_agentcard_plan(
            intent,
            list(execution.get("generated_workflow") or []),
            list(execution.get("selected_steps") or []),
        )
        return {
            "workflow_id": repaired.get("workflow_id"),
            "generated_workflow": repaired.get("generated_workflow"),
            "steps": repaired.get("resolved_steps"),
            "reset_runtime": True,
            "rationale": "Used deterministic agent-card recovery fallback because the LLM recovery planner was unavailable.",
            "planner_repaired": True,
            "repair_reason": "Deterministic fallback recovery plan.",
            "planner_task": task,
            "planner_error": response_text or "Provider task failed.",
            "planner_unavailable": planner_unavailable,
            "method_available": not planner_unavailable,
        }

    plan = parse_llm_plan(response_text)
    repaired = validate_or_repair_agentcard_plan(
        intent,
        normalize_generated_workflow(plan.get("generated_workflow")),
        normalize_discovery_steps(plan.get("steps")),
    )
    return {
        "workflow_id": repaired.get("workflow_id"),
        "generated_workflow": repaired.get("generated_workflow"),
        "steps": repaired.get("resolved_steps"),
        "reset_runtime": bool(plan.get("reset_runtime")),
        "rationale": str(plan.get("rationale") or ""),
        "planner_repaired": bool(repaired.get("planner_repaired")),
        "repair_reason": str(repaired.get("repair_reason") or ""),
        "planner_task": task,
        "planner_plan": plan,
        "planner_error": "",
        "planner_unavailable": False,
        "method_available": True,
    }


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
        "Return only JSON with keys workflow_id, generated_workflow, mode, approve, reset_runtime, and rationale.\n"
        "Rules:\n"
        "- workflow_id must be one of the provided workflow_id values.\n"
        "- generated_workflow must exactly match that workflow's action_chain.\n"
        "- mode must be either 'enforced' or 'advisory'.\n"
        "- approve must be true only when advisory mode should be manually approved immediately.\n"
        "- reset_runtime should be true when the safest repair requires clearing the current conflicting runtime state before retry.\n"
        "- Prefer the safest valid recovery that preserves the intent.\n"
        f"Intent: {intent.get('intent')}\n"
        f"Category: {intent.get('category')}\n"
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

    task_payload = api_run_task("orchestrator", AgentTaskRequest(prompt=llm_recovery_prompt(intent, execution), provider="auto"))
    task = dict(task_payload.get("task") or {})
    response_text = str(task.get("response") or task.get("error") or "")
    if task.get("status") != "completed":
        planner_unavailable = _is_provider_unavailable(response_text)
        fallback_mode = "advisory" if (detect_conflict(execution, list(execution.get("tool_calls") or [])) or detect_failure(execution, list(execution.get("tool_calls") or []))) else "enforced"
        fallback = {
            "workflow_id": execution.get("generated_workflow_id") or route_intent(intent),
            "generated_workflow": list(execution.get("generated_workflow") or normalize_action_chain(str(execution.get("generated_workflow_id") or route_intent(intent)))),
            "mode": fallback_mode,
            "approve": fallback_mode == "advisory",
            "reset_runtime": True,
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
        "reset_runtime": bool(plan.get("reset_runtime")),
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
    workflow_id = route_intent(intent)
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []
    for agent_id, action_id in actions_for_workflow(workflow_id):
        tool_call, run_payload, _ = invoke_action(agent_id, action_id)
        tool_calls.append(tool_call)
        if run_payload is not None:
            raw_runs.append(run_payload)
    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": normalize_action_chain(workflow_id),
        "tool_calls": tool_calls,
        "raw_runs": raw_runs,
        "status": "completed_with_issues" if any(call["status"] == "failed" for call in tool_calls) else "completed",
        "blocked_reason": "",
        "manual_override": False,
    }


def execute_single_xapp(intent: Dict[str, Any], duration_s: int) -> Dict[str, Any]:
    workflow_id = route_intent(intent)
    action_pairs = actions_for_workflow(workflow_id)
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []
    generated_workflow: List[str] = []
    if action_pairs:
        agent_id, action_id = action_pairs[0]
        tool_call, run_payload, _ = invoke_action(agent_id, action_id)
        tool_calls.append(tool_call)
        generated_workflow = [agent_id.upper()]
        if run_payload is not None:
            raw_runs.append(run_payload)
    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": generated_workflow,
        "tool_calls": tool_calls,
        "raw_runs": raw_runs,
        "status": "completed_with_issues" if any(call["status"] == "failed" for call in tool_calls) else "completed",
        "blocked_reason": "",
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

    recovery_reset_applied = bool(recovery_plan.get("reset_runtime")) or initial_conflict or initial_failure
    if recovery_reset_applied:
        reset_runtime()

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


def execute_agentcard_sequence(intent: Dict[str, Any], workflow_id: str, generated_workflow: List[str], steps: List[Dict[str, str]], duration_s: int) -> Dict[str, Any]:
    del duration_s
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []
    blocked_reason = ""
    action_pairs = action_pairs_for_chain(generated_workflow, intent, requested_steps=steps)
    selected_steps = [{"agent_id": agent_id, "action_id": action_id} for agent_id, action_id in action_pairs]
    for agent_id, action_id in action_pairs:
        tool_call, run_payload, error = invoke_action(agent_id, action_id)
        tool_calls.append(tool_call)
        if run_payload is not None:
            raw_runs.append(run_payload)
        if error or tool_call.get("status") in {"failed", "conflict", "queued"}:
            blocked_reason = str(tool_call.get("detail") or error or "")
            break

    if any(call.get("status") in {"conflict", "queued"} for call in tool_calls):
        status = "queued"
    elif any(call.get("status") == "failed" for call in tool_calls):
        status = "completed_with_issues"
    else:
        status = "completed"

    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": generated_workflow,
        "tool_calls": tool_calls,
        "raw_runs": raw_runs,
        "status": status,
        "blocked_reason": blocked_reason,
        "manual_override": False,
        "method_available": True,
        "selected_steps": selected_steps,
    }


def execute_langgraph_agentcard(intent: Dict[str, Any], duration_s: int, repair: bool = True, recover: bool = True) -> Dict[str, Any]:
    planner = plan_with_agent_cards(intent, repair=repair)
    if not planner.get("ok"):
        return {
            "generated_workflow_id": None,
            "generated_workflow": [],
            "tool_calls": [],
            "raw_runs": [],
            "workflow_run": None,
            "status": "unavailable" if planner.get("planner_unavailable") else "failed",
            "blocked_reason": "",
            "manual_override": False,
            "method_available": bool(planner.get("method_available", True)),
            "planner_task": planner.get("planner_task"),
            "planner_error": planner.get("planner_error", ""),
            "planner_unavailable": planner.get("planner_unavailable", False),
        }

    initial = execute_agentcard_sequence(
        intent=intent,
        workflow_id=str(planner.get("workflow_id") or custom_workflow_id_from_chain(list(planner.get("generated_workflow") or []))),
        generated_workflow=list(planner.get("generated_workflow") or []),
        steps=list(planner.get("steps") or []),
        duration_s=duration_s,
    )
    initial.update(
        {
            "planner_task": planner.get("planner_task"),
            "planner_plan": planner.get("planner_plan"),
            "planner_repaired": planner.get("planner_repaired", False),
            "planner_repair_reason": planner.get("repair_reason", ""),
            "selected_steps": list(planner.get("steps") or []),
            "compat_report": planner.get("compat_report"),
            "retrieval": planner.get("retrieval"),
        }
    )

    tool_calls = list(initial.get("tool_calls") or [])
    initial_conflict = detect_conflict(initial, tool_calls)
    initial_failure = detect_failure(initial, tool_calls)
    if not recover or not (initial_conflict or initial_failure):
        initial["internal_recovery_attempted"] = False
        initial["internal_recovery_succeeded"] = False
        return initial

    recovery_plan = plan_agentcard_recovery_with_llm(intent, initial)
    if recovery_plan.get("method_available") is False:
        initial["internal_recovery_attempted"] = True
        initial["internal_recovery_succeeded"] = False
        initial["recovery_planner_task"] = recovery_plan.get("planner_task")
        initial["recovery_planner_error"] = recovery_plan.get("planner_error", "")
        return initial

    recovery_reset_applied = bool(recovery_plan.get("reset_runtime")) or initial_conflict or initial_failure
    if recovery_reset_applied:
        reset_runtime()

    recovery_execution = execute_agentcard_sequence(
        intent=intent,
        workflow_id=str(recovery_plan.get("workflow_id") or custom_workflow_id_from_chain(list(recovery_plan.get("generated_workflow") or []))),
        generated_workflow=list(recovery_plan.get("generated_workflow") or []),
        steps=list(recovery_plan.get("steps") or []),
        duration_s=duration_s,
    )
    recovery_tool_calls = list(recovery_execution.get("tool_calls") or [])
    recovery_success = not detect_conflict(recovery_execution, recovery_tool_calls) and not detect_failure(recovery_execution, recovery_tool_calls)

    initial_snapshot = copy.deepcopy(initial)
    recovery_snapshot = copy.deepcopy(recovery_execution)
    final_execution = copy.deepcopy(recovery_execution if recovery_success else initial)
    final_execution.update(
        {
            "method_available": True,
            "planner_task": initial.get("planner_task"),
            "planner_plan": initial.get("planner_plan"),
            "planner_repaired": initial.get("planner_repaired", False),
            "planner_repair_reason": initial.get("planner_repair_reason", ""),
            "internal_recovery_attempted": True,
            "internal_recovery_succeeded": recovery_success,
            "initial_execution": initial_snapshot,
            "recovery_planner_task": recovery_plan.get("planner_task"),
            "recovery_planner_plan": recovery_plan.get("planner_plan"),
            "recovery_planner_repaired": recovery_plan.get("planner_repaired", False),
            "recovery_planner_reason": recovery_plan.get("repair_reason", ""),
            "recovery_reset_runtime": recovery_reset_applied,
            "recovery_execution": recovery_snapshot,
        }
    )
    return final_execution


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
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []

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

    for agent_id, action_id in action_pairs:
        tool_call, run_payload, _ = invoke_action(agent_id, action_id)
        tool_calls.append(tool_call)
        if run_payload is not None:
            raw_runs.append(run_payload)

    return {
        "generated_workflow_id": workflow_id,
        "generated_workflow": generated_workflow,
        "tool_calls": tool_calls,
        "raw_runs": raw_runs,
        "workflow_run": None,
        "status": "completed_with_issues" if any(call["status"] == "failed" for call in tool_calls) else "completed",
        "blocked_reason": "",
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
    tool_calls: List[Dict[str, Any]] = []
    raw_runs: List[Dict[str, Any]] = []
    for name in generated_workflow:
        agent_id = known_by_label.get(name)
        if not agent_id or not AGENTS[agent_id].actions:
            # Unknown application: nothing to launch, policy_validation records
            # the hallucinated reference from generated_workflow.
            continue
        action_id = default_action_for_agent(agent_id, intent) or AGENTS[agent_id].actions[0].id
        tool_call, run_payload, _ = invoke_action(agent_id, action_id)
        tool_calls.append(tool_call)
        if run_payload is not None:
            raw_runs.append(run_payload)
    return {
        "generated_workflow_id": workflow_id_from_chain(generated_workflow) or custom_workflow_id_from_chain(generated_workflow),
        "generated_workflow": generated_workflow,
        "tool_calls": tool_calls,
        "raw_runs": raw_runs,
        "workflow_run": None,
        "status": "completed_with_issues" if any(call["status"] == "failed" for call in tool_calls) else "completed",
        "blocked_reason": "",
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
    conflict_detected = detect_conflict(execution, tool_calls)
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
        "workflow_set_match": workflow_set_match,
        "accepted_workflows": accepted,
        "planner_provider": planner_provider,
        "planner_model": planner_model,
        "planner_cached": bool(execution.get("planner_cached", False)),
        "compat_ok": (execution.get("compat_report") or {}).get("ok") if execution.get("compat_report") else None,
        "compat_report": execution.get("compat_report"),
        "retrieval": execution.get("retrieval"),
        "retrieval_hit": (execution.get("retrieval") or {}).get("expected_retrieved") if execution.get("retrieval") else None,
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
        "workflow_events": list((workflow_run or {}).get("events") or []),
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
            "External recovery is defined as a clean rerun of the same method after a runtime reset, without the synthetic conflict seed used to create the stress case.",
            "Internal recovery is counted separately when a method repairs its own plan before the record is finalized.",
        ],
    }
    return record


def run_record(method: str, intent: Dict[str, Any], repeat_index: int, duration_s: int, enable_recovery: bool) -> Dict[str, Any]:
    reset_runtime()
    before_snapshot = capture_metrics_snapshot()
    conflict_seed = seed_conflict_if_needed(intent, method, duration_s)
    method_error: Optional[str] = None
    recovery_result: Optional[Dict[str, Any]] = None
    started = time.perf_counter()
    try:
        execution = execute_method(method, intent, duration_s)
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

    conflict_detected = detect_conflict(execution, list(execution.get("tool_calls") or []))
    failure_detected = bool(method_error) or detect_failure(execution, list(execution.get("tool_calls") or []))
    recovery_attempted = False
    recovered_from_failure = False

    if enable_recovery and (failure_detected or conflict_detected):
        recovery_attempted = True
        reset_runtime()
        try:
            retry_started = time.perf_counter()
            recovery_execution = execute_method(method, {**intent, "conflict_seed": None, "expects_conflict": False}, duration_s)
            retry_latency_ms = (time.perf_counter() - retry_started) * 1000.0
            recovery_result = {
                "status": recovery_execution.get("status"),
                "tool_calls": recovery_execution.get("tool_calls"),
                "generated_workflow": recovery_execution.get("generated_workflow"),
                "latency_ms": round(retry_latency_ms, 3),
            }
            recovered_from_failure = not detect_failure(recovery_execution, list(recovery_execution.get("tool_calls") or [])) and not detect_conflict(recovery_execution, list(recovery_execution.get("tool_calls") or []))
        except Exception as exc:  # pragma: no cover - runtime dependent
            recovery_result = {"status": "failed", "error": str(exc)}
            recovered_from_failure = False

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
        recovery_result=recovery_result,
        conflict_seed=conflict_seed,
        method_error=method_error,
    )
    reset_runtime()
    return record


def manifest(methods: List[str], intents: List[Dict[str, Any]], repeats: int, duration_s: int) -> Dict[str, Any]:
    return {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "methods": methods,
        "intent_count": len(intents),
        "repeat_count": repeats,
        "duration_s": duration_s,
        "evaluation_runtime_config": copy.deepcopy(EVAL_RUNTIME_CONFIG),
        "method_labels": {method: METHOD_LABELS.get(method, method) for method in methods},
        "planner_inference_settings": llm_sampling_settings(),
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
    parser.add_argument("--disable-recovery", action="store_true")
    parser.add_argument("--metrics-mode", choices=["off", "cached", "live"], default="live")
    parser.add_argument("--metrics-min-interval-s", type=float, default=15.0)
    parser.add_argument("--observation-cache-ttl-s", type=float, default=0.0)
    parser.add_argument("--planner-cache-ttl-s", type=float, default=0.0)
    parser.add_argument("--workflow-poll-timeout-s", type=float, default=2.0)
    parser.add_argument("--workflow-poll-interval-s", type=float, default=0.05)
    parser.add_argument("--tool-ack-timeout-s", type=float, default=10.0, help="How long to wait for launched xApps to show real work in their logs before marking the tool call unacknowledged.")
    parser.add_argument("--retrieval-k", type=int, default=0, help="Agent-card retrieval depth for the planner prompt; 0 = include every executable card (small-registry mode).")
    parser.add_argument("--retrieval-include-deprecated", action="store_true", help="Let deprecated directory cards be retrieved (harder discovery).")
    parser.add_argument("--label", default="", help="Optional suffix for the run directory name.")
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
            "retrieval_include_deprecated": bool(args.retrieval_include_deprecated),
            "rapp_directory_enabled": os.getenv("FLEXRIC_RAPP_DIRECTORY", "").strip().lower() in {"1", "true", "yes", "on"},
        }
    )
    intent_path = Path(args.intents).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    methods = [method for method in args.methods if method in METHODS]
    if not methods:
        raise SystemExit("No supported methods were selected.")

    intents = load_intents(intent_path)
    if args.max_intents > 0:
        intents = intents[: args.max_intents]

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S_%fZ")
    output_dir = output_root / (f"{timestamp}_{args.label}" if args.label else timestamp)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_manifest = manifest(methods, intents, args.repeat, args.duration_s)
    (output_dir / "manifest.json").write_text(json.dumps(batch_manifest, indent=2, sort_keys=True), encoding="utf-8")
    # Records are appended as they finish so a long batch can be watched and survives a crash.
    partial_path = output_dir / "records.partial.jsonl"
    total = max(1, int(args.repeat)) * len(intents) * len(methods)
    records: List[Dict[str, Any]] = []
    for repeat_index in range(1, max(1, int(args.repeat)) + 1):
        for intent in intents:
            for method in methods:
                record = run_record(
                    method=method,
                    intent=intent,
                    repeat_index=repeat_index,
                    duration_s=int(args.duration_s),
                    enable_recovery=not args.disable_recovery,
                )
                records.append(record)
                with partial_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
                print(f"[{len(records)}/{total}] r{repeat_index} {method} {intent.get('id')}", flush=True)

    write_artifacts(output_dir, intents, records, batch_manifest)
    partial_path.unlink(missing_ok=True)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
