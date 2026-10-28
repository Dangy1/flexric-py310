#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _split(item: Dict[str, Any]) -> str:
    return str(item.get("intent_split") or ("open_world" if item.get("intent_open_world") else "known"))


# ---------------------------------------------------------------- pre-registered label rule
def load_run_intents(run_dir: Path, records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Intents of a run: `intents.json` copied into the run directory, else the labels each record carries.

    Records store `expected_workflow` and `accepted_workflows`, the only inputs of the label rule, so
    runs written before `intents.json` was copied (e.g. merged Batch A) score identically.
    """
    intents: Dict[str, Dict[str, Any]] = {}
    path = run_dir / "intents.json"
    if path.exists():
        for intent in json.loads(path.read_text(encoding="utf-8")):
            intents[str(intent.get("id"))] = intent
    for record in records:
        intent_id = str(record.get("intent_id"))
        if intent_id not in intents:
            intents[intent_id] = {
                "id": intent_id,
                "expected_workflow": list(record.get("expected_workflow") or []),
                "accepted_workflows": [list(chain) for chain in (record.get("accepted_workflows") or [])],
            }
    return intents


def run_registry(run_dir: Path) -> Dict[str, Any]:
    """The Agent Registry of a run: current cards, restricted to the card ids in its manifest."""
    from evaluation.label_rules import build_registry

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    agent_ids = (manifest.get("registry") or {}).get("agent_ids")
    directory = bool((manifest.get("evaluation_runtime_config") or {}).get("rapp_directory_enabled"))
    if agent_ids and any(str(a).startswith("rapp.") for a in agent_ids):
        directory = True
    return build_registry(rapp_directory=directory or not agent_ids, agent_ids=agent_ids)


def attach_rule_matches(records: List[Dict[str, Any]], intents: Dict[str, Dict[str, Any]],
                        registry: Dict[str, Any], force: bool = False) -> int:
    """Set `workflow_match_rule` / `workflow_rule_reasons` from `generated_workflow` (in place).

    Records that already carry `workflow_match_rule` (written by the harness) are kept unless `force`.
    Returns the number of records scored here.
    """
    from evaluation.label_rules import rule_match

    scored = 0
    for record in records:
        if not force and record.get("workflow_match_rule") is not None:
            continue
        intent = intents.get(str(record.get("intent_id")))
        if intent is None:
            continue
        ok, reasons = rule_match(record.get("generated_workflow") or [], intent, registry)
        record["workflow_match_rule"] = ok
        record["workflow_rule_reasons"] = reasons
        scored += 1
    return scored


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


def _execution_conflict(execution: Dict[str, Any]) -> bool:
    """Same rule as run_harness.detect_conflict: queued run, blocked launch, or a refused tool call."""
    if str(execution.get("status") or "") == "queued" or execution.get("blocked_reason"):
        return True
    return any(call.get("status") in {"conflict", "queued"} or is_lease_refusal(call) for call in execution.get("tool_calls") or [])


def is_lease_refusal(call: Dict[str, Any]) -> bool:
    """The portal's per-agent lease refused the launch (HTTP 409) - before any control was issued.

    Template workflows record this as a failed tool call, custom chains as `blocked_reason`; both are
    the same event and count as a detected conflict for every method.
    """
    return str(call.get("detail") or "").startswith("409") or "already has an active action" in str(call.get("detail") or "")


def conflict_flagged(item: Dict[str, Any]) -> bool:
    """Conflict flagged before control, in the record's final execution *or* its first execution.

    With internal recovery the final execution is the clean re-run, so a conflict the method hit and
    refused on its first execution is only visible in `execution_artifacts.initial_execution`.
    """
    if item.get("conflict_detected") is True:
        return True
    # Recomputed from the raw record so batches written before the rule was unified score the same.
    if item.get("blocked_reason") or any(is_lease_refusal(call) for call in item.get("tool_calls") or []):
        return True
    initial = (item.get("execution_artifacts") or {}).get("initial_execution")
    return isinstance(initial, dict) and _execution_conflict(initial)


def _conflict_detected_or_handled(item: Dict[str, Any]) -> bool:
    if conflict_flagged(item):
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


def build_summary(records: List[Dict[str, Any]], intents: Dict[str, Dict[str, Any]] | None = None,
                  registry: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Per-method summary. With `intents` and `registry`, records without `workflow_match_rule` are scored
    under the pre-registered label rule first (rule accuracy is the primary accuracy; METRICS.md)."""
    if intents is not None and registry is not None:
        attach_rule_matches(records, intents, registry)
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
        rule_items = [item for item in available_items if item.get("workflow_match_rule") is not None]
        rule_match_count = sum(1 for item in rule_items if item.get("workflow_match_rule") is True)
        known_rule_items = [item for item in rule_items if _split(item) == "known"]
        open_world_rule_items = [item for item in rule_items if item.get("intent_open_world") is True]
        known_rule_match = sum(1 for item in known_rule_items if item.get("workflow_match_rule") is True)
        open_world_rule_match = sum(1 for item in open_world_rule_items if item.get("workflow_match_rule") is True)
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
                if not conflict_flagged(item):
                    conflict_correct += 1
        # Detection proper: the method flagged the seeded conflict before issuing
        # control (queue/lease/twin decision). Recovery after the fact is reported
        # separately and never counted as detection.
        seeded = [item for item in conflict_labeled if item.get("conflict_label") is True]
        unseeded = [item for item in conflict_labeled if item.get("conflict_label") is False]
        true_positive = sum(1 for item in seeded if conflict_flagged(item))
        false_positive = sum(1 for item in unseeded if conflict_flagged(item))
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

        retrieval_items = [item for item in available_items if item.get("retrieval_hit") is not None]
        retrieval_hits = sum(1 for item in retrieval_items if item.get("retrieval_hit") is True)
        compat_items = [item for item in available_items if item.get("compat_ok") is not None]
        compat_ok = sum(1 for item in compat_items if item.get("compat_ok") is True)
        by_split: Dict[str, Dict[str, Any]] = {}
        for split in sorted({_split(item) for item in available_items}):
            split_items = [item for item in available_items if _split(item) == split]
            matched = sum(1 for item in split_items if item.get("workflow_match") is True)
            accepted = sum(1 for item in split_items if item.get("workflow_match_any_accepted") is True)
            split_rule = [item for item in split_items if item.get("workflow_match_rule") is not None]
            rule_ok = sum(1 for item in split_rule if item.get("workflow_match_rule") is True)
            by_split[split] = {
                "records": len(split_items),
                "rule_accuracy": _rate(rule_ok, len(split_rule)),
                "rule_ci95": _ci95_halfwidth(rule_ok, len(split_rule)),
                "workflow_accuracy": _rate(matched, len(split_items)),
                "ci95": _ci95_halfwidth(matched, len(split_items)),
                "accepted_accuracy": _rate(accepted, len(split_items)),
            }

        summary["methods"][method] = {
            "metric_definitions": "see evaluation/METRICS.md",
            "by_split": by_split,
            "retrieval_hit_rate": _rate(retrieval_hits, len(retrieval_items)),
            "compat_ok_rate": _rate(compat_ok, len(compat_items)),
            "intent_count": len({str(item.get("intent_id")) for item in items}),
            "repeat_count": len({int(item.get("repeat_index") or 0) for item in items}),
            "rule_scored_records": len(rule_items),
            "rule_accuracy": _rate(rule_match_count, len(rule_items)),
            "rule_accuracy_ci95": _ci95_halfwidth(rule_match_count, len(rule_items)),
            "known_rule_accuracy": _rate(known_rule_match, len(known_rule_items)),
            "known_rule_accuracy_ci95": _ci95_halfwidth(known_rule_match, len(known_rule_items)),
            "open_world_rule_accuracy": _rate(open_world_rule_match, len(open_world_rule_items)),
            "open_world_rule_accuracy_ci95": _ci95_halfwidth(open_world_rule_match, len(open_world_rule_items)),
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
            "rule_match_rate": _rate(sum(1 for item in items if item.get("workflow_match_rule") is True),
                                     sum(1 for item in items if item.get("workflow_match_rule") is not None)),
            "workflow_match_rate": _rate(sum(1 for item in items if item.get("workflow_match") is True), len(items)),
            "failure_rate": _rate(sum(1 for item in items if item.get("failure_detected") is True), len(items)),
            "conflict_rate": _rate(sum(1 for item in items if conflict_flagged(item)), len(items)),
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
    lines.append("Metric definitions: `evaluation/METRICS.md`. **Accuracy** is the pre-registered label rule (required apps, observe < control < validate, no forbidden writer; `evaluation/label_rules.py`); *exact* is the ordered match with the labelled chain. ±95% CI half-widths; latency is intent→validated plan, excluding the tool-acknowledgement wait.")
    lines.append("")
    lines.append("| Method | Records (intents×repeats) | Accuracy (rule) | Known (rule) | Open-world (rule) | Exact acc. | Known exact | Open-world exact | Set acc. | Tool calls | Launched | Acknowledged | Halluc. refs | Conflict recall (TP/seeded) | Conflict FP rate | Seeded recovered | Latency mean±sd / median / p95 / max (ms) |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for method, item in sorted(summary.get("methods", {}).items()):
        lat = item.get("latency") or {}
        lines.append(
            "| {method} | {runs} ({intents}×{repeats}) | {rule} ±{rule_ci} | {known_rule} ±{known_rule_ci} | {open_rule} ±{open_rule_ci} | {workflow} ±{workflow_ci} | {known_workflow} ±{known_ci} | {open_world_workflow} ±{open_ci} | {set_acc} | {calls} | {launched} | {acked} | {hall} | {recall} ({tp}/{seeded}) | {fpr} | {recovered} | {lat_mean}±{lat_sd} / {lat_med} / {lat_p95} / {lat_max} |".format(
                method=method,
                runs=item.get("available_run_count", 0),
                intents=item.get("intent_count", 0),
                repeats=item.get("repeat_count", 0),
                rule=_format_rate(item.get("rule_accuracy")),
                rule_ci=_format_rate(item.get("rule_accuracy_ci95")),
                known_rule=_format_rate(item.get("known_rule_accuracy")),
                known_rule_ci=_format_rate(item.get("known_rule_accuracy_ci95")),
                open_rule=_format_rate(item.get("open_world_rule_accuracy")),
                open_rule_ci=_format_rate(item.get("open_world_rule_accuracy_ci95")),
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
    lines.append("| Intent ID | Runs | Rule match | Exact match | Failure rate | Conflict rate |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for intent_id, item in sorted(summary.get("intents", {}).items()):
        lines.append(
            "| {intent_id} | {runs} | {rule} | {workflow} | {failure} | {conflict} |".format(
                intent_id=intent_id,
                runs=item.get("run_count", 0),
                rule=_format_rate(item.get("rule_match_rate")),
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
    import argparse

    parser = argparse.ArgumentParser(description="Summarise a batch; rule accuracy is scored from generated_workflow + "
                                                 "the run's intents.json (or the labels in each record) + the run's registry.")
    parser.add_argument("records", help="records.jsonl of a run directory")
    parser.add_argument("--markdown", action="store_true", help="print the markdown analysis instead of JSON")
    parser.add_argument("--rescore", action="store_true", help="recompute workflow_match_rule even if records carry it")
    args = parser.parse_args(argv[1:])
    record_path = Path(args.records).resolve()
    records = load_records(record_path)
    run_dir = record_path.parent
    attach_rule_matches(records, load_run_intents(run_dir, records), run_registry(run_dir), force=args.rescore)
    summary = build_summary(records)
    print(build_markdown(summary) if args.markdown else json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
