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


def _latency_stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0, "mean_ms": None, "sd_ms": None, "median_ms": None, "p95_ms": None, "max_ms": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        "n": len(ordered),
        "mean_ms": statistics.fmean(ordered),
        "sd_ms": statistics.pstdev(ordered) if len(ordered) > 1 else 0.0,
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[p95_index],
        "max_ms": ordered[-1],
    }


def _ci95_halfwidth(successes: int, total: int) -> float | None:
    """Normal-approximation 95% half-width for a proportion."""
    if total <= 0:
        return None
    p = successes / total
    return 1.96 * ((p * (1 - p)) / total) ** 0.5


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
        # Detection proper: the method flagged the seeded conflict before issuing
        # control (queue/lease/twin decision). Recovery after the fact is reported
        # separately and never counted as detection.
        seeded = [item for item in conflict_labeled if item.get("conflict_label") is True]
        unseeded = [item for item in conflict_labeled if item.get("conflict_label") is False]
        true_positive = sum(1 for item in seeded if item.get("conflict_detected") is True)
        false_positive = sum(1 for item in unseeded if item.get("conflict_detected") is True)
        seeded_recovered = sum(
            1 for item in seeded
            if bool((item.get("execution_artifacts") or {}).get("internal_recovery_succeeded"))
        )
        latency_values = [float(item["orchestration_latency_ms"]) for item in available_items if item.get("orchestration_latency_ms") is not None]
        acknowledged_calls = sum(1 for call in tool_calls if call.get("acknowledged") is True)
        ack_known_calls = sum(1 for call in tool_calls if call.get("acknowledged") is not None)
        set_match = sum(1 for item in available_items if item.get("workflow_set_match") is True)
        any_accepted_match = sum(1 for item in available_items if item.get("workflow_match_any_accepted") is True)
        hallucinated_references = sum(int(item.get("hallucinated_reference_count") or 0) for item in available_items)
        cached_planner = sum(1 for item in available_items if item.get("planner_cached") is True)

        summary["methods"][method] = {
            "metric_definitions": "see evaluation/METRICS.md",
            "intent_count": len({str(item.get("intent_id")) for item in items}),
            "repeat_count": len({int(item.get("repeat_index") or 0) for item in items}),
            "workflow_accuracy_ci95": _ci95_halfwidth(exact_workflow, len(available_items)),
            "known_workflow_accuracy_ci95": _ci95_halfwidth(known_exact_workflow, len(known_items)),
            "open_world_workflow_accuracy_ci95": _ci95_halfwidth(open_world_exact_workflow, len(open_world_items)),
            "workflow_set_accuracy": _rate(set_match, len(available_items)),
            "workflow_accepted_accuracy": _rate(any_accepted_match, len(available_items)),
            "tool_call_total": len(tool_calls),
            "tool_call_launch_success_rate": _rate(tool_success, len(tool_calls)),
            "tool_call_acknowledged_rate": _rate(acknowledged_calls, ack_known_calls),
            "hallucinated_reference_count": hallucinated_references,
            "planner_cached_record_count": cached_planner,
            "seeded_conflict_records": len(seeded),
            "conflict_true_positive": true_positive,
            "conflict_false_positive": false_positive,
            "conflict_recall": _rate(true_positive, len(seeded)),
            "conflict_precision": _rate(true_positive, true_positive + false_positive),
            "conflict_false_positive_rate": _rate(false_positive, len(unseeded)),
            "seeded_conflict_internal_recovery_rate": _rate(seeded_recovered, len(seeded)),
            "latency": _latency_stats(latency_values),
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
    lines.append("Metric definitions: `evaluation/METRICS.md`. Accuracies are exact ordered matches with ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.")
    lines.append("")
    lines.append("| Method | Records (intents×repeats) | Workflow acc. | Known acc. | Open-world acc. | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for method, item in sorted(summary.get("methods", {}).items()):
        lat = item.get("latency") or {}
        lines.append(
            "| {method} | {runs} ({intents}×{repeats}) | {workflow} ±{workflow_ci} | {known_workflow} ±{known_ci} | {open_world_workflow} ±{open_ci} | {set_acc} | {calls} | {launched} | {acked} | {hall} | {recall} ({tp}/{seeded}) | {fpr} | {recovered} | {lat_mean}±{lat_sd} / {lat_med} / {lat_p95} / {lat_max} |".format(
                method=method,
                runs=item.get("available_run_count", 0),
                intents=item.get("intent_count", 0),
                repeats=item.get("repeat_count", 0),
                workflow=_format_rate(item.get("workflow_accuracy")),
                workflow_ci=_format_rate(item.get("workflow_accuracy_ci95")),
                known_workflow=_format_rate(item.get("known_workflow_accuracy")),
                known_ci=_format_rate(item.get("known_workflow_accuracy_ci95")),
                open_world_workflow=_format_rate(item.get("open_world_workflow_accuracy")),
                open_ci=_format_rate(item.get("open_world_workflow_accuracy_ci95")),
                set_acc=_format_rate(item.get("workflow_set_accuracy")),
                calls=item.get("tool_call_total", 0),
                launched=_format_rate(item.get("tool_call_launch_success_rate")),
                acked=_format_rate(item.get("tool_call_acknowledged_rate")),
                hall=item.get("hallucinated_reference_count", 0),
                recall=_format_rate(item.get("conflict_recall")),
                tp=item.get("conflict_true_positive", 0),
                seeded=item.get("seeded_conflict_records", 0),
                fpr=_format_rate(item.get("conflict_false_positive_rate")),
                recovered=_format_rate(item.get("seeded_conflict_internal_recovery_rate")),
                lat_mean=_format_float(lat.get("mean_ms")),
                lat_sd=_format_float(lat.get("sd_ms")),
                lat_med=_format_float(lat.get("median_ms")),
                lat_p95=_format_float(lat.get("p95_ms")),
                lat_max=_format_float(lat.get("max_ms")),
            )
        )
    lines.append("")
    lines.append("Legacy columns (kept for comparison with the May-2026 batch): `conflict_detection_accuracy` counts true negatives and recoveries; `tool_call_success_rate` is launch success. Do not quote them in the paper.")
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
