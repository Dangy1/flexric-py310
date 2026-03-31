#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

try:
    from backend.a2a_adapter import A2AAdapter, A2AHandlers
    from backend.agents import build_agents
    from backend.common import AgentAction, AgentCard, PORTAL_MANAGED_RUNTIME_ITEMS, SERVICE_RESTART_COMPONENTS
    from backend.graph.runtime import graph_backend_name, graph_runtime_status, langsmith_status, run_graph_workflow
    from backend.graph.tools import PortalToolbox, build_langchain_tools
    from backend.orchestration import (
        GRAPH_STAGE_AGENTS,
        GRAPH_STAGE_LABELS,
        WORKFLOW_ACTIONS,
        WORKFLOW_RESOURCE_REQUIREMENTS,
        WORKFLOW_TEMPLATES,
    )
except Exception:
    A2AAdapter = None
    A2AHandlers = None
    AgentAction = None
    AgentCard = None
    build_agents = None
    PortalToolbox = None
    PORTAL_MANAGED_RUNTIME_ITEMS = []
    SERVICE_RESTART_COMPONENTS = []
    GRAPH_STAGE_AGENTS = {}
    GRAPH_STAGE_LABELS = {}
    WORKFLOW_ACTIONS = {}
    WORKFLOW_RESOURCE_REQUIREMENTS = {}
    WORKFLOW_TEMPLATES = {}

    def graph_backend_name() -> str:
        return "legacy"

    def graph_runtime_status() -> Dict[str, Any]:
        return {
            "backend": "legacy",
            "langgraph_installed": False,
            "node_names": [],
            "supports_tracing": False,
            "tracing": {
                "installed": False,
                "enabled": False,
                "api_key_present": False,
                "project": "flexric-agent-portal",
                "endpoint": "https://api.smith.langchain.com",
                "detail": "LangGraph runtime helpers were not imported.",
            },
        }

    def langsmith_status() -> Dict[str, Any]:
        return graph_runtime_status()["tracing"]

    def build_langchain_tools(toolbox: Any) -> List[Any]:
        return []

    run_graph_workflow = None

load_dotenv()

THIS_DIR = Path(__file__).resolve().parent
PORTAL_DIR = THIS_DIR / "agent_portal"
RUN_LOG_DIR = Path(os.getenv("FLEXRIC_AGENT_PORTAL_LOG_DIR", "/tmp/flexric_agent_portal"))
RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
PORTAL_DB_PATH = Path(os.getenv("FLEXRIC_AGENT_PORTAL_DB_PATH", str(THIS_DIR / "agent_portal.db")))
PORTAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_WORKFLOW_DURATION_S = max(15, int(os.getenv("FLEXRIC_WORKFLOW_DURATION_S", "45")))
WORKFLOW_DURATION_GRACE_S = max(10, int(os.getenv("FLEXRIC_WORKFLOW_GRACE_S", "25")))
WORKFLOW_QUEUE_TIMEOUT_S = max(30, int(os.getenv("FLEXRIC_WORKFLOW_QUEUE_TIMEOUT_S", "240")))
WORKFLOW_LEASE_TIMEOUT_GRACE_S = max(15, int(os.getenv("FLEXRIC_WORKFLOW_LEASE_TIMEOUT_GRACE_S", "45")))


def _portal_asset_version() -> str:
    assets = [
        PORTAL_DIR / "index.html",
        PORTAL_DIR / "app.js",
        PORTAL_DIR / "styles.css",
    ]
    latest = 0
    for asset in assets:
        if asset.exists():
            latest = max(latest, int(asset.stat().st_mtime))
    return str(latest or int(time.time()))


def _portal_html() -> str:
    html = (PORTAL_DIR / "index.html").read_text(encoding="utf-8")
    version = _portal_asset_version()
    return (
        html.replace('/portal/assets/styles.css', f'/portal/assets/styles.css?v={version}')
        .replace('/portal/assets/app.js', f'/portal/assets/app.js?v={version}')
    )


def _graph_stage_events(events: List[Dict[str, Any]], stage: str) -> List[Dict[str, Any]]:
    return [event for event in events if event.get("stage") == stage]


def _make_stage_output(label: str, content: Any, **metadata: Any) -> Dict[str, Any]:
    item = {"label": label, "content": str(content)}
    for key, value in metadata.items():
        if value is not None:
            item[key] = value
    return item


def _run_result_sort_key(result: Dict[str, Any]) -> tuple[int, int, float]:
    status = str(result.get("status") or "")
    priority = {
        "launching": 0,
        "starting": 0,
        "running": 0,
        "exited": 1,
        "completed": 1,
        "success": 1,
        "blocked_by_conflict": 2,
        "failed": 2,
        "timed_out": 2,
        "cancelled": 2,
        "queued": 3,
    }
    run_id = str(result.get("id") or result.get("run_id") or "")
    blocked_placeholder = 1 if run_id.startswith("blocked:") else 0
    ts = -float(result.get("ended_at") or result.get("started_at") or 0.0)
    return (priority.get(status, 4), blocked_placeholder, ts)


def _dedupe_workflow_run_results(run_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    ordered_keys: List[Tuple[str, str]] = []
    extras: List[Dict[str, Any]] = []
    for item in run_results:
        result = dict(item)
        agent_id = str(result.get("agent_id") or "")
        action_id = str(result.get("action_id") or "")
        if not agent_id or not action_id:
            extras.append(result)
            continue
        key = (agent_id, action_id)
        current = best_by_key.get(key)
        if current is None:
            best_by_key[key] = result
            ordered_keys.append(key)
            continue
        if _run_result_sort_key(result) < _run_result_sort_key(current):
            best_by_key[key] = result
    return [best_by_key[key] for key in ordered_keys] + extras


def _dedupe_text_items(items: List[Any]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for item in items:
        text = str(item)
        if text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def _group_text_items(items: List[Any]) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    index_by_text: Dict[str, int] = {}
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        index = index_by_text.get(text)
        if index is None:
            index_by_text[text] = len(groups)
            groups.append({"text": text, "count": 1})
        else:
            groups[index]["count"] += 1
    return groups


def _build_graph_steps_payload(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = list(run.get("events", []))
    observations = list(run.get("observations", []))
    hypotheses = list(run.get("hypotheses", []))
    recommendations = list(run.get("recommendations", []))
    verification_notes = list(run.get("verification_notes", []))
    errors = list(run.get("errors", []))
    selected_actions = list(run.get("selected_actions", []))
    run_results = list(run.get("run_results", []))
    result_by_key = {}
    for result in run_results:
        key = (result.get("agent_id"), result.get("action_id"))
        if key[0] and key[1]:
            result_by_key[key] = result

    observe_events = _graph_stage_events(events, "observe")
    observe_outputs = [_make_stage_output("Observation", item) for item in observations]

    diagnose_events = _graph_stage_events(events, "diagnose")
    diagnose_outputs = [_make_stage_output("Hypothesis", item) for item in hypotheses]
    diagnose_outputs.extend(_make_stage_output("Recommendation", item) for item in recommendations)

    approve_events = _graph_stage_events(events, "approve")
    approval_reason = str(run.get("approval_reason") or "No approval note.")
    approval_required = bool(run.get("approval_required"))
    approved_value = run.get("approved")
    approved = approved_value is True
    if approval_required:
        approval_decision = "Approved" if approved else "Not approved"
    else:
        approval_decision = "Not applicable"
    approve_outputs: List[Dict[str, Any]] = []
    if approval_required or approval_reason or approve_events or approved_value is not None:
        approve_outputs = [
            _make_stage_output("Decision", approval_decision),
            _make_stage_output("Reason", approval_reason),
        ]

    act_events = _graph_stage_events(events, "act")
    act_outputs: List[Dict[str, Any]] = []
    active_results = 0
    failed_results = 0
    queued_results = 0
    for item in selected_actions:
        agent_id = str(item.get("agent_id") or "unknown")
        action_id = str(item.get("action_id") or "unknown")
        result = result_by_key.get((agent_id, action_id))
        if result is not None:
            status = str(result.get("status") or "unknown")
            if status in {"starting", "running", "launching"}:
                active_results += 1
            elif status in {"queued"}:
                queued_results += 1
            elif status in {"blocked_by_conflict"}:
                queued_results += 1
                failed_results += 1
            elif status not in {"exited", "completed", "success"}:
                failed_results += 1
            act_outputs.append(
                _make_stage_output(
                    "Launch",
                    f"{agent_id}:{action_id} -> {status}",
                    agent_id=agent_id,
                    action_id=action_id,
                    run_id=result.get("id"),
                    status=status,
                    returncode=result.get("returncode"),
                )
            )
        else:
            act_outputs.append(
                _make_stage_output(
                    "Planned action",
                    f"{agent_id}:{action_id}",
                    agent_id=agent_id,
                    action_id=action_id,
                )
            )

    verify_events = _graph_stage_events(events, "verify")
    verify_outputs = [_make_stage_output("Verification", item) for item in verification_notes]

    summarize_events = _graph_stage_events(events, "summarize")
    summarize_outputs: List[Dict[str, Any]] = []
    if run.get("summary"):
        summarize_outputs.append(_make_stage_output("Summary", run.get("summary")))
    summarize_outputs.extend(_make_stage_output("Error", item) for item in errors)

    if selected_actions and approved:
        if active_results:
            act_status = "running"
            act_summary = f"{active_results} launched action(s) still running."
        elif queued_results:
            act_status = "queued"
            act_summary = f"{queued_results} action(s) are waiting for scheduler resources."
        elif failed_results:
            act_status = "completed"
            act_summary = f"{failed_results} launched action(s) finished with issues."
        elif run_results:
            act_status = "completed"
            act_summary = f"{len(run_results)} action(s) launched successfully."
        else:
            act_status = "completed" if errors else "pending"
            act_summary = "Action execution was approved but nothing was launched."
    elif selected_actions and approval_required:
        act_status = "completed"
        act_summary = "Execution stopped at the RC approval stage."
    elif selected_actions:
        act_status = "completed"
        act_summary = "Execution was skipped because this workflow ran in advisory mode."
    else:
        act_status = "completed"
        act_summary = "No concrete action is mapped for this workflow."

    if active_results:
        verify_status = "running"
    elif queued_results:
        verify_status = "queued"
    elif failed_results or errors:
        verify_status = "completed"
    elif verify_outputs or verify_events:
        verify_status = "completed"
    else:
        verify_status = "pending"

    summarize_status = str(run.get("status") or "pending")
    if summarize_status not in {"running", "completed", "pending", "queued", "waiting_for_approval", "admitted", "completed_with_issues", "cancelled", "expired"}:
        summarize_status = "completed"

    stages = [
        {
            "id": "observe",
            "label": GRAPH_STAGE_LABELS["observe"],
            "agent_id": GRAPH_STAGE_AGENTS["observe"],
            "status": "completed" if observe_outputs or observe_events else "pending",
            "summary": f"Collected {len(observe_outputs)} observations from service health and agent snapshots.",
            "outputs": observe_outputs,
            "events": observe_events,
        },
        {
            "id": "diagnose",
            "label": GRAPH_STAGE_LABELS["diagnose"],
            "agent_id": GRAPH_STAGE_AGENTS["diagnose"],
            "status": "completed" if diagnose_outputs or diagnose_events else "pending",
            "summary": f"Generated {len(hypotheses)} hypotheses and {len(recommendations)} recommendations.",
            "outputs": diagnose_outputs,
            "events": diagnose_events,
        },
        {
            "id": "approve",
            "label": GRAPH_STAGE_LABELS["approve"],
            "agent_id": GRAPH_STAGE_AGENTS["approve"],
            "status": "completed" if approve_outputs or approve_events else "pending",
            "summary": approval_reason,
            "outputs": approve_outputs,
            "events": approve_events,
            "metadata": {
                "approval_required": approval_required,
                "approved": approved_value,
                "mode": run.get("mode", "advisory"),
            },
        },
        {
            "id": "act",
            "label": GRAPH_STAGE_LABELS["act"],
            "agent_id": GRAPH_STAGE_AGENTS["act"],
            "status": act_status,
            "summary": act_summary,
            "outputs": act_outputs,
            "events": act_events,
            "metadata": {
                "selected_action_count": len(selected_actions),
                "launched_action_count": len(run_results),
            },
        },
        {
            "id": "verify",
            "label": GRAPH_STAGE_LABELS["verify"],
            "agent_id": GRAPH_STAGE_AGENTS["verify"],
            "status": verify_status,
            "summary": f"Prepared {len(verify_outputs)} verification note(s).",
            "outputs": verify_outputs,
            "events": verify_events,
        },
        {
            "id": "summarize",
            "label": GRAPH_STAGE_LABELS["summarize"],
            "agent_id": GRAPH_STAGE_AGENTS["summarize"],
            "status": summarize_status,
            "summary": str(run.get("summary") or "No summary recorded yet."),
            "outputs": summarize_outputs,
            "events": summarize_events,
        },
    ]
    return stages


def _synchronize_graph_workflow_locked(workflow: Dict[str, Any]) -> None:
    run_results = workflow.get("run_results")
    if not isinstance(run_results, list):
        return
    workflow["run_results"] = _dedupe_workflow_run_results(run_results)
    run_results = workflow["run_results"]
    workflow["errors"] = _dedupe_text_items(list(workflow.get("errors", [])))
    workflow["error_groups"] = _group_text_items(list(workflow.get("errors", [])))
    workflow["recommendation_groups"] = _group_text_items(list(workflow.get("recommendations", [])))

    selected_actions = list(workflow.get("selected_actions", []))
    result_by_key = {
        (result.get("agent_id"), result.get("action_id")): result
        for result in run_results
        if result.get("agent_id") and result.get("action_id")
    }

    for step in workflow.get("steps", []):
        agent_id = step.get("agent_id")
        action_id = step.get("action_id")
        if not action_id:
            mapped = next(
                (
                    item.get("action_id")
                    for item in selected_actions
                    if item.get("agent_id") == agent_id and item.get("action_id")
                ),
                None,
            )
            if mapped:
                step["action_id"] = mapped
                step.setdefault("action_label", mapped)
                action_id = mapped
        if not agent_id or not action_id:
            continue
        result = result_by_key.get((agent_id, action_id))
        if result is None:
            continue

        status = str(result.get("status") or "unknown")
        step["run_id"] = result.get("id") or result.get("run_id")
        step["run_status"] = status
        step["returncode"] = result.get("returncode")
        step["message"] = f"{agent_id}:{action_id} -> {status}"
        if status in {"starting", "running", "launching"}:
            step["status"] = "running"
        elif status in {"queued", "blocked_by_conflict"}:
            step["status"] = "queued"
            step["detail"] = result.get("detail") or step.get("detail")
        elif status in {"exited", "completed", "success"}:
            step["status"] = "completed"
            step["ended_at"] = result.get("ended_at") or time.time()
            step.pop("error", None)
        elif status == "cancelled":
            step["status"] = "cancelled"
            step["ended_at"] = result.get("ended_at") or time.time()
            step["detail"] = result.get("detail")
            step["error"] = str(result.get("detail") or f"Action {step.get('action_label', action_id)} was cancelled.")
        elif status == "timed_out":
            step["status"] = "timed_out"
            step["ended_at"] = result.get("ended_at") or time.time()
            step["detail"] = result.get("detail")
            step["error"] = str(result.get("detail") or f"Action {step.get('action_label', action_id)} timed out.")
        else:
            step["status"] = "failed"
            step["ended_at"] = result.get("ended_at") or time.time()
            step["detail"] = result.get("detail")
            step["error"] = str(result.get("detail") or f"Action {step.get('action_label', action_id)} failed.")

    active_results = 0
    failed_results = 0
    queued_results = 0
    verification_notes = []
    for result in run_results:
        agent_id = str(result.get("agent_id") or "unknown")
        status = str(result.get("status") or "unknown")
        detail = str(result.get("detail") or "").strip()
        verification_notes.append(f"{agent_id} launch status: {status}" + (f". {detail}" if detail else ""))
        if status in {"starting", "running", "launching"}:
            active_results += 1
        elif status == "queued":
            queued_results += 1
        elif status == "blocked_by_conflict":
            failed_results += 1
        elif status not in {"exited", "completed", "success"}:
            failed_results += 1

    if verification_notes:
        workflow["verification_notes"] = verification_notes
    workflow["verification_note_groups"] = _group_text_items(list(workflow.get("verification_notes", [])))

    current_status = str(workflow.get("status") or "")
    scheduler_waiting = _workflow_has_scheduler_queue_state(workflow)
    if active_results:
        workflow["status"] = "running"
    elif current_status == "cancelled":
        workflow["status"] = current_status
    elif current_status == "waiting_for_approval" and workflow.get("approved") is not True:
        workflow["status"] = current_status
    elif current_status == "expired" and scheduler_waiting:
        workflow["status"] = current_status
    elif queued_results and scheduler_waiting:
        workflow["status"] = "queued"
    elif run_results:
        workflow["status"] = "completed_with_issues" if failed_results else "completed"
    elif selected_actions and workflow.get("approved") is not True:
        workflow["status"] = "waiting_for_approval"
    else:
        workflow["status"] = "completed_with_issues" if workflow.get("errors") else "completed"

    workflow["active_run_count"] = active_results
    workflow["action_run_count"] = len(run_results)
    workflow["completed_step_count"] = sum(1 for step in workflow.get("steps", []) if step.get("status") == "completed")
    workflow["queue_position"] = _workflow_queue_position_locked(workflow)
    workflow["updated_at"] = time.time()
    if workflow["status"] in {"completed", "completed_with_issues", "cancelled", "expired"}:
        workflow["completed_at"] = workflow.get("completed_at") or workflow["updated_at"]
    else:
        workflow["completed_at"] = None

    recommendations = list(workflow.get("recommendations", []))
    approval = workflow.get("approval_reason", "No approval note.")
    verification_count = len(list(workflow.get("verification_notes", [])))
    summary = (
        f"Mode={workflow.get('mode', 'advisory')}. Approval: {approval} "
        f"Recommendations={len(recommendations)}. "
        f"Actions launched={len(run_results)}. "
        f"Verification notes={verification_count}."
    )
    if workflow.get("blocked_reason"):
        summary += f" Queue={workflow.get('blocked_reason')}"
    if workflow.get("errors"):
        summary += f" Errors={len(list(workflow.get('errors', [])))}."
    workflow["summary"] = summary
    workflow["scheduler"] = {
        "state": workflow.get("status"),
        "queue_position": workflow.get("queue_position"),
        "blocked_reason": workflow.get("blocked_reason", ""),
        "required_resources": list(workflow.get("required_resources", [])),
        "lease_state": workflow.get("lease_state") or {"state": "none", "leases": []},
    }
    workflow["graph_steps"] = _build_graph_steps_payload(workflow)



def _refresh_graph_workflow_locked(workflow: Dict[str, Any]) -> None:
    _expire_workflow_locked(workflow)
    run_results = workflow.get("run_results")
    if not isinstance(run_results, list):
        return

    events = workflow.setdefault("events", [])
    workflow_errors = [str(item) for item in workflow.get("errors", [])]
    loaded_without_state = any("Loaded from persisted storage" in item for item in workflow_errors)
    for result in run_results:
        previous_status = str(result.get("status") or "")
        run_id = result.get("id") or result.get("run_id")
        child = RUNS.get(run_id) if run_id else None
        if child is None:
            if previous_status in {"starting", "running", "launching"} and (loaded_without_state or workflow.get("timed_out")):
                result["status"] = "timed_out" if workflow.get("timed_out") else "failed"
                result["returncode"] = result.get("returncode", -15)
                result["ended_at"] = result.get("ended_at") or time.time()
                result["detail"] = result.get("detail") or (workflow.get("errors") or ["Action state was unavailable after restart."])[-1]
            continue
        latest = child.to_public()
        result.update(latest)
        result.setdefault("agent_id", child.agent_id)
        result.setdefault("action_id", child.action_id)
        result.setdefault("label", child.label)
        if child.status != previous_status and child.status in {"exited", "failed", "timed_out", "cancelled"}:
            if child.status == "exited":
                event_kind = "action-completed"
            elif child.status == "timed_out":
                event_kind = "action-timed-out"
            elif child.status == "cancelled":
                event_kind = "action-cancelled"
            else:
                event_kind = "action-failed"
            detail = child.detail or f"Action {child.action_id} for {child.agent_id} finished with status {child.status}."
            events.append(
                {
                    "timestamp": time.time(),
                    "stage": "act",
                    "kind": event_kind,
                    "agent_id": child.agent_id,
                    "content": detail,
                    "metadata": {
                        "action_id": child.action_id,
                        "run_id": child.id,
                        "returncode": child.returncode,
                        "status": child.status,
                    },
                }
            )

    _synchronize_graph_workflow_locked(workflow)
    if workflow.get("status") in {"completed", "completed_with_issues", "cancelled", "expired"}:
        _release_workflow_leases_locked(workflow, f"Workflow reached terminal state {workflow.get('status')}.")
    _persist_workflow_run_locked(workflow)



@dataclass
class RunState:
    id: str
    agent_id: str
    action_id: str
    label: str
    cmd: List[str]
    cwd: str
    log_path: str
    started_at: float
    status: str = "starting"
    pid: Optional[int] = None
    returncode: Optional[int] = None
    ended_at: Optional[float] = None
    detail: str = ""
    termination_reason: str = ""
    proc: Optional[subprocess.Popen] = field(default=None, repr=False)

    def to_public(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "action_id": self.action_id,
            "label": self.label,
            "cmd": self.cmd,
            "cwd": self.cwd,
            "log_path": self.log_path,
            "started_at": self.started_at,
            "status": self.status,
            "pid": self.pid,
            "returncode": self.returncode,
            "ended_at": self.ended_at,
            "detail": self.detail,
            "termination_reason": self.termination_reason,
        }


@dataclass
class TaskState:
    id: str
    agent_id: str
    provider_id: str
    prompt: str
    status: str
    started_at: float
    response: str = ""
    error: str = ""
    ended_at: Optional[float] = None

    def to_public(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "provider_id": self.provider_id,
            "prompt": self.prompt,
            "status": self.status,
            "started_at": self.started_at,
            "response": self.response,
            "error": self.error,
            "ended_at": self.ended_at,
        }


class MessageRequest(BaseModel):
    target_id: str
    content: str
    kind: str = "handoff"


class WorkflowRequest(BaseModel):
    goal: str = "Optimize the near-RT RIC using live telemetry and control loops."
    mode: str = "advisory"
    duration_s: Optional[int] = None


class WorkflowApprovalRequest(BaseModel):
    reason: str = "Manually approved from the portal UI. Execute the selected actions now."


class SavedWorkflowRequest(BaseModel):
    name: str
    purpose: str = ""


class AgentTaskRequest(BaseModel):
    prompt: str
    provider: str = "auto"


class TestAllRequest(BaseModel):
    include_actions: bool = True
    include_messages: bool = True


class RuntimeResetRequest(BaseModel):
    clear_saved_workflows: bool = False


def _package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _normalize_runtime_host(host: str) -> str:
    value = (host or "").strip()
    return "127.0.0.1" if value in {"", "0.0.0.0", "::"} else value


def _normalize_workflow_duration_s(value: Any) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        duration = DEFAULT_WORKFLOW_DURATION_S
    return max(15, min(duration, 1800))


def _command_flag_value(command: List[str], flag: str) -> Optional[str]:
    try:
        idx = command.index(flag)
    except ValueError:
        return None
    next_idx = idx + 1
    if next_idx >= len(command):
        return None
    return str(command[next_idx])


def _action_expected_duration_s(action: AgentAction) -> int:
    value = _command_flag_value(action.command, "--duration-s")
    try:
        return max(1, int(value)) if value is not None else 30
    except (TypeError, ValueError):
        return 30


def _workflow_recommended_duration_s(workflow_id: str) -> int:
    mapping = WORKFLOW_ACTIONS.get(workflow_id, {})
    durations: List[int] = []
    for agent_id, action_id in mapping.items():
        agent = AGENTS.get(agent_id)
        if agent is None:
            continue
        action = next((item for item in agent.actions if item.id == action_id), None)
        if action is None:
            continue
        durations.append(_action_expected_duration_s(action))
    if not durations:
        return DEFAULT_WORKFLOW_DURATION_S
    return max(DEFAULT_WORKFLOW_DURATION_S, max(durations) + WORKFLOW_DURATION_GRACE_S)


def _resource_requirements_for_workflow(workflow_id: str) -> List[Dict[str, Any]]:
    items = WORKFLOW_RESOURCE_REQUIREMENTS.get(workflow_id, [])
    return [dict(item) for item in items]


def _apply_workflow_duration_policy(workflow_id: str, requested_duration_s: Any) -> Tuple[int, Optional[str]]:
    requested = _normalize_workflow_duration_s(requested_duration_s)
    recommended = _workflow_recommended_duration_s(workflow_id)
    if requested >= recommended:
        return requested, None
    return recommended, f"Workflow window auto-expanded from {requested}s to {recommended}s so the mapped actions can finish cleanly."


def _summarize_run_failure(run: RunState) -> str:
    if run.termination_reason:
        if "execution window" in run.termination_reason:
            return f"Stopped by the workflow timeout: {run.termination_reason}"
        return run.termination_reason
    tail = [line.strip() for line in _tail_lines(run.log_path, 12) if str(line).strip()]
    for line in reversed(tail):
        if "Another TC Python xApp is already running" in line:
            return line
        if "No E2 nodes connected" in line:
            return line
        if line.startswith("Traceback"):
            continue
        return line
    if run.returncode == -15:
        return "Stopped before the action could finish cleanly."
    return f"Process exited with rc={run.returncode}."


def _display_runtime_host(bind_host: str, public_host: str) -> str:
    explicit = (public_host or "").strip()
    if explicit:
        return explicit
    value = (bind_host or "").strip()
    return "127.0.0.1" if value in {"", "0.0.0.0", "::"} else value


def _mcp_service_status_locked() -> Dict[str, Any]:
    for service in _service_health():
        if service.get("id") == "mcp":
            return service
    return {"id": "mcp", "label": "MCP Metrics", "ok": False, "status": "down", "detail": "MCP service state is unavailable."}


_KPM_LINE_RE = re.compile(
    r"ue_type=(?P<ue_type>\S+)\s+amf_ue_ngap_id=(?P<ue_id>\S+)\s+meas=(?P<meas>\S+)\s+value=(?P<value>\S+)"
)


AGENTS = build_agents(sys.executable, THIS_DIR) if build_agents is not None else {}
RUNS: Dict[str, RunState] = {}
TASKS: List[TaskState] = []
MESSAGES: List[Dict[str, Any]] = []
WORKFLOW_RUNS: List[Dict[str, Any]] = []
MANAGED_SERVICE_PROCS: Dict[str, subprocess.Popen] = {}
STATE_LOCK = threading.RLock()


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PORTAL_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table_columns(conn: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _init_portal_db() -> None:
    with _db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY, workflow_id TEXT, label TEXT, goal TEXT, mode TEXT,
                status TEXT, started_at REAL, updated_at REAL, payload TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_workflows (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL UNIQUE, workflow_id TEXT, label TEXT,
                name TEXT NOT NULL, purpose TEXT, route TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_id TEXT, agent_id TEXT, status TEXT,
                started_at REAL, ended_at REAL, payload TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resource_leases (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, resource_id TEXT NOT NULL, mode TEXT, state TEXT,
                acquired_at REAL, heartbeat_at REAL, timeout_at REAL, released_at REAL, payload TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_queue_entries (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, resource_id TEXT NOT NULL, state TEXT, queued_at REAL, reason TEXT, payload TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_events (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, event_ts REAL, stage TEXT, kind TEXT, agent_id TEXT, payload TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operator_actions (
                id TEXT PRIMARY KEY, run_id TEXT, action TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT, created_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS implementation_change_log (
                id TEXT PRIMARY KEY, change_id TEXT NOT NULL, summary TEXT NOT NULL, result TEXT NOT NULL, created_at REAL NOT NULL
            )
        """)
        _ensure_table_columns(conn, "workflow_runs", {"workflow_id": "TEXT", "label": "TEXT", "goal": "TEXT", "mode": "TEXT", "status": "TEXT", "started_at": "REAL", "updated_at": "REAL", "payload": "TEXT"})
        _ensure_table_columns(conn, "saved_workflows", {"workflow_id": "TEXT", "label": "TEXT", "name": "TEXT", "purpose": "TEXT", "route": "TEXT", "created_at": "REAL", "updated_at": "REAL"})
        _ensure_table_columns(conn, "workflow_steps", {"step_id": "TEXT", "agent_id": "TEXT", "status": "TEXT", "started_at": "REAL", "ended_at": "REAL", "payload": "TEXT"})
        _ensure_table_columns(conn, "resource_leases", {"mode": "TEXT", "state": "TEXT", "acquired_at": "REAL", "heartbeat_at": "REAL", "timeout_at": "REAL", "released_at": "REAL", "payload": "TEXT"})
        _ensure_table_columns(conn, "workflow_queue_entries", {"state": "TEXT", "queued_at": "REAL", "reason": "TEXT", "payload": "TEXT"})
        _ensure_table_columns(conn, "workflow_events", {"event_ts": "REAL", "stage": "TEXT", "kind": "TEXT", "agent_id": "TEXT", "payload": "TEXT"})
        _ensure_table_columns(conn, "operator_actions", {"run_id": "TEXT", "action": "TEXT", "actor": "TEXT", "detail": "TEXT", "created_at": "REAL"})
        _ensure_table_columns(conn, "implementation_change_log", {"change_id": "TEXT", "summary": "TEXT", "result": "TEXT", "created_at": "REAL"})
        conn.commit()


def _persist_workflow_run_locked(run: Dict[str, Any]) -> None:
    payload = json.dumps(run, default=str)
    updated_at = float(run.get("updated_at") or run.get("completed_at") or run.get("started_at") or time.time())
    run["updated_at"] = updated_at
    with _db_connect() as conn:
        conn.execute(
            """
            INSERT INTO workflow_runs (run_id, workflow_id, label, goal, mode, status, started_at, updated_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                workflow_id = excluded.workflow_id,
                label = excluded.label,
                goal = excluded.goal,
                mode = excluded.mode,
                status = excluded.status,
                started_at = excluded.started_at,
                updated_at = excluded.updated_at,
                payload = excluded.payload
            """,
            (run.get("id"), run.get("workflow_id"), run.get("label"), run.get("goal"), run.get("mode"), run.get("status"), float(run.get("started_at") or time.time()), updated_at, payload),
        )
        conn.execute("DELETE FROM workflow_steps WHERE run_id = ?", (run.get("id"),))
        conn.execute("DELETE FROM resource_leases WHERE run_id = ?", (run.get("id"),))
        conn.execute("DELETE FROM workflow_queue_entries WHERE run_id = ?", (run.get("id"),))
        conn.execute("DELETE FROM workflow_events WHERE run_id = ?", (run.get("id"),))
        run_id = str(run.get("id") or "")
        for index, step in enumerate(list(run.get("graph_steps") or run.get("steps") or [])):
            step_key = str(step.get("id") or index)
            row_id = f"{run_id}:step:{step_key}"
            conn.execute('INSERT INTO workflow_steps (id, run_id, step_id, agent_id, status, started_at, ended_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (row_id, run.get("id"), step.get("id"), step.get("agent_id"), step.get("status"), step.get("started_at"), step.get("ended_at"), json.dumps(step, default=str)))
        lease_state = run.get("lease_state") or {}
        for index, lease in enumerate(list(lease_state.get("leases") or [])):
            lease_key = str(lease.get("id") or lease.get("resource_id") or index)
            row_id = f"{run_id}:lease:{lease_key}"
            conn.execute('INSERT INTO resource_leases (id, run_id, resource_id, mode, state, acquired_at, heartbeat_at, timeout_at, released_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, run.get("id"), lease.get("resource_id"), lease.get("mode"), lease_state.get("state"), lease.get("acquired_at"), lease.get("heartbeat_at"), lease.get("timeout_at"), lease.get("released_at"), json.dumps(lease, default=str)))
        for index, entry in enumerate(list(run.get("queue_entries") or [])):
            entry_key = str(entry.get("id") or entry.get("resource_id") or index)
            row_id = f"{run_id}:queue:{entry_key}:{index}"
            conn.execute('INSERT INTO workflow_queue_entries (id, run_id, resource_id, state, queued_at, reason, payload) VALUES (?, ?, ?, ?, ?, ?, ?)', (row_id, run.get("id"), entry.get("resource_id"), entry.get("state"), entry.get("queued_at"), entry.get("reason"), json.dumps(entry, default=str)))
        for index, event in enumerate(list(run.get("events") or [])):
            event_key = str(event.get("id") or event.get("stage") or index)
            row_id = f"{run_id}:event:{event_key}:{index}"
            conn.execute('INSERT INTO workflow_events (id, run_id, event_ts, stage, kind, agent_id, payload) VALUES (?, ?, ?, ?, ?, ?, ?)', (row_id, run.get("id"), event.get("timestamp"), event.get("stage"), event.get("kind"), event.get("agent_id"), json.dumps(event, default=str)))
        conn.commit()


def _load_persisted_workflow_runs() -> List[Dict[str, Any]]:
    with _db_connect() as conn:
        rows = conn.execute("SELECT payload FROM workflow_runs ORDER BY started_at ASC").fetchall()
    runs: List[Dict[str, Any]] = []
    for row in rows:
        try:
            run = json.loads(row["payload"])
        except Exception:
            continue
        if str(run.get("status") or "") in {"running", "starting", "active", "admitted", "queued", "waiting_for_approval"}:
            run["status"] = "completed_with_issues"
            run.setdefault("errors", []).append("Loaded from persisted storage after restart; live child run state is unavailable.")
            run["completed_at"] = run.get("updated_at") or time.time()
        if not run.get("graph_steps"):
            run["graph_steps"] = _build_graph_steps_payload(run) if "selected_actions" in run else []
        runs.append(run)
    return runs


def _saved_workflows_locked() -> List[Dict[str, Any]]:
    with _db_connect() as conn:
        rows = conn.execute("SELECT id, run_id, workflow_id, label, name, purpose, route, created_at, updated_at FROM saved_workflows ORDER BY updated_at DESC, created_at DESC").fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        payload = {key: row[key] for key in row.keys()}
        try:
            run = _workflow_run_by_id(str(row["run_id"]))
        except HTTPException:
            run = None
        payload["run_status"] = run.get("status") if run else "missing"
        payload["run_mode"] = run.get("mode") if run else None
        payload["run_goal"] = run.get("goal") if run else None
        items.append(payload)
    return items


def _clear_persisted_workflow_runs_locked() -> None:
    with _db_connect() as conn:
        for table in ["workflow_runs", "workflow_steps", "resource_leases", "workflow_queue_entries", "workflow_events", "operator_actions"]:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()


def _clear_saved_workflows_locked() -> None:
    with _db_connect() as conn:
        conn.execute("DELETE FROM saved_workflows")
        conn.commit()


def _save_workflow_record_locked(run: Dict[str, Any], name: str, purpose: str) -> Dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Saved workflow name is required.")
    _persist_workflow_run_locked(run)
    now = time.time()
    with _db_connect() as conn:
        existing = conn.execute("SELECT id, created_at FROM saved_workflows WHERE run_id = ?", (run["id"],)).fetchone()
        record_id = existing["id"] if existing is not None else uuid.uuid4().hex
        created_at = float(existing["created_at"]) if existing is not None else now
        conn.execute("""
            INSERT INTO saved_workflows (id, run_id, workflow_id, label, name, purpose, route, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                name = excluded.name, purpose = excluded.purpose, workflow_id = excluded.workflow_id,
                label = excluded.label, route = excluded.route, updated_at = excluded.updated_at
        """, (record_id, run["id"], run.get("workflow_id"), run.get("label"), clean_name, purpose.strip(), f"/workflows/{run['id']}", created_at, now))
        conn.commit()
    return next(item for item in _saved_workflows_locked() if item["run_id"] == run["id"])


def _record_operator_action_locked(run_id: Optional[str], action: str, actor: str, detail: str) -> None:
    with _db_connect() as conn:
        columns = _table_columns(conn, "operator_actions")
        record_id = uuid.uuid4().hex
        created_at = time.time()
        payload = json.dumps(
            {
                "id": record_id,
                "run_id": run_id,
                "action": action,
                "actor": actor,
                "detail": detail,
                "created_at": created_at,
            },
            default=str,
        )
        if "payload" in columns:
            conn.execute(
                "INSERT INTO operator_actions (id, run_id, action, actor, detail, created_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (record_id, run_id, action, actor, detail, created_at, payload),
            )
        else:
            conn.execute(
                "INSERT INTO operator_actions (id, run_id, action, actor, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (record_id, run_id, action, actor, detail, created_at),
            )
        conn.commit()


def _recent_operator_actions_locked(limit: int = 25) -> List[Dict[str, Any]]:
    with _db_connect() as conn:
        rows = conn.execute("SELECT id, run_id, action, actor, detail, created_at FROM operator_actions ORDER BY created_at DESC LIMIT ?", (max(1, int(limit)),)).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _record_change_log_locked(change_id: str, summary: str, result: str) -> None:
    with _db_connect() as conn:
        columns = _table_columns(conn, "implementation_change_log")
        record_id = uuid.uuid4().hex
        created_at = time.time()
        if {"title", "detail"}.issubset(columns):
            conn.execute(
                "INSERT INTO implementation_change_log (id, title, detail, result, created_at, change_id, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (record_id, change_id, summary, result, created_at, change_id, summary),
            )
        else:
            conn.execute(
                "INSERT INTO implementation_change_log (id, change_id, summary, result, created_at) VALUES (?, ?, ?, ?, ?)",
                (record_id, change_id, summary, result, created_at),
            )
        conn.commit()


def _recent_change_log_locked(limit: int = 25) -> List[Dict[str, Any]]:
    with _db_connect() as conn:
        columns = _table_columns(conn, "implementation_change_log")
        if {"title", "detail"}.issubset(columns):
            rows = conn.execute(
                "SELECT id, COALESCE(change_id, title) AS change_id, COALESCE(summary, detail, title) AS summary, result, created_at FROM implementation_change_log ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, change_id, summary, result, created_at FROM implementation_change_log ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _platform_payload_locked() -> Dict[str, Any]:
    toolbox = _portal_toolbox_locked()
    langgraph = graph_runtime_status()
    langsmith = langgraph.get("tracing", langsmith_status())
    tools: List[Dict[str, Any]] = []
    langchain_error = ""
    if toolbox is not None:
        try:
            tools = [{"name": getattr(tool, "name", type(tool).__name__), "description": getattr(tool, "description", "")} for tool in build_langchain_tools(toolbox)]
        except Exception as exc:
            langchain_error = str(exc)

    services = _service_health()
    mcp_service = next((service for service in services if service.get("id") == "mcp"), {"id": "mcp", "label": "MCP Metrics", "ok": False, "status": "down", "detail": "MCP status unavailable."})
    a2a_methods = list(getattr(A2AAdapter, "orchestrator_methods", ["agents.list", "agent.get_card", "message.send", "workflow.run", "workflow.status", "workflow.events", "workflow.cancel", "workflow.queue_status", "agent.task.run", "portal.test_all", "portal.scheduler_status", "portal.reset_runtime"]))

    if langchain_error:
        langchain_detail = f"LangChain tool export failed: {langchain_error}"
    elif tools:
        langchain_detail = f"Portal toolbox currently exposes {len(tools)} LangChain tool(s)."
    else:
        langchain_detail = "LangChain is available, but no toolbox tools are registered yet."

    return {
        "label": "LangGraph",
        "description": "LangGraph is the orchestration runtime, while MCP is the telemetry and tool-access plane. They can work together, and LangGraph can keep running even if MCP is temporarily stopped.",
        "routes": {
            "page": "/platform",
            "scheduler_page": "/scheduler",
            "rpc": "/api/a2a/rpc",
            "overview": "/api/platform",
            "workflow_list": "/api/workflows",
            "orchestrator_card": "/.well-known/agent-card.json",
        },
        "langgraph": {
            "installed": bool(langgraph.get("langgraph_installed")),
            "backend": langgraph.get("backend", graph_backend_name()),
            "node_names": list(langgraph.get("node_names", [])),
            "workflow_templates": [{"id": workflow_id, "label": template["label"], "step_count": len(template["steps"]), "steps": list(template["steps"])} for workflow_id, template in WORKFLOW_TEMPLATES.items()],
            "detail": "LangGraph is the internal workflow runtime used by the portal when installed. It falls back to the linear runner otherwise.",
        },
        "langchain": {
            "installed": _package_available("langchain"),
            "tool_count": len(tools),
            "tools": tools,
            "detail": langchain_detail,
        },
        "a2a": {
            "installed": A2AAdapter is not None,
            "protocol": "A2A-aligned JSON-RPC",
            "rpc_path": "/api/a2a/rpc",
            "agent_card_path": "/.well-known/agent-card.json",
            "methods": a2a_methods,
            "cards": [{"agent_id": agent.id, "name": agent.name, "path": agent.a2a_card_path} for agent in AGENTS.values()],
            "detail": "The orchestrator exposes discovery cards plus workflow/task handoff methods over JSON-RPC.",
        },
        "langsmith": langsmith,
        "runtime_safety": _runtime_safety_locked(),
        "scheduler": _scheduler_payload_locked(),
        "scheduler_history": {
            "operator_actions": _recent_operator_actions_locked(),
            "implementation_changes": _recent_change_log_locked(),
            "endpoints": {
                "scheduler": "/api/runtime/scheduler",
                "leases": "/api/runtime/leases",
                "queues": "/api/runtime/queues",
                "reconcile": "/api/runtime/leases/reconcile",
            },
        },
        "mcp_control": {
            "service": mcp_service,
            "actions": {"start": "/api/runtime/mcp/start", "stop": "/api/runtime/mcp/stop"},
            "langgraph_mode": "LangGraph orchestrates workflow state and can still run in recommend-only mode even if MCP is stopped.",
            "mcp_mode": "The Overview page and the normal portal flow use MCP automatically when the service is up, so you do not need to pre-enable it before starting the stack.",
        },
    }


def _provider_statuses() -> List[Dict[str, Any]]:
    ollama_url = os.getenv("OLLAMA_BASE_URL", "").strip() or os.getenv("OLLAMA_URL", "").strip() or "http://127.0.0.1:11434"
    ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model = os.getenv("OPENAI_MODEL", "").strip()
    return [
        {"id": "ollama", "label": "Ollama", "enabled": bool(ollama_model), "endpoint": ollama_url, "model": ollama_model or "not-configured", "notes": "Best for private on-box automation loops and local model routing.", "supports_tasks": bool(ollama_model)},
        {"id": "openai", "label": "OpenAI API", "enabled": bool(os.getenv("OPENAI_API_KEY")) and bool(openai_model), "endpoint": openai_base_url, "model": openai_model or "not-configured", "notes": "Best for richer planning or cross-domain automation once API credentials are configured.", "supports_tasks": bool(os.getenv("OPENAI_API_KEY")) and bool(openai_model)},
    ]


def _timeline(text: str) -> str:
    return f"{time.strftime('%H:%M:%S')} {text}"


def _approve_graph_workflow_locked(workflow: Dict[str, Any], reason: str) -> Dict[str, Any]:
    selected_actions = list(workflow.get("selected_actions", []))
    if not selected_actions:
        raise HTTPException(status_code=400, detail="This workflow does not have any mapped actions to approve.")

    if isinstance(workflow.get("run_results"), list) and any(
        str(item.get("status") or "") in {"starting", "running", "launching"}
        for item in workflow["run_results"]
    ):
        _refresh_graph_workflow_locked(workflow)
        return workflow

    toolbox = _portal_toolbox_locked()
    events = workflow.setdefault("events", [])
    approval_reason = reason.strip() or "Manually approved from the portal UI. Execute the selected actions now."
    workflow["approval_required"] = True
    workflow["approved"] = True
    workflow["approval_reason"] = approval_reason
    approved_duration, duration_note = _apply_workflow_duration_policy(str(workflow.get("workflow_id") or ""), workflow.get("requested_duration_s") or workflow.get("duration_s"))
    workflow["effective_duration_s"] = approved_duration
    workflow["duration_s"] = approved_duration
    if duration_note:
        workflow.setdefault("errors", []).append(duration_note)

    approval_event = toolbox.event(
        "approve",
        "manual-approval",
        approval_reason,
        agent_id="rc",
        metadata={
            "approved": True,
            "approval_required": True,
            "manual": True,
            "mode": workflow.get("mode", "advisory"),
            "action_count": len(selected_actions),
        },
    ) if toolbox is not None else {
        "timestamp": time.time(),
        "stage": "approve",
        "kind": "manual-approval",
        "agent_id": "rc",
        "content": approval_reason,
        "metadata": {
            "approved": True,
            "approval_required": True,
            "manual": True,
            "mode": workflow.get("mode", "advisory"),
            "action_count": len(selected_actions),
        },
    }
    events.append(approval_event)
    workflow["events"] = events
    workflow["status"] = "admitted"
    _record_operator_action_locked(workflow.get("id"), "approve", "operator", approval_reason)
    approved = _scheduler_submit_workflow_locked(workflow, manual=True)
    _persist_workflow_run_locked(approved)
    return approved


def _service_targets() -> List[Dict[str, str]]:
    portal_bind_host = os.getenv("FLEXRIC_AGENT_PORTAL_HOST", "127.0.0.1")
    portal_host = _normalize_runtime_host(portal_bind_host)
    portal_public_host = _display_runtime_host(portal_bind_host, os.getenv("FLEXRIC_AGENT_PORTAL_PUBLIC_HOST", ""))
    portal_port = os.getenv("FLEXRIC_AGENT_PORTAL_PORT", "8088")
    rpc_bind_host = os.getenv("XAPP_RPC_HOST", "127.0.0.1")
    rpc_host = _normalize_runtime_host(rpc_bind_host)
    rpc_public_host = _display_runtime_host(rpc_bind_host, os.getenv("XAPP_RPC_PUBLIC_HOST", ""))
    rpc_port = os.getenv("XAPP_RPC_PORT", "8090")
    mcp_bind_host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_host = _normalize_runtime_host(mcp_bind_host)
    mcp_public_host = _display_runtime_host(mcp_bind_host, os.getenv("MCP_PUBLIC_HOST", ""))
    mcp_port = os.getenv("MCP_PORT", "8000")
    kpm_bus_bind_host = os.getenv("KPM_BUS_HOST", "127.0.0.1")
    kpm_bus_host = _normalize_runtime_host(kpm_bus_bind_host)
    kpm_bus_public_host = _display_runtime_host(kpm_bus_bind_host, os.getenv("KPM_BUS_PUBLIC_HOST", ""))
    kpm_bus_port = os.getenv("KPM_BUS_PORT", "8091")

    return [
        {
            "id": "portal",
            "label": "Agent Portal",
            "url": f"http://{portal_host}:{portal_port}/api/overview",
            "public_url": f"http://{portal_public_host}:{portal_port}/",
        },
        {
            "id": "rpc",
            "label": "xApp RPC",
            "url": f"http://{rpc_host}:{rpc_port}/health",
            "public_url": f"http://{rpc_public_host}:{rpc_port}/health",
        },
        {
            "id": "mcp",
            "label": "MCP Metrics",
            "url": f"http://{mcp_host}:{mcp_port}/healthz",
            "public_url": f"http://{mcp_public_host}:{mcp_port}/healthz",
        },
        {
            "id": "kpm_bus",
            "label": "KPM Bus",
            "url": f"http://{kpm_bus_host}:{kpm_bus_port}/healthz",
            "public_url": f"http://{kpm_bus_public_host}:{kpm_bus_port}/healthz",
        },
    ]


def _kpm_bus_base_url() -> str:
    kpm_bus_bind_host = os.getenv("KPM_BUS_HOST", "127.0.0.1")
    kpm_bus_host = _normalize_runtime_host(kpm_bus_bind_host)
    kpm_bus_port = os.getenv("KPM_BUS_PORT", "8091")
    return f"http://{kpm_bus_host}:{kpm_bus_port}"


def _parse_kpm_line(raw: str, seq: Optional[int] = None, ts: Optional[str] = None) -> Optional[Dict[str, Any]]:
    match = _KPM_LINE_RE.search(str(raw or "").strip())
    if not match:
        return None
    value_text = match.group("value")
    try:
        value = float(value_text)
    except ValueError:
        return None
    return {
        "seq": int(seq or 0),
        "ts": ts,
        "ue_type": match.group("ue_type"),
        "ue_id": match.group("ue_id"),
        "measurement": match.group("meas"),
        "value": value,
        "raw": raw,
    }


def _kpm_recent_records(limit: int = 180) -> Dict[str, Any]:
    try:
        response = requests.get(
            f"{_kpm_bus_base_url()}/kpm/recent",
            params={"mode": "all", "limit": max(20, min(limit, 400))},
            timeout=1.5,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return {
            "ok": False,
            "status": "down",
            "detail": f"KPM bus unavailable: {exc}",
            "records": [],
            "record_count": 0,
            "indication_count": 0,
            "last_ts": None,
        }

    parsed: List[Dict[str, Any]] = []
    for record in payload.get("records", []):
        point = _parse_kpm_line(record.get("raw"), seq=record.get("seq"), ts=record.get("ts"))
        if point is not None:
            parsed.append(point)
    payload["parsed_records"] = parsed
    payload["ok"] = bool(payload.get("ok", True))
    return payload


def _kpm_figure(metric_names: List[str], title: str, unit: str, description: str, records: List[Dict[str, Any]], colors: Dict[str, str]) -> Dict[str, Any]:
    series = []
    latest_values: List[Dict[str, Any]] = []
    for metric_name in metric_names:
        metric_records = [record for record in records if record["measurement"] == metric_name]
        points = [
            {
                "x": index + 1,
                "y": record["value"],
                "seq": record["seq"],
                "ts": record["ts"],
                "label": metric_name,
            }
            for index, record in enumerate(metric_records[-40:])
        ]
        if metric_records:
            latest = metric_records[-1]
            latest_values.append(
                {
                    "measurement": metric_name,
                    "value": latest["value"],
                    "seq": latest["seq"],
                    "ts": latest["ts"],
                }
            )
        series.append(
            {
                "id": metric_name,
                "label": metric_name.split(".")[-1],
                "measurement": metric_name,
                "color": colors.get(metric_name, "#0f6d78"),
                "points": points,
            }
        )
    sample_count = sum(len(item["points"]) for item in series)
    return {
        "title": title,
        "unit": unit,
        "description": description,
        "sample_count": sample_count,
        "series": series,
        "latest_values": latest_values,
    }


def _kpm_agent_figures_payload() -> Dict[str, Any]:
    payload = _kpm_recent_records()
    records = payload.get("parsed_records", [])
    figures = [
        _kpm_figure(
            ["RRU.PrbTotDl", "RRU.PrbTotUl"],
            "RRU PRB Levels",
            "PRB",
            "Latest downlink and uplink PRB totals from the shared KPM subscription.",
            records,
            {"RRU.PrbTotDl": "#0f6d78", "RRU.PrbTotUl": "#cc6b49"},
        ),
        _kpm_figure(
            ["DRB.UEThpDl", "DRB.UEThpUl", "DRB.RlcSduDelayDl"],
            "UE Throughput And Delay",
            "Throughput / Delay",
            "Downlink and uplink throughput with RLC delay from the same telemetry stream.",
            records,
            {
                "DRB.UEThpDl": "#114b5f",
                "DRB.UEThpUl": "#2f7d32",
                "DRB.RlcSduDelayDl": "#b85c38",
            },
        ),
    ]
    recent_measurements = [
        {
            "measurement": record["measurement"],
            "value": record["value"],
            "ue_id": record["ue_id"],
            "ts": record["ts"],
            "seq": record["seq"],
        }
        for record in records[-8:]
    ]
    return {
        "ok": bool(payload.get("ok")) and any(figure["sample_count"] > 0 for figure in figures),
        "status": "ready" if bool(payload.get("ok")) and records else str(payload.get("status", "warning")),
        "detail": payload.get("detail", "KPM figure data is unavailable."),
        "source": {
            "service": "kpm_bus",
            "url": f"{_kpm_bus_base_url()}/kpm/recent",
            "indication_count": int(payload.get("indication_count", 0)),
            "record_count": len(records),
            "last_ts": payload.get("last_ts"),
        },
        "figures": figures,
        "recent_measurements": recent_measurements,
    }


def _service_health() -> List[Dict[str, Any]]:
    timeout_s = float(os.getenv("FLEXRIC_AGENT_PORTAL_HEALTH_TIMEOUT", "1.5"))
    statuses: List[Dict[str, Any]] = []

    for target in _service_targets():
        started_at = time.time()
        status = {
            "id": target["id"],
            "label": target["label"],
            "url": target["url"],
            "public_url": target.get("public_url", target["url"]),
            "ok": False,
            "status": "down",
            "latency_ms": None,
            "detail": "",
        }
        if target["id"] == "portal":
            status["ok"] = True
            status["status"] = "ready"
            status["latency_ms"] = 0
            status["detail"] = "Local portal process is serving this request."
            statuses.append(status)
            continue
        try:
            response = requests.get(target["url"], timeout=timeout_s)
            latency_ms = int((time.time() - started_at) * 1000)
            status["latency_ms"] = latency_ms
            payload = None
            try:
                payload = response.json()
            except Exception:
                payload = None

            if payload is not None and isinstance(payload, dict):
                if payload.get("ok") is True:
                    status["ok"] = True
                    status["status"] = "ready"
                    status["detail"] = payload.get("detail", f"HTTP {response.status_code}")
                else:
                    reported = str(payload.get("status", "")).lower()
                    if reported in {"ok", "success", "ready"}:
                        status["ok"] = True
                        status["status"] = "ready"
                    elif reported == "warning":
                        status["ok"] = False
                        status["status"] = "warning"
                    else:
                        status["ok"] = response.ok
                        status["status"] = "ready" if response.ok else "warning"
                    status["detail"] = str(
                        payload.get("detail")
                        or payload.get("message")
                        or f"HTTP {response.status_code}"
                    )
            else:
                status["ok"] = response.ok
                status["status"] = "ready" if response.ok else "warning"
                if response.ok:
                    status["detail"] = f"HTTP {response.status_code}"
                else:
                    status["detail"] = f"HTTP {response.status_code}: {response.text[:200].strip()}"
        except Exception as exc:
            status["detail"] = str(exc)
        statuses.append(status)

    return statuses


def _summarize_local_child_runs(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summarized: List[Dict[str, Any]] = []
    for item in items:
        status = str(item.get("status") or item.get("run_status") or "unknown")
        run_id = item.get("id") or item.get("run_id")
        summarized.append(
            {
                "id": run_id,
                "agent_id": item.get("agent_id"),
                "action_id": item.get("action_id"),
                "label": item.get("label") or item.get("action_label") or item.get("action_id") or "run",
                "status": status,
                "detail": item.get("detail") or item.get("termination_reason") or "",
                "started_at": item.get("started_at"),
                "ended_at": item.get("ended_at"),
                "returncode": item.get("returncode"),
            }
        )
    return summarized


def _workflow_runtime_scope_locked(workflow: Dict[str, Any]) -> Dict[str, Any]:
    run_results = [dict(item) for item in workflow.get("run_results", [])]
    child_runs: List[Dict[str, Any]] = []
    for result in run_results:
        run_id = result.get("id") or result.get("run_id")
        child = RUNS.get(run_id) if run_id else None
        child_runs.append(child.to_public() if child is not None else result)
    summarized = _summarize_local_child_runs(child_runs)
    active_count = sum(1 for item in summarized if str(item.get("status") or "") in {"starting", "running", "launching"})
    lease_state = workflow.get("lease_state") or {}
    queue_entries = list(workflow.get("queue_entries") or [])
    if not queue_entries:
        blockers = _scheduler_blockers_locked(workflow)
        if blockers:
            queue_entries = _queue_entries_for_workflow(workflow, blockers)
    return {
        "portal_managed_state": list(PORTAL_MANAGED_RUNTIME_ITEMS),
        "local_child_run_count": len(summarized),
        "active_local_child_run_count": active_count,
        "local_child_runs": summarized,
        "queue_entry_count": len(queue_entries),
        "lease_count": len(list(lease_state.get("leases", []))),
        "reset_scope": "Emergency reset clears portal-managed runtime state and local child runs for this workflow, but it does not restart the FlexRIC services.",
        "restart_scope": "Restarting services restarts nearRT-RIC, emulator, portal, RPC, MCP, and KPM bus processes.",
        "service_restart_components": list(SERVICE_RESTART_COMPONENTS),
    }


def _agent_runtime_scope_locked(agent: AgentCard) -> Dict[str, Any]:
    runs = sorted((run.to_public() for run in RUNS.values() if run.agent_id == agent.id), key=lambda item: float(item.get("started_at") or 0), reverse=True)
    tasks = [task.to_public() for task in _agent_tasks(agent.id, limit=5)]
    summarized = _summarize_local_child_runs(runs[:5])
    active_count = sum(1 for item in summarized if str(item.get("status") or "") in {"starting", "running", "launching"})
    return {
        "portal_managed_state": [
            "local child xApp runs started from this agent page or workflow chain",
            "provider-backed tasks started from this agent page",
            "handoff messages and timeline entries recorded by the portal",
        ],
        "local_child_run_count": len(runs),
        "active_local_child_run_count": active_count,
        "local_child_runs": summarized,
        "task_count": len(tasks),
        "latest_task_status": tasks[0].get("status") if tasks else None,
        "reset_scope": "Emergency reset clears this agent's portal-managed runs, tasks, and workflow-linked state, but does not restart FlexRIC services.",
        "restart_scope": "Restarting services restarts nearRT-RIC, emulator, portal, RPC, MCP, and KPM bus processes.",
        "service_restart_components": list(SERVICE_RESTART_COMPONENTS),
    }


def _workflow_issue_count(run: Dict[str, Any]) -> int:
    count = len(list(run.get("errors", [])))
    for result in list(run.get("run_results", [])):
        status = str(result.get("status") or "")
        if status in {"failed", "timed_out", "cancelled", "blocked_by_conflict"}:
            count += 1
    return count


def _workflow_has_active_leases(run: Dict[str, Any]) -> bool:
    lease_state = run.get("lease_state") or {}
    return str(lease_state.get("state") or "") == "active" and bool(lease_state.get("leases"))


def _workflow_has_scheduler_queue_state(run: Dict[str, Any]) -> bool:
    return bool(run.get("queue_entries")) or bool(run.get("wait_started_at")) or bool(run.get("blocked_reason"))


def _scheduler_active_leases_locked() -> List[Dict[str, Any]]:
    leases: List[Dict[str, Any]] = []
    for workflow in WORKFLOW_RUNS:
        lease_state = workflow.get("lease_state") or {}
        if str(lease_state.get("state") or "") != "active":
            continue
        for lease in list(lease_state.get("leases", [])):
            item = dict(lease)
            item.setdefault("run_id", workflow.get("id"))
            item.setdefault("workflow_id", workflow.get("workflow_id"))
            item.setdefault("workflow_label", workflow.get("label"))
            leases.append(item)
    return sorted(leases, key=lambda item: (str(item.get("resource_id")), float(item.get("acquired_at") or 0.0)))


def _scheduler_queued_runs_locked() -> List[Dict[str, Any]]:
    queued = [run for run in WORKFLOW_RUNS if str(run.get("status") or "") == "queued"]
    return sorted(queued, key=lambda item: float(item.get("wait_started_at") or item.get("started_at") or 0.0))


def _workflow_queue_position_locked(run: Dict[str, Any]) -> Optional[int]:
    if str(run.get("status") or "") != "queued":
        return None
    queued = _scheduler_queued_runs_locked()
    for index, item in enumerate(queued, start=1):
        if item.get("id") == run.get("id"):
            return index
    return None


def _scheduler_blockers_locked(run: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    requirements = [item for item in list(run.get("required_resources", [])) if str(item.get("mode") or "") == "exclusive"]
    run_id = str(run.get("id") or "")
    wait_started_at = float(run.get("wait_started_at") or run.get("started_at") or time.time())
    active_leases = _scheduler_active_leases_locked()
    queued = _scheduler_queued_runs_locked()
    for requirement in requirements:
        resource_id = str(requirement.get("id") or "")
        owner = next((lease for lease in active_leases if str(lease.get("resource_id")) == resource_id and str(lease.get("run_id")) != run_id), None)
        if owner is not None:
            blockers.append(f"{resource_id} is leased by {owner.get('workflow_label') or owner.get('run_id')}")
            continue
        older_waiting = next(
            (
                queued_run for queued_run in queued
                if str(queued_run.get("id") or "") != run_id
                and float(queued_run.get("wait_started_at") or queued_run.get("started_at") or 0.0) <= wait_started_at
                and any(str(item.get("id") or "") == resource_id and str(item.get("mode") or "") == "exclusive" for item in list(queued_run.get("required_resources", [])))
            ),
            None,
        )
        if older_waiting is not None:
            blockers.append(f"{resource_id} is reserved by older queued workflow {older_waiting.get('label')}")
    return blockers


def _queue_entries_for_workflow(run: Dict[str, Any], blockers: List[str]) -> List[Dict[str, Any]]:
    now = time.time()
    items: List[Dict[str, Any]] = []
    for requirement in list(run.get("required_resources", [])):
        if str(requirement.get("mode") or "") != "exclusive":
            continue
        resource_id = str(requirement.get("id") or "")
        resource_blockers = [item for item in blockers if resource_id in item]
        if not resource_blockers:
            continue
        items.append(
            {
                "id": f"{run.get('id')}:{resource_id}",
                "run_id": run.get("id"),
                "workflow_id": run.get("workflow_id"),
                "workflow_label": run.get("label"),
                "resource_id": resource_id,
                "resource_mode": requirement.get("mode"),
                "queued_at": now,
                "reason": "; ".join(resource_blockers),
                "state": "queued",
            }
        )
    return items


def _set_workflow_queued_locked(run: Dict[str, Any], blockers: List[str]) -> None:
    now = time.time()
    if not run.get("wait_started_at"):
        run["wait_started_at"] = now
    run["queue_timeout_s"] = int(run.get("queue_timeout_s") or WORKFLOW_QUEUE_TIMEOUT_S)
    run["status"] = "queued"
    run["blocked_reason"] = "; ".join(blockers)
    run["queue_entries"] = _queue_entries_for_workflow(run, blockers)
    run["queue_position"] = _workflow_queue_position_locked(run) or 1
    run["updated_at"] = now
    run.setdefault("events", []).append(
        {
            "timestamp": now,
            "stage": "act",
            "kind": "queued",
            "agent_id": "orchestrator",
            "content": run["blocked_reason"],
            "metadata": {"queue_position": run["queue_position"], "required_resources": list(run.get("required_resources", []))},
        }
    )


def _clear_workflow_queue_locked(run: Dict[str, Any]) -> None:
    run["queue_entries"] = []
    run["queue_position"] = None
    run["blocked_reason"] = ""


def _acquire_workflow_leases_locked(run: Dict[str, Any]) -> None:
    now = time.time()
    effective_duration = int(run.get("effective_duration_s") or run.get("duration_s") or DEFAULT_WORKFLOW_DURATION_S)
    lease_timeout_s = int(run.get("lease_timeout_s") or (effective_duration + WORKFLOW_LEASE_TIMEOUT_GRACE_S))
    leases: List[Dict[str, Any]] = []
    for requirement in list(run.get("required_resources", [])):
        leases.append(
            {
                "resource_id": requirement.get("id"),
                "mode": requirement.get("mode"),
                "scope": requirement.get("scope"),
                "owner_run_id": run.get("id"),
                "acquired_at": now,
                "heartbeat_at": now,
                "timeout_at": now + lease_timeout_s,
            }
        )
    run["lease_state"] = {
        "state": "active",
        "leases": leases,
        "released_at": None,
        "release_reason": "",
    }
    run["lease_acquired_at"] = now
    run["admitted_at"] = now
    run["status"] = "admitted"
    run["execution_started_at"] = now
    run["execution_deadline_at"] = now + effective_duration
    _clear_workflow_queue_locked(run)


def _release_workflow_leases_locked(run: Dict[str, Any], reason: str) -> None:
    lease_state = run.setdefault("lease_state", {"state": "none", "leases": []})
    if str(lease_state.get("state") or "") != "active":
        return
    now = time.time()
    for lease in list(lease_state.get("leases", [])):
        lease["released_at"] = now
        lease["release_reason"] = reason
    lease_state["state"] = "released"
    lease_state["released_at"] = now
    lease_state["release_reason"] = reason
    run["updated_at"] = now


def _workflow_terminal_status_locked(run: Dict[str, Any]) -> str:
    if str(run.get("status") or "") in {"cancelled", "expired"}:
        return str(run.get("status"))
    return "completed_with_issues" if _workflow_issue_count(run) else "completed"


def _launch_scheduled_actions_locked(workflow: Dict[str, Any], *, manual: bool = False) -> Dict[str, Any]:
    toolbox = _portal_toolbox_locked()
    events = workflow.setdefault("events", [])
    errors = list(workflow.get("errors", []))
    run_results = list(workflow.get("run_results", []))
    selected_actions = list(workflow.get("selected_actions", []))
    launched = 0
    for item in selected_actions:
        agent_id = str(item.get("agent_id") or "unknown")
        action_id = str(item.get("action_id") or "unknown")
        label = str(item.get("label") or action_id)
        existing_real = next((existing for existing in run_results if str(existing.get("agent_id")) == agent_id and str(existing.get("action_id")) == action_id and (existing.get("id") or existing.get("run_id")) and str(existing.get("status") or "") in {"launching", "starting", "running", "completed", "exited", "success", "blocked_by_conflict", "failed", "timed_out", "cancelled"}), None)
        if existing_real is not None:
            continue
        run_results = [existing for existing in run_results if not (str(existing.get("agent_id")) == agent_id and str(existing.get("action_id")) == action_id and str(existing.get("status") or "") in {"queued", "blocked_by_conflict"} and not (existing.get("id") or existing.get("run_id")))]
        try:
            launched_run = _run_action_public_locked(agent_id, action_id)
            launched_run.setdefault("agent_id", agent_id)
            launched_run.setdefault("action_id", action_id)
            launched_run.setdefault("label", label)
            launched_run["status"] = launched_run.get("status") or "running"
            run_results.append(dict(launched_run))
            launched += 1
            _record_message("orchestrator", agent_id, f"Scheduler admitted workflow '{workflow.get('label', workflow.get('workflow_id', 'workflow'))}' and launched {label}.", "scheduler-handoff")
            events.append(
                toolbox.event("act", "action-launched", f"Launched {label} for {agent_id}.", agent_id=agent_id, metadata={"action_id": action_id, "run": dict(launched_run), "manual": manual}) if toolbox is not None else {
                    "timestamp": time.time(), "stage": "act", "kind": "action-launched", "agent_id": agent_id, "content": f"Launched {label} for {agent_id}.", "metadata": {"action_id": action_id, "run": dict(launched_run), "manual": manual},
                }
            )
        except Exception as exc:
            detail = str(exc)
            errors.append(detail)
            blocked = {
                "id": f"blocked:{workflow.get('id')}:{agent_id}:{action_id}", "agent_id": agent_id, "action_id": action_id, "label": label,
                "status": "blocked_by_conflict", "detail": detail, "started_at": time.time(), "ended_at": time.time(), "manual": manual,
            }
            run_results.append(blocked)
            events.append(
                toolbox.event("act", "action-blocked", f"Blocked {label} for {agent_id}: {detail}", agent_id=agent_id, metadata={"action_id": action_id, "manual": manual}) if toolbox is not None else {
                    "timestamp": time.time(), "stage": "act", "kind": "action-blocked", "agent_id": agent_id, "content": f"Blocked {label} for {agent_id}: {detail}", "metadata": {"action_id": action_id, "manual": manual},
                }
            )
    workflow["run_results"] = run_results
    workflow["errors"] = errors
    if launched:
        workflow["status"] = "running"
    else:
        workflow["status"] = _workflow_terminal_status_locked(workflow)
        workflow["completed_at"] = workflow.get("completed_at") or time.time()
        _release_workflow_leases_locked(workflow, "No runnable actions were launched.")
    workflow["updated_at"] = time.time()
    _synchronize_graph_workflow_locked(workflow)
    return workflow


def _scheduler_submit_workflow_locked(workflow: Dict[str, Any], *, manual: bool = False) -> Dict[str, Any]:
    blockers = _scheduler_blockers_locked(workflow)
    if blockers:
        _set_workflow_queued_locked(workflow, blockers)
        _synchronize_graph_workflow_locked(workflow)
        _persist_workflow_run_locked(workflow)
        return workflow
    _acquire_workflow_leases_locked(workflow)
    events = workflow.setdefault("events", [])
    events.append({
        "timestamp": time.time(),
        "stage": "act",
        "kind": "admitted",
        "agent_id": "orchestrator",
        "content": "Workflow acquired the required resources and was admitted by the scheduler.",
        "metadata": {"required_resources": list(workflow.get("required_resources", [])), "manual": manual},
    })
    workflow["events"] = events
    return _launch_scheduled_actions_locked(workflow, manual=manual)


def _refresh_scheduler_heartbeats_locked() -> None:
    now = time.time()
    for workflow in WORKFLOW_RUNS:
        lease_state = workflow.get("lease_state") or {}
        if str(lease_state.get("state") or "") != "active":
            continue
        for lease in list(lease_state.get("leases", [])):
            lease["heartbeat_at"] = now


def _promote_queued_workflows_locked() -> None:
    for workflow in _scheduler_queued_runs_locked():
        if str(workflow.get("status") or "") != "queued":
            continue
        if not _workflow_has_scheduler_queue_state(workflow):
            continue
        if _scheduler_blockers_locked(workflow):
            workflow["queue_position"] = _workflow_queue_position_locked(workflow)
            continue
        _scheduler_submit_workflow_locked(workflow, manual=False)


def _expire_queued_workflows_locked() -> None:
    now = time.time()
    for workflow in WORKFLOW_RUNS:
        if str(workflow.get("status") or "") != "queued":
            continue
        if not _workflow_has_scheduler_queue_state(workflow):
            continue
        wait_started_at = float(workflow.get("wait_started_at") or workflow.get("started_at") or now)
        queue_timeout_s = int(workflow.get("queue_timeout_s") or WORKFLOW_QUEUE_TIMEOUT_S)
        if now - wait_started_at < queue_timeout_s:
            continue
        workflow["status"] = "expired"
        workflow["completed_at"] = now
        workflow["updated_at"] = now
        workflow.setdefault("errors", []).append(f"Workflow queue wait exceeded {queue_timeout_s}s.")
        workflow.setdefault("events", []).append({
            "timestamp": now,
            "stage": "act",
            "kind": "expired",
            "agent_id": "orchestrator",
            "content": f"Workflow queue wait exceeded {queue_timeout_s}s.",
            "metadata": {},
        })
        _clear_workflow_queue_locked(workflow)
        _persist_workflow_run_locked(workflow)


def _cancel_or_drain_workflow_locked(workflow: Dict[str, Any], *, mode: str, actor: str = "operator") -> Dict[str, Any]:
    now = time.time()
    if mode not in {"cancel", "drain"}:
        raise ValueError("Unsupported workflow stop mode")
    stop_reason = "Cancelled by operator." if mode == "cancel" else "Drained by operator."
    for result in list(workflow.get("run_results", [])):
        run_id = result.get("id") or result.get("run_id")
        child = RUNS.get(run_id) if run_id else None
        if child is not None and child.status in {"starting", "running"}:
            _terminate_run_locked(child, stop_reason)
            result.update(child.to_public())
        elif str(result.get("status") or "") == "queued":
            result["status"] = "cancelled"
            result["ended_at"] = now
            result["detail"] = stop_reason
    workflow.setdefault("events", []).append({
        "timestamp": now, "stage": "summarize", "kind": mode, "agent_id": "orchestrator", "content": stop_reason, "metadata": {"actor": actor},
    })
    workflow.setdefault("errors", []).append(stop_reason)
    workflow["status"] = "cancelled" if mode == "cancel" else "completed_with_issues"
    workflow["completed_at"] = now
    workflow["updated_at"] = now
    _clear_workflow_queue_locked(workflow)
    _release_workflow_leases_locked(workflow, stop_reason)
    _synchronize_graph_workflow_locked(workflow)
    _persist_workflow_run_locked(workflow)
    _record_operator_action_locked(workflow.get("id"), mode, actor, stop_reason)
    return workflow


def _reconcile_scheduler_locked() -> Dict[str, Any]:
    now = time.time()
    released = 0
    expired = 0
    for workflow in WORKFLOW_RUNS:
        if str(workflow.get("status") or "") == "queued":
            wait_started_at = float(workflow.get("wait_started_at") or workflow.get("started_at") or now)
            queue_timeout_s = int(workflow.get("queue_timeout_s") or WORKFLOW_QUEUE_TIMEOUT_S)
            if now - wait_started_at >= queue_timeout_s:
                workflow["status"] = "expired"
                workflow["completed_at"] = now
                workflow["updated_at"] = now
                workflow.setdefault("errors", []).append(f"Workflow queue wait exceeded {queue_timeout_s}s.")
                _clear_workflow_queue_locked(workflow)
                _persist_workflow_run_locked(workflow)
                expired += 1
        if _workflow_has_active_leases(workflow) and str(workflow.get("status") or "") in {"completed", "completed_with_issues", "cancelled", "expired"}:
            _release_workflow_leases_locked(workflow, "Lease reconciled after terminal workflow state.")
            _persist_workflow_run_locked(workflow)
            released += 1
    _promote_queued_workflows_locked()
    return {"status": "success", "released_leases": released, "expired_workflows": expired, "scheduler": _scheduler_payload_locked()}


def _scheduler_payload_locked() -> Dict[str, Any]:
    active_leases = _scheduler_active_leases_locked()
    queued_runs = _scheduler_queued_runs_locked()
    blocked_reasons = [str(run.get("blocked_reason") or "") for run in queued_runs if run.get("blocked_reason")]
    return {
        "active_lease_count": len(active_leases),
        "queued_workflow_count": len(queued_runs),
        "leases": active_leases,
        "queues": [{
            "run_id": run.get("id"),
            "workflow_id": run.get("workflow_id"),
            "label": run.get("label"),
            "mode": run.get("mode"),
            "queue_position": _workflow_queue_position_locked(run),
            "blocked_reason": run.get("blocked_reason"),
            "wait_started_at": run.get("wait_started_at"),
            "required_resources": list(run.get("required_resources", [])),
        } for run in queued_runs],
        "safe_for_enforced": not queued_runs and not any(lease.get("mode") == "exclusive" for lease in active_leases),
        "blocked_reasons": blocked_reasons[:10],
        "leases_endpoint": "/api/runtime/leases",
        "queues_endpoint": "/api/runtime/queues",
    }


def _runtime_safety_locked() -> Dict[str, Any]:
    services = _service_health()
    essential_ids = {"portal", "rpc", "kpm_bus"}
    essential = [service for service in services if service.get("id") in essential_ids]
    optional = [service for service in services if service.get("id") not in essential_ids]
    active_actions = [run.to_public() for run in RUNS.values() if run.status in {"starting", "running"}]
    scheduler = _scheduler_payload_locked()
    active_workflows = [
        {
            "id": workflow.get("id"),
            "label": workflow.get("label"),
            "status": workflow.get("status"),
            "mode": workflow.get("mode"),
        }
        for workflow in WORKFLOW_RUNS
        if str(workflow.get("status") or "") in {"queued", "admitted", "running", "waiting_for_approval"}
    ]
    blockers: List[str] = []
    warnings: List[str] = []
    not_ready_essential = [service for service in essential if not service.get("ok")]
    if not_ready_essential:
        blockers.append(
            "Core services are not fully ready: "
            + ", ".join(service.get("label", service.get("id", "service")) for service in not_ready_essential)
            + "."
        )
    if scheduler.get("active_lease_count"):
        blockers.append(f"{scheduler.get('active_lease_count')} resource lease(s) are still active.")
    if scheduler.get("queued_workflow_count"):
        warnings.append(f"{scheduler.get('queued_workflow_count')} workflow(s) are waiting in the scheduler queue.")
    if active_actions:
        warnings.append(
            "Active local action runs: "
            + ", ".join(f"{item['agent_id']}:{item['action_id']}" for item in active_actions[:6])
            + ("." if len(active_actions) <= 6 else ", ...")
        )
    mcp_service = next((service for service in optional if service.get("id") == "mcp"), None)
    if mcp_service is not None and not mcp_service.get("ok"):
        warnings.append("MCP is down. Advisory workflows can still run, but telemetry/tool coverage is reduced.")
    if not blockers and not warnings:
        warnings.append("Runtime is clean for the next enforced test run.")

    return {
        "status": "ready" if not blockers else "attention",
        "safe_for_enforced": not blockers,
        "clear_to_test": not active_actions and not scheduler.get("active_lease_count") and not scheduler.get("queued_workflow_count"),
        "blockers": blockers,
        "warnings": warnings,
        "active_action_count": len(active_actions),
        "active_workflow_count": len(active_workflows),
        "active_actions": active_actions[:10],
        "active_workflows": active_workflows[:10],
        "essential_service_count": len(essential),
        "essential_ready_count": sum(1 for service in essential if service.get("ok")),
        "recommended_windows": {workflow_id: _workflow_recommended_duration_s(workflow_id) for workflow_id in WORKFLOW_TEMPLATES.keys()},
        "scheduler": scheduler,
        "reset_endpoint": "/api/runtime/reset",
        "reset_label": "Emergency Reset",
    }



def _reset_runtime_locked(clear_saved_workflows: bool = False) -> Dict[str, Any]:
    stopped_runs = 0
    for run in list(RUNS.values()):
        if run.status in {"starting", "running"}:
            _terminate_run_locked(run, "Portal runtime reset requested.")
            stopped_runs += 1
    RUNS.clear()
    TASKS.clear()
    MESSAGES.clear()
    WORKFLOW_RUNS.clear()
    AGENTS.clear()
    AGENTS.update(build_agents(sys.executable, THIS_DIR) if build_agents is not None else {})
    _clear_persisted_workflow_runs_locked()
    if clear_saved_workflows:
        _clear_saved_workflows_locked()
    return {
        "status": "success",
        "detail": "Runtime state was reset to a clean baseline.",
        "stopped_run_count": stopped_runs,
        "cleared": {
            "runs": True,
            "tasks": True,
            "messages": True,
            "workflow_runs": True,
            "saved_workflows": bool(clear_saved_workflows),
        },
        "safety": _runtime_safety_locked(),
    }


def _multi_agent_summary() -> Dict[str, Any]:
    runs = sorted(WORKFLOW_RUNS, key=lambda item: item["started_at"], reverse=True)
    latest_workflow = runs[0] if runs else None
    recent_messages = list(reversed(MESSAGES[-10:]))
    active_runs = [run for run in RUNS.values() if run.status in {"starting", "running"}]
    agents_with_actions = [agent.id for agent in AGENTS.values() if agent.actions]
    agents_with_runs = sorted({run.agent_id for run in RUNS.values()})
    services = _service_health()
    ready_services = sum(1 for service in services if service["ok"])
    scheduler = _scheduler_payload_locked()

    return {
        "status": "ready" if ready_services == len(services) else "warning",
        "service_count": len(services),
        "ready_service_count": ready_services,
        "workflow_run_count": len(WORKFLOW_RUNS),
        "message_count": len(MESSAGES),
        "task_count": len(TASKS),
        "active_run_count": len(active_runs),
        "agents_with_actions": agents_with_actions,
        "agents_with_runs": agents_with_runs,
        "graph_backend": (latest_workflow or {}).get("graph_backend", graph_backend_name()),
        "scheduler": scheduler,
        "latest_workflow": latest_workflow,
        "latest_workflow_events": list((latest_workflow or {}).get("events", [])[-12:]),
        "recent_messages": recent_messages,
        "services": services,
    }


def _terminate_run_locked(run: RunState, reason: str) -> None:
    if run.proc is not None and run.status in {"starting", "running"}:
        try:
            os.killpg(run.proc.pid, 15)
        except Exception:
            try:
                run.proc.terminate()
            except Exception:
                pass
        try:
            run.proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(run.proc.pid, 9)
            except Exception:
                try:
                    run.proc.kill()
                except Exception:
                    pass
            try:
                run.proc.wait(timeout=2)
            except Exception:
                pass
    if run.returncode is None:
        try:
            run.returncode = run.proc.returncode if run.proc is not None else -15
        except Exception:
            run.returncode = -15
    run.ended_at = time.time()
    run.termination_reason = reason
    if "execution window" in reason:
        run.status = "timed_out"
    elif "operator" in reason.lower():
        run.status = "cancelled"
    else:
        run.status = "failed"
    run.detail = _summarize_run_failure(run)
    agent = AGENTS.get(run.agent_id)
    if agent is not None:
        agent.status = "warning"
        agent.activity = f"Action '{run.label}' stopped: {reason}"
        agent.timeline.insert(0, _timeline(f"Stopped action {run.action_id}: {reason}"))


def _workflow_execution_started_at(workflow: Dict[str, Any]) -> float:
    value = workflow.get("execution_started_at")
    return float(value) if value is not None else 0.0



def _expire_workflow_locked(workflow: Dict[str, Any]) -> None:
    if str(workflow.get("status") or "") not in {"admitted", "running"}:
        return
    execution_started_at = _workflow_execution_started_at(workflow)
    if execution_started_at <= 0:
        return
    duration_s = _normalize_workflow_duration_s(workflow.get("effective_duration_s") or workflow.get("duration_s"))
    workflow["effective_duration_s"] = duration_s
    workflow["duration_s"] = duration_s
    deadline = float(workflow.get("execution_deadline_at") or (execution_started_at + duration_s))
    workflow["execution_deadline_at"] = deadline
    if time.time() <= deadline:
        return

    reason = f"Workflow execution exceeded its {duration_s}s execution window."
    now = time.time()
    timed_out_any = False
    for step in workflow.get("steps", []):
        if step.get("status") != "running":
            continue
        run_id = step.get("run_id")
        child = RUNS.get(run_id) if run_id else None
        if child is not None and child.status not in {"starting", "running"}:
            step["run_status"] = child.status
            step["returncode"] = child.returncode
            step["detail"] = child.detail
            step["ended_at"] = child.ended_at or now
            if child.status == "exited":
                step["status"] = "completed"
                step.pop("error", None)
            else:
                step["status"] = "failed"
                step["error"] = child.detail or reason
            continue
        if child is not None:
            _terminate_run_locked(child, reason)
            step["run_status"] = child.status
            step["returncode"] = child.returncode
            step["detail"] = child.detail or reason
        else:
            step["run_status"] = "timed_out"
            step["returncode"] = -15
            step["detail"] = reason
        step["status"] = "failed"
        step["error"] = step.get("detail") or reason
        step["ended_at"] = now
        timed_out_any = True

    if not timed_out_any:
        return

    errors = workflow.setdefault("errors", [])
    if reason not in errors:
        errors.append(reason)
    workflow["timed_out"] = True
    workflow["status"] = "completed_with_issues"
    workflow["completed_at"] = now
    workflow["updated_at"] = now
    _release_workflow_leases_locked(workflow, reason)



def _poll_runs_locked() -> None:
    for run in RUNS.values():
        if run.proc is None or run.status not in {"starting", "running"}:
            continue
        rc = run.proc.poll()
        if rc is None:
            run.status = "running"
            continue
        run.returncode = rc
        run.ended_at = time.time()
        run.status = "exited" if rc == 0 else (run.status if run.status == "timed_out" else "failed")
        run.detail = "Completed successfully." if rc == 0 else _summarize_run_failure(run)
        agent = AGENTS.get(run.agent_id)
        if agent:
            agent.status = "ready" if rc == 0 else "warning"
            agent.activity = f"Last action '{run.label}' finished with status={run.status}."
            timeline_note = f"Completed action {run.action_id} rc={rc}" if rc == 0 else f"Action {run.action_id} ended: {run.detail}"
            agent.timeline.insert(0, _timeline(timeline_note))


def _default_workflow_action(agent: AgentCard, workflow_id: str) -> Optional[AgentAction]:
    preferred = WORKFLOW_ACTIONS.get(workflow_id, {}).get(agent.id)
    if preferred:
        for action in agent.actions:
            if action.id == preferred:
                return action
    return agent.actions[0] if agent.actions else None


def _begin_workflow_step_locked(run: Dict[str, Any], idx: int) -> bool:
    step = run["steps"][idx]
    if step["status"] != "pending":
        return step["status"] in {"running", "failed"}

    agent_id = step["agent_id"]
    agent = AGENTS[agent_id]

    if idx == 0:
        message = f"Goal received: {run['goal']}"
    else:
        prev = run["steps"][idx - 1]["agent_id"]
        message = f"Handoff from {prev} to {agent_id} for workflow '{run['label']}'"
        _record_message(prev, agent_id, message, "workflow-handoff")

    step["message"] = message
    step["started_at"] = time.time()
    agent.status = "active"
    agent.activity = message
    agent.timeline.insert(0, _timeline(message))

    action = _default_workflow_action(agent, run["workflow_id"])
    if action is None:
        step["status"] = "completed"
        step["ended_at"] = time.time()
        agent.status = "ready"
        if idx == len(run["steps"]) - 1:
            agent.activity = "Workflow chain reached final validation stage."
        return False

    try:
        launched = _run_action_locked(agent, action)
        step["status"] = "running"
        step["action_id"] = action.id
        step["action_label"] = action.label
        step["run_id"] = launched.id
        step["run_status"] = launched.status
        return True
    except Exception as exc:
        step["status"] = "failed"
        step["detail"] = str(exc)
        step["error"] = str(exc)
        step["ended_at"] = time.time()
        agent.status = "warning"
        agent.activity = f"Workflow action launch failed: {action.label}"
        agent.timeline.insert(0, _timeline(f"Workflow action {action.id} failed to launch: {exc}"))
        run["status"] = "completed"
        run["completed_at"] = step["ended_at"]
        return True


def _advance_workflow_locked(run: Dict[str, Any]) -> None:
    if run.get("status") == "completed":
        return

    while True:
        running = next((step for step in run["steps"] if step["status"] == "running"), None)
        if running is not None:
            run["status"] = "running"
            return

        pending_idx = next((idx for idx, step in enumerate(run["steps"]) if step["status"] == "pending"), None)
        if pending_idx is None:
            run["status"] = "completed"
            run["completed_at"] = run.get("completed_at") or time.time()
            return

        should_wait = _begin_workflow_step_locked(run, pending_idx)
        if should_wait:
            return


def _poll_workflows_locked() -> None:
    _expire_queued_workflows_locked()
    _refresh_scheduler_heartbeats_locked()
    for workflow in WORKFLOW_RUNS:
        _expire_workflow_locked(workflow)
        if isinstance(workflow.get("run_results"), list):
            _refresh_graph_workflow_locked(workflow)
        workflow["completed_step_count"] = sum(1 for step in workflow.get("steps", []) if step.get("status") == "completed")
        workflow["active_run_count"] = sum(
            1 for result in list(workflow.get("run_results", []))
            if str(result.get("status") or "") in {"starting", "running", "launching"}
        )
        workflow["action_run_count"] = len(list(workflow.get("run_results", [])))
        workflow["queue_position"] = _workflow_queue_position_locked(workflow)
        if workflow.get("status") in {"completed", "completed_with_issues", "cancelled", "expired"}:
            _release_workflow_leases_locked(workflow, f"Workflow reached terminal state {workflow.get('status')}.")
            workflow["completed_at"] = workflow.get("completed_at") or time.time()
        _persist_workflow_run_locked(workflow)
    _promote_queued_workflows_locked()



def _tail_lines(path: str, lines: int = 20) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    data = p.read_text(errors="replace").splitlines()
    return data[-max(1, lines):]


def _agent_tasks(agent_id: str, limit: int = 10) -> List[TaskState]:
    tasks = [task for task in TASKS if task.agent_id == agent_id]
    return sorted(tasks, key=lambda item: item.started_at, reverse=True)[:limit]


def _agent_payload(agent: AgentCard) -> Dict[str, Any]:
    payload = asdict(agent)
    payload["actions"] = [asdict(action) for action in agent.actions]
    payload["latest_run"] = None
    payload["latest_task"] = None
    runs = [run for run in RUNS.values() if run.agent_id == agent.id]
    if runs:
        latest = sorted(runs, key=lambda item: item.started_at, reverse=True)[0]
        payload["latest_run"] = latest.to_public()
        payload["latest_run"]["tail"] = _tail_lines(latest.log_path)
    tasks = _agent_tasks(agent.id, limit=5)
    payload["tasks"] = [task.to_public() for task in tasks]
    if tasks:
        payload["latest_task"] = tasks[0].to_public()
    payload["runtime_scope"] = _agent_runtime_scope_locked(agent)
    return payload


def _overview_payload() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return {
            "title": "FlexRIC Agent Portal",
            "providers": _provider_statuses(),
            "agents": [_agent_payload(agent) for agent in AGENTS.values()],
            "workflow_templates": WORKFLOW_TEMPLATES,
            "messages": list(reversed(MESSAGES[-30:])),
            "runs": [run.to_public() for run in sorted(RUNS.values(), key=lambda item: item.started_at, reverse=True)[:20]],
            "tasks": [task.to_public() for task in sorted(TASKS, key=lambda item: item.started_at, reverse=True)[:20]],
            "multi_agent": _multi_agent_summary(),
            "runtime_safety": _runtime_safety_locked(),
            "scheduler": _scheduler_payload_locked(),
            "scheduler_history": {
                "operator_actions": _recent_operator_actions_locked(),
                "implementation_changes": _recent_change_log_locked(),
            },
            "platform": _platform_payload_locked(),
            "saved_workflows": _saved_workflows_locked(),
        }


def _record_message(source_id: str, target_id: str, content: str, kind: str) -> Dict[str, Any]:
    source = AGENTS[source_id]
    target = AGENTS[target_id]
    msg = {
        "id": uuid.uuid4().hex,
        "timestamp": time.time(),
        "source_id": source_id,
        "target_id": target_id,
        "kind": kind,
        "content": content,
    }
    MESSAGES.append(msg)
    source.activity = f"Sent {kind} message to {target.name}."
    target.activity = f"Received {kind} message from {source.name}."
    source.timeline.insert(0, _timeline(f"Sent {kind} to {target_id}: {content}"))
    target.timeline.insert(0, _timeline(f"Received {kind} from {source_id}: {content}"))
    return msg


def _agent_context(agent: AgentCard) -> str:
    task = _agent_tasks(agent.id, limit=1)
    latest_task = task[0].response if task else "None"
    latest_messages = [
        msg for msg in reversed(MESSAGES)
        if msg["source_id"] == agent.id or msg["target_id"] == agent.id
    ][:4]
    lines = [
        f"Agent: {agent.name}",
        f"Role: {agent.role}",
        f"Service model: {agent.service_model}",
        f"Activity: {agent.activity}",
        f"Skills: {', '.join(agent.skills)}",
        f"Measurements: {', '.join(agent.measurements)}",
        f"Use cases: {', '.join(agent.use_cases)}",
        f"Peers: {', '.join(agent.peers)}",
        f"Recent timeline: {' | '.join(agent.timeline[:4]) or 'None'}",
        f"Recent task output: {latest_task[:1000]}",
    ]
    if latest_messages:
        lines.append(
            "Recent messages: "
            + " | ".join(
                f"{msg['source_id']}->{msg['target_id']}:{msg['content']}"
                for msg in latest_messages
            )
        )
    return "\n".join(lines)


def _enabled_provider(provider_hint: str) -> Dict[str, Any]:
    providers = _provider_statuses()
    if provider_hint != "auto":
        for provider in providers:
            if provider["id"] == provider_hint:
                if not provider["enabled"]:
                    raise HTTPException(status_code=400, detail=f"Provider {provider_hint} is not configured")
                return provider
        raise HTTPException(status_code=404, detail=f"Unknown provider {provider_hint}")

    for provider in providers:
        if provider["enabled"]:
            return provider
    raise HTTPException(status_code=400, detail="No LLM provider is configured. Set Ollama or OpenAI env vars first.")


def _invoke_provider(provider: Dict[str, Any], agent: AgentCard, prompt: str) -> str:
    system = (
        "You are a FlexRIC service-model agent. Reply concisely with a practical network-automation answer, "
        "including observations, risks, and the next best action."
    )
    context = _agent_context(agent)
    full_prompt = f"{context}\n\nUser task:\n{prompt}"
    timeout_s = int(os.getenv("FLEXRIC_AGENT_PROVIDER_TIMEOUT", "90"))

    if provider["id"] == "ollama":
        response = requests.post(
            f"{provider['endpoint'].rstrip('/')}/api/generate",
            json={
                "model": provider["model"],
                "system": system,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=timeout_s,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "").strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response")
        return text

    if provider["id"] == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        response = requests.post(
            f"{provider['endpoint'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_prompt},
                ],
            },
            timeout=timeout_s,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        if not text:
            raise RuntimeError("OpenAI-compatible endpoint returned an empty response")
        return text

    raise RuntimeError(f"Unsupported provider: {provider['id']}")


def _run_task_locked(agent: AgentCard, provider_hint: str, prompt: str) -> TaskState:
    provider = _enabled_provider(provider_hint)
    task = TaskState(
        id=uuid.uuid4().hex,
        agent_id=agent.id,
        provider_id=provider["id"],
        prompt=prompt,
        status="running",
        started_at=time.time(),
    )
    TASKS.append(task)
    agent.status = "active"
    agent.activity = f"Thinking with {provider['label']}."
    agent.timeline.insert(0, _timeline(f"Started LLM task via {provider['id']}"))

    try:
        task.response = _invoke_provider(provider, agent, prompt)
        task.status = "completed"
        agent.status = "ready"
        agent.activity = f"Completed LLM task via {provider['label']}."
        agent.timeline.insert(0, _timeline(f"Completed LLM task via {provider['id']}"))
    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)
        agent.status = "warning"
        agent.activity = f"LLM task failed via {provider['label']}."
        agent.timeline.insert(0, _timeline(f"LLM task failed via {provider['id']}: {exc}"))
    finally:
        task.ended_at = time.time()
    return task


def _run_action_locked(agent: AgentCard, action: AgentAction) -> RunState:
    if not action.command:
        raise HTTPException(status_code=400, detail=f"Action {action.id} does not launch a local suite")

    active = next((item for item in RUNS.values() if item.agent_id == agent.id and item.status in {"starting", "running"}), None)
    if active is not None:
        raise RuntimeError(
            f"Agent {agent.id} already has an active action ({active.action_id}, run {active.id[:8]}). Wait for it to finish before launching another one."
        )

    run_id = uuid.uuid4().hex
    log_path = RUN_LOG_DIR / f"{agent.id}-{action.id}-{run_id}.log"
    logf = open(log_path, "ab", buffering=0)
    proc = subprocess.Popen(
        action.command,
        cwd=str(THIS_DIR),
        stdout=logf,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    run = RunState(
        id=run_id,
        agent_id=agent.id,
        action_id=action.id,
        label=action.label,
        cmd=action.command,
        cwd=str(THIS_DIR),
        log_path=str(log_path),
        started_at=time.time(),
        status="running",
        pid=proc.pid,
        proc=proc,
    )
    RUNS[run.id] = run
    agent.status = "running"
    agent.activity = f"Running action '{action.label}'."
    agent.timeline.insert(0, _timeline(f"Started action {action.id} pid={proc.pid}"))
    return run



def _run_action_public_locked(agent_id: str, action_id: str) -> Dict[str, Any]:
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent {agent_id}")
    for action in agent.actions:
        if action.id == action_id:
            return _run_action_locked(agent, action).to_public()
    raise HTTPException(status_code=404, detail=f"Unknown action {action_id} for {agent_id}")


def _run_task_public_locked(agent_id: str, prompt: str, provider: str = "auto") -> Dict[str, Any]:
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent {agent_id}")
    return _run_task_locked(agent, provider, prompt).to_public()


def _workflow_run_by_id(run_id: str) -> Dict[str, Any]:
    for run in WORKFLOW_RUNS:
        if run["id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail="Unknown workflow run")


def _workflow_events_by_id(run_id: str) -> List[Dict[str, Any]]:
    run = _workflow_run_by_id(run_id)
    return list(run.get("events", []))


def _portal_toolbox_locked() -> Optional[PortalToolbox]:
    if PortalToolbox is None:
        return None
    return PortalToolbox(
        get_agent=lambda agent_id: _agent_payload(AGENTS[agent_id]),
        list_agents=lambda: [_agent_payload(agent) for agent in AGENTS.values()],
        service_health=_service_health,
        record_message=_record_message,
        launch_action=_run_action_public_locked,
        run_task=_run_task_public_locked,
        metadata={"backend": graph_backend_name()},
    )


def _workflow_run_from_graph_state(
    workflow_id: str,
    template: Dict[str, Any],
    goal: str,
    mode: str,
    duration_s: int,
    graph_state: Dict[str, Any],
) -> Dict[str, Any]:
    results_by_agent: Dict[str, Dict[str, Any]] = {}
    run_results = [dict(item) for item in graph_state.get("run_results", [])]
    for item in run_results:
        agent_id = item.get("agent_id")
        if agent_id:
            results_by_agent[agent_id] = {
                "action_id": item.get("action_id"),
                "label": item.get("label"),
                "run": item,
            }

    events = list(graph_state.get("events", []))
    steps: List[Dict[str, Any]] = []
    for agent_id in template["steps"]:
        step = {
            "id": agent_id,
            "agent_id": agent_id,
            "status": "completed",
            "message": f"Graph visited {agent_id}.",
        }
        agent_events = [event for event in events if event.get("agent_id") == agent_id]
        if agent_events:
            step["message"] = str(agent_events[-1].get("content") or step["message"])
            step["events"] = agent_events
        result = results_by_agent.get(agent_id)
        if result is not None:
            run = result["run"]
            status = str(run.get("status", "unknown"))
            step.update(
                {
                    "action_id": result.get("action_id"),
                    "action_label": result.get("label"),
                    "run_id": run.get("id"),
                    "run_status": status,
                    "output": f"{agent_id}:{result.get('action_id')} -> {status}",
                }
            )
            if status in {"starting", "running", "launching"}:
                step["status"] = "running"
            elif status in {"queued", "blocked_by_conflict"}:
                step["status"] = "queued"
            elif status in {"exited", "completed", "success"}:
                step["status"] = "completed"
            else:
                step["status"] = "failed"
        steps.append(step)

    selected_actions = list(graph_state.get("selected_actions", []))
    approved = graph_state.get("approved")
    approval_required = bool(selected_actions)
    if selected_actions and mode == "advisory" and approved is not True:
        status = "waiting_for_approval"
    elif selected_actions and approved is True:
        status = "admitted"
    else:
        status = "completed_with_issues" if list(graph_state.get("errors", [])) else "completed"

    now = time.time()
    run = {
        "id": uuid.uuid4().hex,
        "workflow_id": workflow_id,
        "label": template["label"],
        "goal": goal,
        "mode": mode,
        "requested_duration_s": _normalize_workflow_duration_s(duration_s),
        "effective_duration_s": _normalize_workflow_duration_s(duration_s),
        "duration_s": _normalize_workflow_duration_s(duration_s),
        "queue_timeout_s": WORKFLOW_QUEUE_TIMEOUT_S,
        "lease_timeout_s": _normalize_workflow_duration_s(duration_s) + WORKFLOW_LEASE_TIMEOUT_GRACE_S,
        "required_resources": _resource_requirements_for_workflow(workflow_id),
        "lease_state": {"state": "none", "leases": []},
        "queue_entries": [],
        "queue_position": None,
        "blocked_reason": "",
        "wait_started_at": None,
        "lease_acquired_at": None,
        "execution_started_at": None,
        "execution_deadline_at": None,
        "graph_backend": graph_state.get("graph_backend", graph_backend_name()),
        "started_at": now,
        "updated_at": now,
        "status": status,
        "completed_at": now if status in {"completed", "completed_with_issues"} else None,
        "completed_step_count": sum(1 for step in steps if step["status"] == "completed"),
        "active_run_count": sum(1 for step in steps if step["status"] == "running"),
        "action_run_count": sum(1 for step in steps if step.get("run_id")),
        "steps": steps,
        "events": events,
        "summary": graph_state.get("summary", ""),
        "observations": list(graph_state.get("observations", [])),
        "hypotheses": list(graph_state.get("hypotheses", [])),
        "recommendations": list(graph_state.get("recommendations", [])),
        "selected_actions": selected_actions,
        "approval_required": approval_required,
        "approval_reason": graph_state.get("approval_reason", ""),
        "approved": approved,
        "run_results": run_results,
        "verification_notes": list(graph_state.get("verification_notes", [])),
        "errors": list(graph_state.get("errors", [])),
        "scheduler": {"state": status, "queue_position": None, "blocked_reason": ""},
    }
    run["graph_steps"] = _build_graph_steps_payload(run)
    return run


def _a2a_adapter() -> Optional[A2AAdapter]:
    if A2AAdapter is None or A2AHandlers is None:
        return None
    return A2AAdapter(
        A2AHandlers(
            list_agents=lambda: [_agent_payload(agent) for agent in AGENTS.values()],
            get_agent_card=lambda agent_id: _agent_payload(AGENTS[agent_id]),
            send_message=lambda source_id, target_id, content, kind: _record_message(source_id, target_id, content, kind),
            run_workflow=lambda workflow_id, goal, mode: api_workflow_run(workflow_id, WorkflowRequest(goal=goal, mode=mode)),
            get_workflow=lambda run_id: _workflow_run_by_id(run_id),
            get_workflow_events=lambda run_id: _workflow_events_by_id(run_id),
            cancel_workflow=lambda run_id: api_workflow_cancel(run_id),
            queue_status=lambda: api_runtime_queues(),
            scheduler_status=lambda: api_runtime_scheduler(),
            run_task=lambda agent_id, prompt, provider: {"status": "success", "task": _run_task_public_locked(agent_id, prompt, provider)},
            test_all=lambda include_actions, include_messages: api_test_all(
                TestAllRequest(include_actions=include_actions, include_messages=include_messages)
            ),
            backend_name=graph_backend_name,
        )
    )


def _test_all_agents_locked(include_actions: bool, include_messages: bool) -> Dict[str, Any]:
    _poll_runs_locked()
    summary = {
        "id": uuid.uuid4().hex,
        "started_at": time.time(),
        "messages": [],
        "runs": [],
        "simulated": [],
    }

    order = ["orchestrator", "kpm", "mac", "slice", "tc", "rc", "rlc", "pdcp", "gtp"]
    if include_messages:
        for source_id, target_id in zip(order, order[1:]):
            msg = _record_message(
                source_id,
                target_id,
                f"Portal test chain from {source_id} to {target_id}. Review current state and prepare next step.",
                "test-handoff",
            )
            summary["messages"].append(msg)

    for agent_id in order:
        agent = AGENTS[agent_id]
        if include_actions and agent.actions:
            action = agent.actions[0]
            try:
                run = _run_action_locked(agent, action)
                summary["runs"].append(run.to_public())
            except Exception as exc:
                agent.status = "warning"
                agent.timeline.insert(0, _timeline(f"Test-all launch failed for {action.id}: {exc}"))
                summary["simulated"].append({"agent_id": agent_id, "error": str(exc)})
        else:
            agent.status = "ready"
            agent.activity = "Test-all validated this agent card and workflow hooks."
            agent.timeline.insert(0, _timeline("Validated via test-all dry run"))
            summary["simulated"].append({"agent_id": agent_id, "status": "validated"})

    return summary


_init_portal_db()
_record_change_log_locked(
    "workflow-concurrency-v1",
    "Added scheduler-backed workflow queueing, resource leases, targeted cancel/drain controls, and SQLite audit tables.",
    "startup-recorded",
)
WORKFLOW_RUNS.extend(_load_persisted_workflow_runs())


app = FastAPI(
    title="FlexRIC Agent Portal",
    description="Agent-centric orchestration layer for FlexRIC service models, workflows, and A2A-style handoffs.",
)
app.mount("/portal/assets", StaticFiles(directory=str(PORTAL_DIR)), name="portal-assets")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _portal_html()


@app.get("/agents/{agent_id}", response_class=HTMLResponse)
def agent_page(agent_id: str) -> str:
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return _portal_html()


@app.get("/platform", response_class=HTMLResponse)
def platform_page() -> str:
    return _portal_html()


@app.get("/comparison", response_class=HTMLResponse)
def comparison_page() -> str:
    return _portal_html()


@app.get("/scheduler", response_class=HTMLResponse)
def scheduler_page() -> str:
    return _portal_html()


@app.get("/workflows/{run_id}", response_class=HTMLResponse)
def workflow_page(run_id: str) -> str:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        _workflow_run_by_id(run_id)
    return _portal_html()


@app.get("/api/overview")
def api_overview() -> Dict[str, Any]:
    return _overview_payload()


@app.get("/api/providers")
def api_providers() -> List[Dict[str, Any]]:
    return _provider_statuses()


@app.get("/api/stack")
def api_stack() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return _multi_agent_summary()


@app.get("/api/platform")
def api_platform() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return _platform_payload_locked()


@app.post("/api/runtime/reset")
def api_runtime_reset(request: RuntimeResetRequest) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        _record_operator_action_locked(None, "emergency_reset", "operator", "Emergency runtime reset requested from the portal.")
        return _reset_runtime_locked(clear_saved_workflows=request.clear_saved_workflows)


@app.get("/api/runtime/scheduler")
def api_runtime_scheduler() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return _scheduler_payload_locked()


@app.get("/api/runtime/leases")
def api_runtime_leases() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return {"leases": _scheduler_active_leases_locked()}


@app.get("/api/runtime/queues")
def api_runtime_queues() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return {"queues": _scheduler_payload_locked().get("queues", [])}


@app.get("/api/runtime/operator-actions")
def api_runtime_operator_actions() -> Dict[str, Any]:
    with STATE_LOCK:
        return {"actions": _recent_operator_actions_locked()}


@app.get("/api/runtime/change-log")
def api_runtime_change_log() -> Dict[str, Any]:
    with STATE_LOCK:
        return {"changes": _recent_change_log_locked()}


@app.post("/api/runtime/leases/reconcile")
def api_runtime_reconcile_leases() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        _record_operator_action_locked(None, "reconcile_leases", "operator", "Lease reconcile requested from the portal.")
        return _reconcile_scheduler_locked()


@app.post("/api/runtime/mcp/start")
def api_runtime_mcp_start() -> Dict[str, Any]:
    with STATE_LOCK:
        service = _start_mcp_service_locked()
        return {"status": "success" if service.get("ok") else "warning", "service": service}


@app.post("/api/runtime/mcp/stop")
def api_runtime_mcp_stop() -> Dict[str, Any]:
    with STATE_LOCK:
        service = _stop_mcp_service_locked()
        return {"status": "success", "service": service}


@app.get("/api/agents")
def api_agents() -> List[Dict[str, Any]]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return [_agent_payload(agent) for agent in AGENTS.values()]


@app.get("/api/agents/{agent_id}")
def api_agent(agent_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        agent = AGENTS.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Unknown agent")
        return _agent_payload(agent)


@app.get("/api/agents/{agent_id}/figures")
def api_agent_figures(agent_id: str) -> Dict[str, Any]:
    if agent_id != "kpm":
        raise HTTPException(status_code=404, detail="No figure service is wired for this agent yet.")
    with STATE_LOCK:
        _poll_runs_locked()
        agent = AGENTS.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Unknown agent")
    return _kpm_agent_figures_payload()


@app.post("/api/agents/{agent_id}/actions/{action_id}/run")
def api_run_action(agent_id: str, action_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        agent = AGENTS.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Unknown agent")
        for action in agent.actions:
            if action.id == action_id:
                try:
                    run = _run_action_locked(agent, action)
                except RuntimeError as exc:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
                return {"status": "success", "run": run.to_public()}
        raise HTTPException(status_code=404, detail="Unknown action")


@app.post("/api/agents/{agent_id}/tasks/run")
def api_run_task(agent_id: str, request: AgentTaskRequest) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        agent = AGENTS.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Unknown agent")
        task = _run_task_locked(agent, request.provider, request.prompt)
        return {"status": "success" if task.status == "completed" else "failed", "task": task.to_public()}


@app.get("/api/runs")
def api_runs() -> List[Dict[str, Any]]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        runs = [run.to_public() for run in sorted(RUNS.values(), key=lambda item: item.started_at, reverse=True)]
        for run in runs[:]:
            run["tail"] = _tail_lines(run["log_path"])
        return runs


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        run = RUNS.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Unknown run")
        payload = run.to_public()
        payload["tail"] = _tail_lines(run.log_path)
        return payload


@app.get("/api/tasks")
def api_tasks() -> List[Dict[str, Any]]:
    with STATE_LOCK:
        return [task.to_public() for task in sorted(TASKS, key=lambda item: item.started_at, reverse=True)]


@app.post("/api/agents/{agent_id}/message")
def api_agent_message(agent_id: str, request: MessageRequest) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        if agent_id not in AGENTS or request.target_id not in AGENTS:
            raise HTTPException(status_code=404, detail="Unknown agent in handoff")
        message = _record_message(agent_id, request.target_id, request.content, request.kind)
        return {"status": "success", "message": message}


@app.post("/api/test-all")
def api_test_all(request: TestAllRequest) -> Dict[str, Any]:
    with STATE_LOCK:
        result = _test_all_agents_locked(request.include_actions, request.include_messages)
        return {"status": "success", "result": result}


@app.post("/api/workflows/{workflow_id}/run")
def api_workflow_run(workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
    template = WORKFLOW_TEMPLATES.get(workflow_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Unknown workflow")

    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        toolbox = _portal_toolbox_locked()
        mode = request.mode.strip().lower() or "advisory"
        duration_s, duration_note = _apply_workflow_duration_policy(workflow_id, request.duration_s)
        if run_graph_workflow is not None and toolbox is not None:
            graph_state = run_graph_workflow(
                workflow_id=workflow_id,
                workflow_label=template["label"],
                goal=request.goal,
                mode=mode,
                agent_sequence=list(template["steps"]),
                toolbox=toolbox,
            )
            run = _workflow_run_from_graph_state(workflow_id, template, request.goal, mode, duration_s, graph_state)
            if duration_note:
                run.setdefault("errors", []).append(duration_note)
                run["summary"] = f"{run.get('summary', '')} Window={duration_s}s.".strip()
            run["requested_duration_s"] = _normalize_workflow_duration_s(request.duration_s)
            run["effective_duration_s"] = duration_s
            run["duration_s"] = duration_s
            WORKFLOW_RUNS.append(run)
            if mode == "enforced" and run.get("approved") is True and run.get("selected_actions"):
                _scheduler_submit_workflow_locked(run, manual=False)
            else:
                _synchronize_graph_workflow_locked(run)
            _persist_workflow_run_locked(run)
            return {"status": "success", "run": run}

        run = {
            "id": uuid.uuid4().hex,
            "workflow_id": workflow_id,
            "label": template["label"],
            "goal": request.goal,
            "mode": mode,
            "duration_s": duration_s,
            "execution_started_at": time.time(),
            "execution_deadline_at": time.time() + duration_s,
            "graph_backend": graph_backend_name(),
            "started_at": time.time(),
            "status": "running",
            "completed_at": None,
            "completed_step_count": 0,
            "active_run_count": 0,
            "action_run_count": 0,
            "steps": [{"agent_id": agent_id, "status": "pending"} for agent_id in template["steps"]],
        }
        if duration_note:
            run.setdefault("errors", []).append(duration_note)
        _advance_workflow_locked(run)
        _poll_workflows_locked()
        WORKFLOW_RUNS.append(run)
        _persist_workflow_run_locked(run)
        return {"status": "success", "run": run}


@app.get("/api/workflows")
def api_workflows() -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        runs = list(reversed(WORKFLOW_RUNS[-20:]))
    return {
        "templates": WORKFLOW_TEMPLATES,
        "runs": runs,
    }


@app.get("/api/workflows/{run_id}")
def api_workflow_status(run_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        payload = dict(_workflow_run_by_id(run_id))
        payload["runtime_scope"] = _workflow_runtime_scope_locked(payload)
        return payload


@app.get("/api/saved-workflows")
def api_saved_workflows() -> List[Dict[str, Any]]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return _saved_workflows_locked()


@app.post("/api/workflows/{run_id}/save")
def api_workflow_save(run_id: str, request: SavedWorkflowRequest) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        run = _workflow_run_by_id(run_id)
        saved = _save_workflow_record_locked(run, request.name, request.purpose)
        return {"status": "success", "saved_workflow": saved}


@app.post("/api/workflows/{run_id}/approve")
def api_workflow_approve(run_id: str, request: Optional[WorkflowApprovalRequest] = None) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        workflow = _workflow_run_by_id(run_id)
        approved = _approve_graph_workflow_locked(
            workflow,
            request.reason if request is not None else "Manually approved from the portal UI. Execute the selected actions now.",
        )
        return {"status": "success", "run": approved}


@app.post("/api/workflows/{run_id}/cancel")
def api_workflow_cancel(run_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        workflow = _workflow_run_by_id(run_id)
        result = _cancel_or_drain_workflow_locked(workflow, mode="cancel")
        return {"status": "success", "run": result}


@app.post("/api/workflows/{run_id}/drain")
def api_workflow_drain(run_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        workflow = _workflow_run_by_id(run_id)
        result = _cancel_or_drain_workflow_locked(workflow, mode="drain")
        return {"status": "success", "run": result}


@app.get("/api/workflows/{run_id}/events")
def api_workflow_events(run_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        _poll_workflows_locked()
        return {"run_id": run_id, "events": _workflow_events_by_id(run_id)}


@app.get("/.well-known/agent-card.json")
def a2a_orchestrator_card() -> Dict[str, Any]:
    adapter = _a2a_adapter()
    if adapter is not None:
        return adapter.orchestrator_card(_agent_payload(AGENTS["orchestrator"]))
    return {
        "protocol": "A2A-aligned JSON-RPC",
        "agent": _agent_payload(AGENTS["orchestrator"]),
        "methods": [
            "agents.list",
            "agent.get_card",
            "message.send",
            "workflow.run",
            "workflow.status",
            "workflow.events",
            "agent.task.run",
            "portal.test_all",
        ],
    }


@app.get("/.well-known/agents/{agent_id}.json")
def a2a_agent_card(agent_id: str) -> Dict[str, Any]:
    with STATE_LOCK:
        _poll_runs_locked()
        agent = AGENTS.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Unknown agent")
        adapter = _a2a_adapter()
        if adapter is not None:
            return adapter.agent_card(_agent_payload(agent))
        return {
            "protocol": "A2A-aligned JSON-RPC",
            "agent": _agent_payload(agent),
            "methods": ["message.send", "agent.get_card", "agent.task.run"],
        }


@app.post("/api/a2a/rpc")
def api_a2a_rpc(payload: Dict[str, Any]) -> Dict[str, Any]:
    adapter = _a2a_adapter()
    if adapter is not None:
        with STATE_LOCK:
            _poll_runs_locked()
            _poll_workflows_locked()
            return adapter.dispatch(payload)

    method = payload.get("method")
    params = payload.get("params", {})
    req_id = payload.get("id")

    try:
        if method == "agents.list":
            result = [_agent_payload(agent) for agent in AGENTS.values()]
        elif method == "agent.get_card":
            agent_id = params["agent_id"]
            result = _agent_payload(AGENTS[agent_id])
        elif method == "message.send":
            source_id = params["source_id"]
            target_id = params["target_id"]
            content = params["content"]
            kind = params.get("kind", "handoff")
            with STATE_LOCK:
                result = _record_message(source_id, target_id, content, kind)
        elif method == "workflow.run":
            workflow_id = params["workflow_id"]
            goal = params.get("goal", "Run a multi-agent FlexRIC workflow")
            mode = params.get("mode", "advisory")
            result = api_workflow_run(workflow_id, WorkflowRequest(goal=goal, mode=mode))
        elif method == "workflow.status":
            result = api_workflow_status(params["run_id"])
        elif method == "workflow.events":
            result = api_workflow_events(params["run_id"])
        elif method == "workflow.cancel":
            result = api_workflow_cancel(params["run_id"])
        elif method == "workflow.queue_status":
            result = api_runtime_queues()
        elif method == "portal.scheduler_status":
            result = api_runtime_scheduler()
        elif method == "agent.task.run":
            agent_id = params["agent_id"]
            prompt = params["prompt"]
            provider = params.get("provider", "auto")
            result = api_run_task(agent_id, AgentTaskRequest(prompt=prompt, provider=provider))
        elif method == "portal.test_all":
            result = api_test_all(
                TestAllRequest(
                    include_actions=params.get("include_actions", True),
                    include_messages=params.get("include_messages", True),
                )
            )
        elif method == "portal.reset_runtime":
            result = api_runtime_reset(RuntimeResetRequest(clear_saved_workflows=params.get("clear_saved_workflows", False)))
        else:
            raise KeyError(f"Unknown method: {method}")
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": str(exc)},
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "flexric_agent_portal:app",
        host=os.getenv("FLEXRIC_AGENT_PORTAL_HOST", "127.0.0.1"),
        port=int(os.getenv("FLEXRIC_AGENT_PORTAL_PORT", "8088")),
        reload=False,
        access_log=False,
    )
