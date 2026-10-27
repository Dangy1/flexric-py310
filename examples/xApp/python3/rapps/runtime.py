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

def fetch_recent_kpm(limit: int = 200, timeout_s: float = 3.0) -> Dict[str, Any]:
    """Return {'available': bool, 'cells': {cell_id: {metric: latest}}, 'detail': str}."""
    try:
        response = requests.get(f"{KPM_BUS_URL}/records", params={"limit": limit}, timeout=timeout_s)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return {"available": False, "cells": {}, "detail": f"KPM bus unavailable: {exc}"}
    cells: Dict[str, Dict[str, float]] = {}
    records = payload.get("records") if isinstance(payload, dict) else payload
    for record in list(records or []):
        cell = str(record.get("cell") or record.get("e2_node") or record.get("ue_id") or "cell-0")
        metrics = record.get("metrics") or record.get("meas") or {}
        if isinstance(metrics, dict):
            for name, value in metrics.items():
                try:
                    cells.setdefault(cell, {})[str(name)] = float(value)
                except (TypeError, ValueError):
                    continue
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
    return {**base, "decision": {}}


def is_apply_tool(tool_id: str) -> bool:
    stem = tool_id.split("_", 1)[-1] if "_" in tool_id and tool_id.split("_", 1)[0] in {"northwind", "kestrel", "orion", "helix", "vtt", "aalto"} else tool_id
    return stem.split("_")[0] in {"apply", "set", "execute", "tune", "wake", "rollback", "clear"}


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
