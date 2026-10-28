#!/usr/bin/env python3
"""Emulated rApp runtime.

Every rApp in `catalog.json` is served by this one module. A tool invocation
reads recent KPM from the shared KPM bus (or the simulator's KPM capture),
computes the rApp's decision with a small, documented model, and either
reports it (recommend_/predict_/detect_ tools) or applies it (apply_/set_/
execute_ tools) by writing an A1-style policy document and, where an xApp
exists for the control, launching it through the portal.

Two entry points:

* CLI (used by the portal's subprocess action launcher, so rApp actions look
  exactly like xApp suite actions to the scheduler and the harness):

      python rapps/runtime.py --rapp rapp.energy_saving --tool recommend_sleep_cells --duration-s 10

  The first line printed on success is `rApp ack: <rapp> <tool> <status>`,
  which the evaluation harness uses as the acknowledgement marker.

* MCP server (optional): `python rapps/runtime.py --serve --port 8010` exposes
  each tool as `<rapp_id>.<tool_id>` over MCP so external agents can call
  them; it is not required for the benchmark.

Everything here is emulation: the numbers are derived from live KPM with
simple estimators and are labelled as such in every output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

THIS_DIR = Path(__file__).resolve().parent
CATALOG_PATH = Path(os.getenv("FLEXRIC_RAPP_CATALOG", str(THIS_DIR / "catalog.json")))
KPM_BUS_URL = os.getenv("KPM_BUS_URL", "http://127.0.0.1:8091").rstrip("/")
POLICY_DIR = Path(os.getenv("FLEXRIC_RAPP_POLICY_DIR", "/tmp/flexric_rapps/policies"))
A1_SINK_URL = os.getenv("FLEXRIC_A1_SINK_URL", "").strip()  # optional: POST policies to a Non-RT RIC A1 endpoint


def load_catalog() -> Dict[str, Dict[str, Any]]:
    entries = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in entries}


# ---------------------------------------------------------------------------
# KPM access
# ---------------------------------------------------------------------------

_KPM_LINE_RE = re.compile(r"ue_type=(?P<ue_type>\S+)\s+amf_ue_ngap_id=(?P<ue_id>\S+)\s+meas=(?P<meas>\S+)\s+value=(?P<value>\S+)")
# The emulator reports raw PRB counts per period rather than a utilisation
# fraction; normalise against the busiest sample in the window so the
# decision thresholds below stay in [0, 1].
_PRB_METRICS = {"RRU.PrbTotDl", "RRU.PrbTotUl"}


def fetch_recent_kpm(limit: int = 200, timeout_s: float = 3.0) -> Dict[str, Any]:
    """Return {'available': bool, 'cells': {cell_id: {metric: latest}}, 'detail': str}.

    Reads the shared KPM bus (`GET /kpm/recent`), whose records carry the
    collector's raw text lines (`ue_type=… amf_ue_ngap_id=… meas=… value=…`).
    Cells are keyed by the reporting node/UE id.
    """
    try:
        response = requests.get(f"{KPM_BUS_URL}/kpm/recent", params={"mode": "all", "limit": max(20, min(limit, 400))}, timeout=timeout_s)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return {"available": False, "cells": {}, "detail": f"KPM bus unavailable: {exc}"}
    cells: Dict[str, Dict[str, float]] = {}
    maxima: Dict[str, float] = {}
    for record in list(payload.get("records") or []):
        match = _KPM_LINE_RE.search(str(record.get("raw") or ""))
        if not match:
            continue
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        name = match.group("meas")
        cells.setdefault(match.group("ue_id"), {})[name] = value
        maxima[name] = max(maxima.get(name, 0.0), value)
    for metrics in cells.values():
        for name in list(metrics):
            if name in _PRB_METRICS and maxima.get(name, 0.0) > 1.0:
                metrics[name] = round(metrics[name] / maxima[name], 3)
    return {"available": bool(cells), "cells": cells, "detail": "" if cells else "No parsable KPM records in window."}


def _metric(cells: Dict[str, Dict[str, float]], name: str) -> Dict[str, float]:
    return {cell: values[name] for cell, values in cells.items() if name in values}


# ---------------------------------------------------------------------------
# Decision models (deliberately simple; documented in the paper as emulation)
# ---------------------------------------------------------------------------

def decide(rapp: Dict[str, Any], tool_id: str, kpm: Dict[str, Any]) -> Dict[str, Any]:
    family = rapp["family"]
    cells = kpm.get("cells") or {}
    prb = _metric(cells, "RRU.PrbTotDl")
    thp = _metric(cells, "DRB.UEThpDl")
    delay = _metric(cells, "DRB.RlcSduDelayDl")
    base = {"rapp": rapp["id"], "tool": tool_id, "family": family, "kpm_available": kpm.get("available", False), "emulated": True}

    if family == "energy_saving":
        sleep = sorted((c for c, v in prb.items() if v < 0.15), key=lambda c: prb[c])
        return {**base, "decision": {"cells_to_sleep": sleep, "threshold_prb": 0.15, "estimated_energy_saving_pct": round(12.0 * len(sleep), 1)}}
    if family == "traffic_steering":
        if prb:
            hot = max(prb, key=prb.get)
            cold = min(prb, key=prb.get)
            return {**base, "decision": {"from_cell": hot, "to_cell": cold, "ue_share_pct": 20 if prb[hot] - prb[cold] > 0.3 else 0}}
        return {**base, "decision": {"from_cell": None, "to_cell": None, "ue_share_pct": 0}}
    if family == "qoe_prediction":
        mos: Dict[str, float] = {}
        for cell in set(thp) | set(delay):
            t = thp.get(cell, 5.0)
            d = delay.get(cell, 20.0)
            mos[cell] = round(max(1.0, min(4.5, 1.0 + 0.6 * min(t, 5.0) - 0.02 * max(0.0, d - 10.0))), 2)
        at_risk = [c for c, m in mos.items() if m < 3.0]
        return {**base, "decision": {"mos_forecast": mos, "at_risk_cells": at_risk, "model": "linear(thp, delay) emulation"}}
    if family in {"mobility_optimization", "interference", "self_healing"}:
        return {**base, "decision": {"cells": sorted(prb)[:2], "parameter_delta": {"a3_offset_db": -1, "ttt_ms": 40} if family == "mobility_optimization" else {"power_cap_dbm": -3}}}
    if family == "ret_tilt":
        return {**base, "decision": {"tilt_deltas_deg": {c: (1 if v > 0.7 else 0) for c, v in prb.items()}}}
    if family in {"root_cause", "anomaly_detection"}:
        anomalies = [c for c, v in delay.items() if v > 50.0] + [c for c, v in prb.items() if v > 0.9]
        return {**base, "decision": {"anomalous_cells": sorted(set(anomalies)), "hypotheses": ["transport queue build-up" if delay else "unknown", "PRB saturation" if prb else "unknown"]}}
    if family == "slice_sla":
        return {**base, "decision": {"slice_prb_targets": {"slice-1": 0.5, "slice-2": 0.3}, "violations": [c for c, v in delay.items() if v > 30.0]}}
    if family in {"capacity_mgmt", "spectrum_sharing"}:
        return {**base, "decision": {"headroom_pct": {c: round(100 * (1 - v), 1) for c, v in prb.items()}, "expand": [c for c, v in prb.items() if v > 0.8]}}
    if family == "pm_kpi":
        return {**base, "decision": {"report": {"cells": len(cells), "prb_mean": round(sum(prb.values()) / len(prb), 3) if prb else None, "thp_mean_mbps": round(sum(thp.values()) / len(thp), 3) if thp else None}}}
    if family == "transport_qos":
        return {**base, "decision": {"queue_policy": "codel" if any(v > 30.0 for v in delay.values()) else "none", "bearers": sorted(delay)}}
    if family == "ran_lifecycle":
        return {**base, "decision": {"change_plan": ["freeze", "stage", "apply", "verify"], "maintenance_window": "02:00-04:00"}}
    if family == "ue_qos_control":
        return {**base, "decision": {"priority_ues": sorted(delay, key=lambda c: -delay[c])[:4], "weight": "high"}}
    extended = decide_extended(family, cells, prb, thp, delay)
    if extended is not None:
        return {**base, "decision": extended}
    return {**base, "decision": {}}


# ---------------------------------------------------------------------------
# Decision rules of the families added on 2026-10-28 (docs/RAPP_USE_CASES.md).
# Same contract as above: deterministic, documented one-line estimators over
# the latest KPM snapshot (PRB fractions normalised to [0, 1], throughput in
# Mbps, delay in ms). Inputs a family would read from O1 PM/CM/FM in a real
# deployment (handover counters, RACH and RRC setup counters, PCIs, alarms,
# power) are not on the KPM bus; the rules then fall back to the KPM proxies
# named in each comment and say so in the output (`proxy`).
# ---------------------------------------------------------------------------

def _pseudo_pci(cell: str) -> int:
    """Stable emulated PCI (0..1007) per reporting entity; the emulator exposes no PCI."""
    return sum((i + 1) * ord(ch) for i, ch in enumerate(str(cell))) % 1008


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def decide_extended(family: str, cells: Dict[str, Dict[str, float]], prb: Dict[str, float],
                    thp: Dict[str, float], delay: Dict[str, float]) -> Optional[Dict[str, Any]]:
    prb_ul = _metric(cells, "RRU.PrbTotUl")
    thp_ul = _metric(cells, "DRB.UEThpUl")
    if family == "anr":
        # Candidate relations: every cell pair whose loads differ by < 0.3 (comparable footprint proxy),
        # at most three per cell; nothing is removed in emulation.
        ids = sorted(prb)
        add = [[a, b] for i, a in enumerate(ids) for b in ids[i + 1:] if abs(prb[a] - prb[b]) < 0.3][: 3 * max(1, len(ids))]
        return {"add_relations": add, "remove_relations": [], "proxy": "PRB similarity (no UE measurement reports on the KPM bus)"}
    if family == "pci_optimization":
        # Collision/confusion proxy: emulated PCIs that share the same PCI mod 3 (DL reference-signal shift).
        groups: Dict[int, List[str]] = {}
        for cell in sorted(cells):
            groups.setdefault(_pseudo_pci(cell) % 3, []).append(cell)
        clashes = [members for members in groups.values() if len(members) > 1]
        reassign = {cell: (_pseudo_pci(cell) + 1 + k) % 1008 for k, members in enumerate(clashes) for cell in members[1:]}
        return {"pci_mod3_clashes": clashes, "pci_reassignment": reassign, "proxy": "emulated PCIs"}
    if family == "sleeping_cell":
        # Sleeping: PRB < 0.02 and throughput < 0.01 Mbps while the median cell has PRB > 0.3.
        busy = _median(list(prb.values())) > 0.3
        sleeping = sorted(c for c, v in prb.items() if busy and v < 0.02 and thp.get(c, 0.0) < 0.01)
        return {"sleeping_cells": sleeping, "rule": "PRB<0.02 and thp<0.01 Mbps while median PRB>0.3"}
    if family == "mobility_load_balancing":
        # CIO: -2 dB on cells 0.2 above the mean PRB (shrink), +2 dB on cells 0.2 below (grow).
        mean = sum(prb.values()) / len(prb) if prb else 0.0
        cio = {c: (-2 if v > mean + 0.2 else 2 if v < mean - 0.2 else 0) for c, v in prb.items()}
        return {"cio_delta_db": cio, "mean_prb": round(mean, 3)}
    if family == "rach_optimization":
        # Access-load proxy: UL PRB > 0.8 -> larger PRACH occasion density and ZCZ step +1.
        hot = sorted(c for c, v in prb_ul.items() if v > 0.8)
        return {"cells": hot, "parameter_delta": {"prach_config_index_step": 1, "zero_correlation_zone_step": 1} if hot else {},
                "proxy": "RRU.PrbTotUl (no RACH/RRC setup counters on the KPM bus)"}
    if family == "beamforming":
        # GoB pattern per cell: PRB > 0.7 -> narrow high-gain beams, < 0.3 -> wide coverage beams, else default.
        return {"beam_pattern": {c: ("narrow_high_gain" if v > 0.7 else "wide_coverage" if v < 0.3 else "default") for c, v in prb.items()}}
    if family == "mimo_sleep":
        # Medium load keeps the cell on: 0.15 <= PRB < 0.25 -> 16T16R, 0.25 <= PRB < 0.4 -> 32T32R, else 64T64R.
        def channels(v: float) -> str:
            return "16T16R" if 0.15 <= v < 0.25 else "32T32R" if 0.25 <= v < 0.4 else "64T64R"
        config = {c: channels(v) for c, v in prb.items()}
        return {"rf_channels": config, "muted_cells": sorted(c for c, v in config.items() if v != "64T64R"),
                "estimated_energy_saving_pct": round(6.0 * sum(1 for v in config.values() if v != "64T64R"), 1)}
    if family == "traffic_forecast":
        # Persistence forecast with 10 % growth headroom (single snapshot; no seasonal model in emulation).
        return {"horizon_min": 60, "prb_forecast": {c: round(min(1.0, 1.1 * v), 3) for c, v in prb.items()},
                "peak_cells": sorted(c for c, v in prb.items() if 1.1 * v > 0.8), "model": "persistence x1.1 emulation"}
    if family == "fault_prediction":
        # Risk = 0.5 [delay > 50 ms] + 0.5 [thp < 0.1 Mbps]; PEE power/temperature are not on the KPM bus.
        risk = {c: round(0.5 * (delay.get(c, 0.0) > 50.0) + 0.5 * (thp.get(c, 1.0) < 0.1), 2) for c in cells}
        return {"fault_risk": risk, "maintenance": sorted(c for c, r in risk.items() if r >= 0.5), "proxy": "delay/throughput"}
    if family == "slice_admission":
        # Mean PRB > 0.85 -> admit only the guaranteed slice; > 0.7 -> cap best-effort at 50 % of its quota.
        mean = sum(prb.values()) / len(prb) if prb else 0.0
        policy = ({"slice-1": "admit", "slice-2": "reject_new"} if mean > 0.85 else
                  {"slice-1": "admit", "slice-2": "cap_50pct"} if mean > 0.7 else {"slice-1": "admit", "slice-2": "admit"})
        return {"admission_policy": policy, "mean_prb": round(mean, 3)}
    if family == "signalling_storm":
        # Storm if more than 64 UE entities report in the window (proxy for a connection-attempt burst).
        storm = len(cells) > 64
        return {"storm_detected": storm, "reporting_ues": len(cells), "throttle_ratio": 0.5 if storm else 0.0,
                "proxy": "reporting-UE count (no RRC setup counters on the KPM bus)"}
    if family == "ul_interference":
        # UL interference suspected: UL PRB > 0.6 with UL throughput < 1 Mbps -> P0 -3 dB, alpha 0.8.
        cells_hit = sorted(c for c, v in prb_ul.items() if v > 0.6 and thp_ul.get(c, 0.0) < 1.0)
        return {"interfered_cells": cells_hit, "parameter_delta": {"p0_nominal_pusch_db": -3, "alpha": 0.8} if cells_hit else {}}
    if family == "endc_steering":
        # NR leg load: PRB > 0.8 -> keep more traffic on the LTE anchor; < 0.3 -> prefer the NR leg.
        return {"dc_profile": {c: ("lte_anchor_heavy" if v > 0.8 else "nr_preferred" if v < 0.3 else "balanced") for c, v in prb.items()}}
    if family == "config_audit":
        # No CM source in emulation: lists the audited entities and reports no deviation.
        return {"audited": sorted(cells), "deviations": [], "note": "CM not available in emulation"}
    if family == "crossed_feeder":
        # Swap symptom proxy: two entities with identical (PRB, thp) pairs.
        seen: Dict[Any, str] = {}
        suspects = []
        for c in sorted(cells):
            key = (prb.get(c), thp.get(c))
            if None not in key and key in seen:
                suspects.append([seen[key], c])
            seen.setdefault(key, c)
        return {"suspect_pairs": suspects}
    if family == "special_events":
        # Event profile on cells with PRB > 0.5: +1 carrier activation flag, CIO +2 dB, revert after 4 h.
        return {"event_cells": sorted(c for c, v in prb.items() if v > 0.5),
                "profile": {"carrier_boost": True, "cio_delta_db": 2}, "revert_after_h": 4}
    return None


def is_apply_tool(tool_id: str) -> bool:
    stem = tool_id.split("_", 1)[-1] if "_" in tool_id and tool_id.split("_", 1)[0] in {"northwind", "kestrel", "orion", "helix", "vtt", "aalto"} else tool_id
    return stem.split("_")[0] in {"apply", "set", "execute", "tune", "wake", "rollback", "clear", "restore", "revert"}


def write_policy(rapp: Dict[str, Any], tool_id: str, result: Dict[str, Any]) -> Path:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    policy = {
        "policy_type": next((i for i in rapp.get("interfaces", []) if i.startswith("A1-P")), "A1-P policy-type emulated"),
        "scope": rapp.get("control_scopes", []),
        "rapp": rapp["id"],
        "tool": tool_id,
        "issued_at": time.time(),
        "body": result.get("decision", {}),
        "emulated": True,
    }
    path = POLICY_DIR / f"{rapp['id']}.{tool_id}.{int(time.time())}.json"
    path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    if A1_SINK_URL:
        try:
            requests.put(f"{A1_SINK_URL}/{rapp['id']}", json=policy, timeout=3.0)
        except Exception as exc:  # pragma: no cover - optional sink
            print(f"A1 sink unreachable: {exc}", file=sys.stderr)
    return path


def run_tool(rapp_id: str, tool_id: str, duration_s: int) -> int:
    catalog = load_catalog()
    rapp = catalog.get(rapp_id)
    if rapp is None:
        print(f"rApp error: unknown rApp {rapp_id}")
        return 2
    if tool_id not in {tool["id"] for tool in rapp["tools"]}:
        print(f"rApp error: unknown tool {tool_id} for {rapp_id}")
        return 2
    if rapp.get("status") == "deprecated":
        print(f"rApp error: {rapp_id} is deprecated; use the current release")
        return 3
    kpm = fetch_recent_kpm()
    result = decide(rapp, tool_id, kpm)
    status = "applied" if is_apply_tool(tool_id) else "recommended"
    if is_apply_tool(tool_id):
        result["policy_path"] = str(write_policy(rapp, tool_id, result))
    print(f"rApp ack: {rapp_id} {tool_id} {status}")
    print(json.dumps(result, sort_keys=True))
    # Keep the process alive for the configured window so the scheduler sees
    # a running action and conflicting workflows contend for the lease.
    end = time.time() + max(0, duration_s)
    while time.time() < end:
        time.sleep(1.0)
    print(f"rApp {rapp_id} {tool_id} finished")
    return 0


def serve(port: int) -> int:  # pragma: no cover - optional
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        print(f"mcp package unavailable: {exc}", file=sys.stderr)
        return 1
    server = FastMCP("flexric-rapp-directory")
    catalog = load_catalog()
    for rapp_id, rapp in catalog.items():
        for tool in rapp["tools"]:
            def make(rid: str, tid: str):
                def handler() -> str:
                    kpm = fetch_recent_kpm()
                    result = decide(catalog[rid], tid, kpm)
                    if is_apply_tool(tid):
                        result["policy_path"] = str(write_policy(catalog[rid], tid, result))
                    return json.dumps(result)
                handler.__name__ = f"{rid.replace('.', '_')}__{tid}"
                return handler
            server.tool(name=f"{rapp_id}.{tool['id']}", description=tool["description"])(make(rapp_id, tool["id"]))
    server.settings.port = port
    server.run(transport="streamable-http")
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Emulated rApp runtime for the AppWeaver rApp Directory.")
    parser.add_argument("--rapp")
    parser.add_argument("--tool")
    parser.add_argument("--duration-s", type=int, default=10)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args(argv)
    if args.serve:
        return serve(args.port)
    if not args.rapp or not args.tool:
        parser.error("--rapp and --tool are required unless --serve is given")
    return run_tool(args.rapp, args.tool, args.duration_s)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
