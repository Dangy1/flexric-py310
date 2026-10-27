#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_records(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def _mean(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values]
    if not items:
        return None
    return statistics.fmean(items)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _metric_delta_values(records: List[Dict[str, Any]], metric_name: str) -> List[float]:
    deltas: List[float] = []
    for record in records:
        before = record.get("before") or {}
        after = record.get("after") or {}
        before_value = before.get(metric_name)
        after_value = after.get(metric_name)
        if before_value is None or after_value is None:
            continue
        deltas.append(float(after_value) - float(before_value))
    return deltas


def _conflict_detected_or_handled(item: Dict[str, Any]) -> bool:
    if item.get("conflict_detected") is True:
        return True
    artifacts = item.get("execution_artifacts") or {}
    return bool(artifacts.get("internal_recovery_attempted")) or bool(artifacts.get("recovery_reset_runtime"))


def build_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_method: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_method[str(record.get("method"))].append(record)
        by_intent[str(record.get("intent_id"))].append(record)

    summary: Dict[str, Any] = {
        "record_count": len(records),
        "methods": {},
        "intents": {},
    }

    for method, items in sorted(by_method.items()):
        available_items = [item for item in items if item.get("method_available") is not False]
        known_items = [item for item in available_items if item.get("intent_open_world") is not True]
        open_world_items = [item for item in available_items if item.get("intent_open_world") is True]
        exact_workflow = sum(1 for item in available_items if item.get("workflow_match") is True)
        known_exact_workflow = sum(1 for item in known_items if item.get("workflow_match") is True)
        open_world_exact_workflow = sum(1 for item in open_world_items if item.get("workflow_match") is True)
        tool_calls = [call for item in available_items for call in list(item.get("tool_calls") or [])]
        tool_success = sum(1 for call in tool_calls if call.get("status") == "success")
        observation_calls = [call for call in tool_calls if call.get("role") == "observation"]
        non_observation_calls = [call for call in tool_calls if call.get("role") != "observation"]
        observation_success = sum(1 for call in observation_calls if call.get("status") == "success")
        non_observation_success = sum(1 for call in non_observation_calls if call.get("status") == "success")
        cached_observation_calls = sum(1 for call in observation_calls if call.get("cached_result") is True)
        policy_valid = sum(1 for item in available_items if item.get("policy_valid") is True)
        hallucinated = sum(1 for item in available_items if item.get("hallucinated_api") is True)
        human_intervention = sum(1 for item in available_items if item.get("human_intervention_required") is True)
        metrics_available = sum(1 for item in available_items if item.get("metrics_available") is True)
        failures = [item for item in available_items if item.get("failure_detected") is True]
        recoveries = sum(1 for item in failures if item.get("recovered_from_failure") is True)
        internal_recovery_attempted_items = [
            item for item in available_items
            if bool((item.get("execution_artifacts") or {}).get("internal_recovery_attempted"))
        ]
        internal_recovery_success = sum(
            1 for item in internal_recovery_attempted_items
            if bool((item.get("execution_artifacts") or {}).get("internal_recovery_succeeded"))
        )
        recovery_triggered = [
            item for item in available_items
            if item.get("failure_detected") is True
            or item.get("conflict_detected") is True
            or bool((item.get("execution_artifacts") or {}).get("internal_recovery_attempted"))
        ]
        effective_recovery_success = sum(
            1 for item in recovery_triggered
            if item.get("recovered_from_failure") is True
            or bool((item.get("execution_artifacts") or {}).get("internal_recovery_succeeded"))
        )
        conflict_labeled = [item for item in available_items if item.get("conflict_label") is not None]
        custom_workflow_items = [
            item for item in available_items
            if str(item.get("generated_workflow_id") or "").startswith("custom:")
        ]
        conflict_correct = 0
        for item in conflict_labeled:
            label = item.get("conflict_label")
            if label is True:
                if _conflict_detected_or_handled(item):
                    conflict_correct += 1
            elif label is False:
                if item.get("conflict_detected") is False:
                    conflict_correct += 1
        latency_values = [float(item["orchestration_latency_ms"]) for item in available_items if item.get("orchestration_latency_ms") is not None]

        summary["methods"][method] = {
            "run_count": len(items),
            "available_run_count": len(available_items),
            "availability_rate": _rate(len(available_items), len(items)),
            "workflow_accuracy": _rate(exact_workflow, len(available_items)),
            "known_workflow_accuracy": _rate(known_exact_workflow, len(known_items)),
            "open_world_workflow_accuracy": _rate(open_world_exact_workflow, len(open_world_items)),
            "tool_call_success_rate": _rate(tool_success, len(tool_calls)),
            "observation_tool_success_rate": _rate(observation_success, len(observation_calls)),
            "non_observation_tool_success_rate": _rate(non_observation_success, len(non_observation_calls)),
            "cached_observation_rate": _rate(cached_observation_calls, len(observation_calls)),
            "custom_workflow_rate": _rate(len(custom_workflow_items), len(available_items)),
            "policy_validity_rate": _rate(policy_valid, len(available_items)),
            "hallucination_rate": _rate(hallucinated, len(available_items)),
            "human_intervention_rate": _rate(human_intervention, len(available_items)),
            "external_recovery_rate": _rate(recoveries, len(failures)),
            "internal_recovery_attempt_rate": _rate(len(internal_recovery_attempted_items), len(available_items)),
            "internal_recovery_success_rate": _rate(internal_recovery_success, len(internal_recovery_attempted_items)),
            "recovery_rate": _rate(effective_recovery_success, len(recovery_triggered)),
            "conflict_detection_accuracy": _rate(conflict_correct, len(conflict_labeled)),
            "average_orchestration_latency_ms": _mean(latency_values),
            "metrics_availability_rate": _rate(metrics_available, len(available_items)),
            "latency_delta_ms": _mean(_metric_delta_values(available_items, "latency_ms")),
            "throughput_delta_mbps": _mean(_metric_delta_values(available_items, "throughput_mbps")),
            "prb_delta": _mean(_metric_delta_values(available_items, "prb_utilization")),
            "sla_violation_delta": _mean(_metric_delta_values(available_items, "sla_violation_rate")),
        }

    for intent_id, items in sorted(by_intent.items()):
        summary["intents"][intent_id] = {
            "intent": items[0].get("intent"),
            "run_count": len(items),
            "methods": sorted({str(item.get("method")) for item in items}),
            "workflow_match_rate": _rate(sum(1 for item in items if item.get("workflow_match") is True), len(items)),
            "failure_rate": _rate(sum(1 for item in items if item.get("failure_detected") is True), len(items)),
            "conflict_rate": _rate(sum(1 for item in items if item.get("conflict_detected") is True), len(items)),
        }

    return summary


def build_markdown(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Evaluation Analysis")
    lines.append("")
    lines.append(f"- records: {summary.get('record_count', 0)}")
    lines.append(f"- methods: {len(summary.get('methods', {}))}")
    lines.append(f"- intents: {len(summary.get('intents', {}))}")
    lines.append("")
    lines.append("## Method Summary")
    lines.append("")
    lines.append("| Method | Runs | Available runs | Workflow accuracy | Known accuracy | Open-world accuracy | Custom workflow rate | Tool success | Non-observation tool success | Cached observation rate | Policy validity | Hallucination | Recovery | Internal recovery | Conflict detection | Avg orchestration latency (ms) |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for method, item in sorted(summary.get("methods", {}).items()):
        lines.append(
            "| {method} | {runs} | {available_runs} ({availability}) | {workflow} | {known_workflow} | {open_world_workflow} | {custom_workflow} | {tool} | {non_observation_tool} | {cached_observation} | {policy} | {hall} | {recovery} | {internal_recovery} | {conflict} | {latency} |".format(
                method=method,
                runs=item.get("run_count", 0),
                available_runs=item.get("available_run_count", 0),
                availability=_format_rate(item.get("availability_rate")),
                workflow=_format_rate(item.get("workflow_accuracy")),
                known_workflow=_format_rate(item.get("known_workflow_accuracy")),
                open_world_workflow=_format_rate(item.get("open_world_workflow_accuracy")),
                custom_workflow=_format_rate(item.get("custom_workflow_rate")),
                tool=_format_rate(item.get("tool_call_success_rate")),
                non_observation_tool=_format_rate(item.get("non_observation_tool_success_rate")),
                cached_observation=_format_rate(item.get("cached_observation_rate")),
                policy=_format_rate(item.get("policy_validity_rate")),
                hall=_format_rate(item.get("hallucination_rate")),
                recovery=_format_rate(item.get("recovery_rate")),
                internal_recovery=_format_rate(item.get("internal_recovery_success_rate")),
                conflict=_format_rate(item.get("conflict_detection_accuracy")),
                latency=_format_float(item.get("average_orchestration_latency_ms")),
            )
        )
    lines.append("")
    lines.append("## Intent Summary")
    lines.append("")
    lines.append("| Intent ID | Runs | Workflow match | Failure rate | Conflict rate |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for intent_id, item in sorted(summary.get("intents", {}).items()):
        lines.append(
            "| {intent_id} | {runs} | {workflow} | {failure} | {conflict} |".format(
                intent_id=intent_id,
                runs=item.get("run_count", 0),
                workflow=_format_rate(item.get("workflow_match_rate")),
                failure=_format_rate(item.get("failure_rate")),
                conflict=_format_rate(item.get("conflict_rate")),
            )
        )
    return "\n".join(lines) + "\n"


def _format_rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _format_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("Usage: analyze_results.py <records.jsonl>", file=sys.stderr)
        return 2
    record_path = Path(argv[1]).resolve()
    records = load_records(record_path)
    summary = build_summary(records)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
