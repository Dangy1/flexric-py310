"""Deploy: launch the validated steps through the injected harness `invoke`.

`invoke` applies the bounded lease wait every method gets (wait for the busy agent up to
--lease-wait-s, retry once). Steps already launched by this workflow are not relaunched.
A refusal that survives the wait stops the deployment; if a control (write) step already
ran, the record is a partial deployment.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from ..state import AppWeaverConfig, AppWeaverDeps, AppWeaverState
from ..util import event, writes


def build_deploy_node(deps: AppWeaverDeps, cfg: AppWeaverConfig) -> Callable[[AppWeaverState], Dict[str, Any]]:
    def deploy_node(state: AppWeaverState) -> Dict[str, Any]:
        steps = list(state.get("steps") or [])
        deployed = dict(state.get("deployed") or {})
        deployed_actions = dict(state.get("deployed_actions") or {})
        writes_done = int(state.get("write_steps_done") or 0)
        lease_wait = float(state.get("lease_wait_s") or 0.0)
        tool_calls: List[Dict[str, Any]] = []
        payloads: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []
        refusal = None
        failure = None
        partial = bool(state.get("partial_deployment"))
        cursor = int(state.get("deploy_cursor") or 0)
        for index in range(cursor, len(steps)):
            step = steps[index]
            agent_id, action_id = step["agent_id"], step.get("action_id")
            if not step.get("executable", True) or not action_id:
                events.append(event(deps, state, "deploy", "skip_non_executable", agent_id=agent_id))
                continue
            if agent_id in deployed and deployed_actions.get(agent_id, action_id) == action_id:
                events.append(event(deps, state, "deploy", "reuse_running", agent_id=agent_id, run_id=deployed[agent_id]))
                continue
            # A different action of an application this workflow already launched (e.g. after a re-plan) is a
            # new launch; the harness serializes it after our own earlier run instead of reusing that run.
            result = deps.invoke(agent_id, action_id) or {}
            calls = list(result.get("tool_calls") or [])
            tool_calls += calls
            payloads += list(result.get("run_payloads") or [])
            waited = float(result.get("lease_wait_s") or 0.0)
            lease_wait += waited
            final = calls[-1] if calls else {}
            events.append(event(deps, state, "deploy", "step", agent_id=agent_id, action_id=action_id,
                                status=final.get("status"), lease_wait_s=round(waited, 3), refused=bool(result.get("refused"))))
            if result.get("refused"):
                partial = partial or writes_done > 0
                refusal = {"agent_id": agent_id, "action_id": action_id, "index": index, "detail": final.get("detail", "")}
                cursor = index
                break
            if result.get("error") or final.get("status") not in {"success"}:
                failure = {"agent_id": agent_id, "action_id": action_id, "index": index,
                           "detail": str(result.get("error") or final.get("detail") or final.get("status"))}
                cursor = index
                break
            deployed[agent_id] = str(final.get("run_id") or "")
            deployed_actions[agent_id] = str(action_id)
            if writes(deps, agent_id, action_id):
                writes_done += 1
            cursor = index + 1
        out: Dict[str, Any] = {
            "tool_calls": tool_calls,
            "run_payloads": payloads,
            "deployed": deployed,
            "deployed_actions": deployed_actions,
            "write_steps_done": writes_done,
            "deploy_cursor": cursor,
            "deploy_refusal": refusal,
            "deploy_failure": failure,
            "partial_deployment": partial,
            "lease_wait_s": lease_wait,
            "events": events,
        }
        if refusal is not None:
            out["recover_trigger"] = "deploy_refused"
            out["busy_resources"] = [{"agent_id": refusal["agent_id"], "detail": refusal["detail"], "writes": writes(deps, refusal["agent_id"])}]
        return out

    return deploy_node
