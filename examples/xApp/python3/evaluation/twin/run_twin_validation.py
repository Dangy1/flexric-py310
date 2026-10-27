#!/usr/bin/env python3
"""Twin-vs-live KPI validation for AppWeaver workflows on ns-O-RAN-flexric (T6).

Substrate: ns-3 + mmWave/5G-LENA (`scenario-zero-with_parallel_loging`) attached to the pinned FlexRIC
(`~/flexric-taap`, E2AP v1.01, KPM v3, RC v1.03) through `xapp_appweaver_actuator` (KPM capture + RC
command execution). Each run gets its own nearRT-RIC on its own ports so runs can execute in parallel.

  twin  = ns-3 instance A: RngRun = seed, N_Ues = TWIN_UES
  live  = ns-3 instance B: RngRun = seed + 100 (independent UE drop, mobility, fading) and
          N_Ues = LIVE_UES (+25% offered load: every UE carries a fixed 3.2 Mb/s CBR flow)

Workflows (chains from intents_v2.json; decisions by the AppWeaver rApp models in rapps/runtime.py):
  energy_saving    KPM -> RAPP.ENERGY_SAVING -> RC                        (handover + cell switch-off)
  traffic_steering KPM -> RAPP.TRAFFIC_STEERING -> RC                     (handover of 20% of the hot cell)
  qoe_steering     KPM -> RAPP.QOE_PREDICTION -> RAPP.TRAFFIC_STEERING -> RC (handover out of at-risk cells)
  noop             KPM only (counterfactual baseline)

KPI delta of a workflow on an instance = workflow run - noop run of the same instance (same seed),
averaged over the sim-time window [T_ACT + SETTLE, SIM_TIME]. Predicted delta = twin delta;
actual delta = live delta. Output: one JSON per run + summary.json/.md in --out.

Usage (flexric-py310 env):
  python run_twin_validation.py --out <dir> --pairs 5 --parallel 4
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]  # examples/xApp/python3
sys.path.insert(0, str(REPO / "rapps"))
import runtime as rapp_runtime  # noqa: E402  (AppWeaver emulated rApp decision models)

FLEXRIC_TAAP = Path(os.getenv("FLEXRIC_TAAP", str(Path.home() / "flexric-taap")))
NS3_DIR = Path(os.getenv("NS3_DIR", str(Path.home() / "ns-oran-flexric" / "mmwave-LENA-oran")))
SCENARIO = "scenario-zero-with_parallel_loging"
NS3_BIN = NS3_DIR / "build" / "scratch" / f"ns3.42-{SCENARIO}-optimized"
RIC_BIN = FLEXRIC_TAAP / "build" / "examples" / "ric" / "nearRT-RIC"
RIC_LIBS = FLEXRIC_TAAP / "install" / "lib" / "flexric"
ACTUATOR = Path(os.getenv("APPWEAVER_ACTUATOR", str(REPO.parents[2] / "build" / "examples" / "xApp" / "python3" / "evaluation" / "twin" / "build" / "xapp_appweaver_actuator")))

N_GNB = 4
TWIN_UES = 8
LIVE_UES = 10
IND_PERIOD = 0.1
SIM_TIME = 8.0
T_ACT = 1.5          # sim time at which the composed workflow runs
SETTLE = 0.5         # handover / switch-off settling before the KPI window opens
CELL_OFF_DELAY = 0.3  # sim seconds between the handovers and the switch-off of a sleeping cell

WORKFLOWS: Dict[str, List[str]] = {
    "noop": ["KPM"],
    "energy_saving": ["KPM", "RAPP.ENERGY_SAVING", "RC"],
    "traffic_steering": ["KPM", "RAPP.TRAFFIC_STEERING", "RC"],
    "qoe_steering": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.TRAFFIC_STEERING", "RC"],
}
DU_MEAS = {"RRU.PrbUsedDl.UEID", "DRB.UEThpDl.UEID", "DRB.BufferSize.Qos.UEID"}
KPIS = ["prb_used_dl", "dl_throughput_mbps", "dl_buffer_kbytes", "energy_j_per_s"]


# ---------------------------------------------------------------- KPM parsing
class KpmState:
    """Incrementally parses the actuator's KPM CSV into per-(gNB, indication) aggregates."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.header_seen = False
        self.ind_index: Dict[int, Dict[int, int]] = defaultdict(dict)  # nb_id -> collect_start -> k
        self.per_ind: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.ue_serving: Dict[int, int] = {}
        self.ue_serving_sinr: Dict[int, float] = {}
        self.ue_neigh: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.ue_thp: Dict[int, float] = {}
        self.ue_prb: Dict[int, float] = {}
        self._pending_neigh: Dict[Tuple[int, int], float] = {}

    def sim_time(self) -> float:
        return max((len(v) for v in self.ind_index.values()), default=0) * IND_PERIOD

    def poll(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self.offset)
            while True:
                line = handle.readline()
                if not line or not line.endswith("\n"):
                    break
                self.offset = handle.tell()
                if not self.header_seen:
                    self.header_seen = True
                    if line.startswith("wall_us"):
                        continue
                self._row(line.rstrip("\n").split(","))

    def _row(self, row: List[str]) -> None:
        if len(row) < 8 or not row[7]:
            return
        try:
            start, nb_id, imsi, idx, value = int(row[1]), int(row[3]), int(row[4]), int(row[6]), float(row[7])
        except ValueError:
            return
        meas = row[5]
        if nb_id < 2:  # LTE eNB (cell 1): anchor only, not a capacity cell
            return
        # One DU report per gNB per indication period; CU-UP / CU-CP reports carry their own
        # collect_start, so only DU rows define the indication clock.
        index = self.ind_index[nb_id]
        if meas in DU_MEAS and start not in index:
            index[start] = len(index)
        k = index.get(start, -1)
        if meas == "RRU.PrbUsedDl.UEID":
            self.per_ind[(nb_id, k)]["prb"] += value
            self.ue_prb[imsi] = value
        elif meas == "DRB.UEThpDl.UEID":
            self.per_ind[(nb_id, k)]["thp_kbps"] += value
            self.ue_thp[imsi] = value
        elif meas == "DRB.BufferSize.Qos.UEID":
            self.per_ind[(nb_id, k)]["buffer_bytes"] += value
        elif meas.startswith("L3servingSINR3gpp_cell_"):
            # L3servingSINR3gpp_cell_<c>_UEID_<imsi>
            parts = meas.split("_")
            try:
                cell, ue = int(parts[2]), int(parts[4])
            except (IndexError, ValueError):
                return
            self.ue_serving[ue] = cell
            self.ue_serving_sinr[ue] = value
        elif meas.startswith("L3neighSINRListOf_UEID_"):
            # L3neighSINRListOf_UEID_<imsi>_of_Cell_<c>: records alternate SINR (even idx) / neighbour id (odd idx)
            parts = meas.split("_")
            try:
                ue = int(parts[2])
            except (IndexError, ValueError):
                return
            if idx % 2 == 0:
                self._pending_neigh[(ue, idx)] = value
            else:
                sinr = self._pending_neigh.pop((ue, idx - 1), None)
                if sinr is not None and int(value) >= 2:
                    self.ue_neigh[ue][int(value)] = sinr

    def cells(self) -> List[int]:
        return sorted(self.ind_index)

    def snapshot(self, window_s: float = 0.5) -> Dict[str, Any]:
        """Per-cell KPM over the last window, in the shape rapps/runtime.decide() consumes."""
        n = max(1, int(round(window_s / IND_PERIOD)))
        cells: Dict[str, Dict[str, float]] = {}
        for nb_id, index in self.ind_index.items():
            last = len(index)
            ks = range(max(0, last - n), last)
            prb = [self.per_ind[(nb_id, k)]["prb"] for k in ks]
            ues = [u for u, c in self.ue_serving.items() if c == nb_id]
            thp = [self.per_ind[(nb_id, k)]["thp_kbps"] for k in ks]
            cells[str(nb_id)] = {
                "RRU.PrbTotDl": sum(prb) / len(prb) if prb else 0.0,
                # per-UE average downlink throughput in Mbit/s (the QoE model's input scale)
                "DRB.UEThpDl": (sum(thp) / len(thp) / 1000.0 / max(1, len(ues))) if thp else 0.0,
            }
        # Same normalisation as rapps/runtime.fetch_recent_kpm(): PRB counts scaled by the cluster maximum
        peak = max((c["RRU.PrbTotDl"] for c in cells.values()), default=0.0)
        if peak > 1.0:
            for c in cells.values():
                c["RRU.PrbTotDl"] = round(c["RRU.PrbTotDl"] / peak, 3)
        return {"available": bool(cells), "cells": cells, "detail": "ns-3 KPM via xapp_appweaver_actuator"}

    def window_kpis(self, k0: int, k1: int, gnbs: List[int]) -> Dict[str, float]:
        bins = range(k0, k1)
        prb = [sum(self.per_ind.get((g, k), {}).get("prb", 0.0) for g in gnbs) for k in bins]
        thp = [sum(self.per_ind.get((g, k), {}).get("thp_kbps", 0.0) for g in gnbs) for k in bins]
        buf = [sum(self.per_ind.get((g, k), {}).get("buffer_bytes", 0.0) for g in gnbs) for k in bins]
        return {
            "prb_used_dl": sum(prb) / len(prb) if prb else float("nan"),
            "dl_throughput_mbps": sum(thp) / len(thp) / 1000.0 if thp else float("nan"),
            "dl_buffer_kbytes": sum(buf) / len(buf) / 1000.0 if buf else float("nan"),
        }


def energy_window(out_dir: Path, gnbs: List[int], t0: float, t1: float) -> float:
    """Joules per simulated second consumed by all gNBs in [t0, t1] (energyfilecell<c>.csv: t,total_J,diff_J)."""
    total = 0.0
    for cell in gnbs:
        path = out_dir / f"energyfilecell{cell}.csv"
        if not path.exists():
            return float("nan")
        series = []
        for row in csv.reader(path.open()):
            try:
                series.append((float(row[0]), float(row[1])))
            except (ValueError, IndexError):
                continue
        if not series:
            return float("nan")
        at = lambda t: min(series, key=lambda p: abs(p[0] - t))[1]  # noqa: E731
        total += at(t1) - at(t0)
    return total / max(1e-9, t1 - t0)


# ---------------------------------------------------------------- workflow -> RC commands
def _rapp(family: str) -> Dict[str, Any]:
    return rapp_runtime.load_catalog()[f"rapp.{family}"]


def _best_target(state: KpmState, ue: int, exclude: set, prefer: Optional[int] = None) -> Optional[int]:
    neigh = {c: s for c, s in state.ue_neigh.get(ue, {}).items() if c not in exclude and c in state.ind_index}
    if prefer is not None and prefer in neigh:
        return prefer
    return max(neigh, key=neigh.get) if neigh else None


def decide_policy(workflow: str, state: KpmState) -> Dict[str, Any]:
    """Run the workflow's rApp chain on a KPM snapshot. The result is a cell-level policy (which cells
    sleep, which cells shed load and where to), portable between twin and live like an A1 policy."""
    kpm = state.snapshot()
    trace: Dict[str, Any] = {"kpm_snapshot": kpm["cells"], "steps": []}
    policy: Dict[str, Any] = {"workflow": workflow, "sleep_cells": [], "shed": [], "trace": trace}
    if workflow == "energy_saving":
        decision = rapp_runtime.decide(_rapp("energy_saving"), "recommend_sleep_cells", kpm)["decision"]
        trace["steps"].append({"rapp": "energy_saving", "decision": decision})
        policy["sleep_cells"] = [int(c) for c in decision.get("cells_to_sleep", [])]
    elif workflow == "traffic_steering":
        ts = rapp_runtime.decide(_rapp("traffic_steering"), "recommend_steering", kpm)["decision"]
        trace["steps"].append({"rapp": "traffic_steering", "decision": ts})
        if ts.get("from_cell") and ts.get("ue_share_pct"):
            policy["shed"].append({"from": int(ts["from_cell"]), "to": int(ts["to_cell"]), "share": ts["ue_share_pct"] / 100.0})
    elif workflow == "qoe_steering":
        qoe = rapp_runtime.decide(_rapp("qoe_prediction"), "predict_qoe", kpm)["decision"]
        trace["steps"].append({"rapp": "qoe_prediction", "decision": qoe})
        mos = {int(c): v for c, v in (qoe.get("mos_forecast") or {}).items()}
        at_risk = [int(c) for c in qoe.get("at_risk_cells", [])]
        if mos and at_risk:
            # Shed only from at-risk cells forecast below the median MOS (if every cell is at risk, moving
            # users between equally bad cells helps nobody).
            median = sorted(mos.values())[len(mos) // 2]
            at_risk = [c for c in at_risk if mos.get(c, median) < median]
        # The steering rApp consumes the QoE forecast: 20% of each source cell's UEs (weakest serving
        # SINR first) leave it, preferably towards the steering rApp's least-loaded cell.
        ts = rapp_runtime.decide(_rapp("traffic_steering"), "recommend_steering", kpm)["decision"]
        trace["steps"].append({"rapp": "traffic_steering", "decision": ts})
        cold = int(ts["to_cell"]) if ts.get("to_cell") and int(ts["to_cell"]) not in at_risk else None
        policy["shed"] = [{"from": c, "to": cold, "share": 0.2, "avoid": at_risk} for c in at_risk]
    return policy


def resolve_commands(policy: Dict[str, Any], state: KpmState) -> List[Tuple[float, str]]:
    """Turn a cell-level policy into RC commands on the instance that executes it (UEs are resolved
    from this instance's own KPM, as an RC executor would)."""
    commands: List[Tuple[float, str]] = []
    gnbs = set(state.cells())
    serving = lambda c: [u for u, s in state.ue_serving.items() if s == c]  # noqa: E731
    asleep: set = set()
    for cell in policy.get("sleep_cells", []):
        if len(gnbs - asleep - {cell}) < max(1, len(gnbs) // 2):
            break  # coverage guard: keep at least half of the gNBs on (documented)
        moves = [(u, _best_target(state, u, asleep | {cell})) for u in serving(cell)]
        if any(t is None for _, t in moves):
            continue  # a served UE has no awake neighbour: do not switch the cell off
        commands += [(0.0, f"HO {u} {t}") for u, t in moves]
        commands.append((CELL_OFF_DELAY, f"OFF {cell}"))
        asleep.add(cell)
    for shed in policy.get("shed", []):
        cell, prefer = shed["from"], shed.get("to")
        avoid = set(shed.get("avoid") or []) | {cell}
        n = math.ceil(shed["share"] * len(serving(cell)))
        if prefer is not None:  # best SINR towards the preferred target first
            ranked = sorted(serving(cell), key=lambda u: -state.ue_neigh.get(u, {}).get(prefer, -1e9))
        else:  # cell-edge UEs (weakest serving SINR) first
            ranked = sorted(serving(cell), key=lambda u: state.ue_serving_sinr.get(u, 0.0))
        moved = 0
        for ue in ranked:
            if moved >= n:
                break
            target = _best_target(state, ue, avoid, prefer)
            if target is not None:
                commands.append((0.0, f"HO {ue} {target}"))
                moved += 1
    return commands


# ---------------------------------------------------------------- one simulation
LIVE_PROCS: set = set()


def _kill_group(proc: subprocess.Popen) -> None:
    """SIGTERM the process group, SIGKILL after 5 s (an xApp whose RIC is gone ignores SIGTERM)."""
    if proc.poll() is not None:
        return
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
            proc.wait(timeout=wait)
            return
        except Exception:
            continue


def _on_exit_signal(signum, frame):  # pragma: no cover - operator interrupt
    for proc in list(LIVE_PROCS):
        _kill_group(proc)
    raise SystemExit(128 + signum)


def _wait_for(predicate, timeout_s: float, interval: float = 0.5) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def run_instance(role: str, seed: int, n_ues: int, workflow: str, slot: int, out_root: Path,
                 policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    run_dir = out_root / "runs" / f"{role}_s{seed}_{workflow}"
    result_path = run_dir / "result.json"
    if result_path.exists():
        cached = json.loads(result_path.read_text())
        if cached.get("ok"):
            return cached  # failed runs are retried
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "ns3_out").mkdir(parents=True)
    e2_port, e42_port = 36500 + 10 * slot, 36501 + 10 * slot
    # FlexRIC keeps conf paths in a short fixed buffer (FR_CONF_FILE_LEN): use a short per-slot path.
    short = Path(f"/tmp/aw_t6/s{slot}")
    short.mkdir(parents=True, exist_ok=True)
    conf = short / "flexric.conf"
    conf.write_text(f"[NEAR-RIC]\nNEAR_RIC_IP = 127.0.0.1\n\n[XAPP]\nDB_DIR = {short}/\n\n[PORTS]\nNEAR_RIC_PORT = {e2_port}\nE42_PORT = {e42_port}\n")
    shutil.copy(conf, run_dir / "flexric.conf")
    procs: List[subprocess.Popen] = []
    started = time.time()
    result: Dict[str, Any] = {"role": role, "seed": seed, "n_ues": n_ues, "workflow": workflow,
                              "chain": WORKFLOWS[workflow], "sim_time_s": SIM_TIME, "t_act_s": T_ACT}
    try:
        ric = subprocess.Popen([str(RIC_BIN), "-c", str(conf), "-p", f"{RIC_LIBS}/"], stdout=(run_dir / "ric.log").open("w"),
                               stderr=subprocess.STDOUT, start_new_session=True)
        procs.append(ric)
        LIVE_PROCS.add(ric)
        _wait_for(lambda: "Initializing Task Manager" in (run_dir / "ric.log").read_text(errors="replace"), 10, 0.1)
        ns3_args = [
            str(NS3_BIN), "--e2TermIp=127.0.0.1", f"--ns3::MmWaveHelper::E2Port={e2_port}",
            f"--ns3::MmWaveHelper::E2LocalPort={38500 + 100 * slot}", "--hoSinrDifference=3",
            f"--indicationPeriodicity={IND_PERIOD}", f"--simTime={SIM_TIME}", "--KPM_E2functionID=2",
            "--RC_E2functionID=3", f"--N_MmWaveEnbNodes={N_GNB}", f"--N_Ues={n_ues}", "--CenterFrequency=3.5e9",
            "--Bandwidth=20e6", "--IntersideDistanceUEs=500", "--IntersideDistanceCells=600", f"--RngRun={seed}",
        ]
        (run_dir / "ns3.cmd").write_text(" ".join(ns3_args) + "\n")
        env = {**os.environ, "LD_LIBRARY_PATH": f"{NS3_DIR / 'build' / 'lib'}:{os.environ.get('LD_LIBRARY_PATH', '')}"}
        ns3 = subprocess.Popen(ns3_args, cwd=run_dir / "ns3_out", env=env, stdout=(run_dir / "ns3.log").open("w"),
                               stderr=subprocess.STDOUT, start_new_session=True)
        procs.append(ns3)
        LIVE_PROCS.add(ns3)
        want = N_GNB + 1
        if not _wait_for(lambda: (run_dir / "ns3.log").read_text(errors="replace").count("Received SETUP-RESPONSE-SUCCESS") >= want
                         or ns3.poll() is not None, 300):
            raise RuntimeError("E2 setup did not complete in 300 s")
        if ns3.poll() is not None:
            raise RuntimeError(f"ns-3 exited early (rc={ns3.returncode})")
        kpm_csv, cmd_file, ack_file = run_dir / "kpm.csv", run_dir / "rc_commands.txt", run_dir / "rc_acks.txt"
        cmd_file.write_text("")
        act_env = {**os.environ, "KPM_CSV": str(kpm_csv), "RC_CMD_FILE": str(cmd_file), "RC_ACK_FILE": str(ack_file)}
        actuator = subprocess.Popen([str(ACTUATOR), "-c", str(conf), "-p", f"{RIC_LIBS}/"], env=act_env, cwd=run_dir,
                                    stdout=(run_dir / "actuator.out").open("w"), stderr=(run_dir / "actuator.log").open("w"),
                                    start_new_session=True)
        procs.append(actuator)
        LIVE_PROCS.add(actuator)
        state = KpmState(kpm_csv)
        pending: List[Tuple[float, str]] = []
        acted = False
        if policy is not None:
            result["policy_from"] = "twin"
        while ns3.poll() is None:
            state.poll()
            t = state.sim_time()
            if not acted and t >= T_ACT:
                acted = True
                result["act_sim_time_s"] = round(t, 2)
                if workflow != "noop":
                    if policy is None:  # twin: AppWeaver decides here (validate before deploy)
                        policy = decide_policy(workflow, state)
                    result["policy"] = policy
                    commands = resolve_commands(policy, state)
                    result["commands"] = [c for _, c in commands]
                    pending = [(t + delay, c) for delay, c in commands]
            due = [c for when, c in pending if t >= when]
            if due:
                with cmd_file.open("a") as handle:
                    handle.write("".join(f"{c}\n" for c in due))
                pending = [(w, c) for w, c in pending if c not in due]
            if actuator.poll() is not None:
                raise RuntimeError(f"actuator exited (rc={actuator.returncode})")
            time.sleep(0.2)
        state.poll()
        gnbs = list(range(2, N_GNB + 2))
        # Indication k covers report time k*IND_PERIOD after the first report; the first report arrives
        # at sim time `offset` (E2 setup + subscription), estimated from the final count.
        n_final = max(len(state.ind_index.get(g, {})) for g in gnbs)
        offset = max(0.0, SIM_TIME - n_final * IND_PERIOD)
        k0 = int(round((T_ACT + SETTLE) / IND_PERIOD))
        k1 = int(round((SIM_TIME - offset) / IND_PERIOD)) - 1
        t0, t1 = offset + k0 * IND_PERIOD, offset + k1 * IND_PERIOD
        result["kpi"] = {**state.window_kpis(k0, k1, gnbs), "energy_j_per_s": energy_window(run_dir / "ns3_out", gnbs, t0, t1)}
        result["kpi_window_indications"] = [k0, k1]
        result["kpi_window_sim_s"] = [round(t0, 2), round(t1, 2)]
        result["first_report_sim_s"] = round(offset, 2)
        result["indications_per_gnb"] = {str(g): len(state.ind_index.get(g, {})) for g in gnbs}
        result["rc_acks"] = ack_file.read_text().splitlines() if ack_file.exists() else []
        result["ns3_returncode"] = ns3.returncode
        result["ok"] = ns3.returncode == 0 and result.get("act_sim_time_s") is not None
    except Exception as exc:  # recorded, never hidden
        result["ok"] = False
        result["error"] = str(exc)
    finally:
        for proc in reversed(procs):
            _kill_group(proc)
            LIVE_PROCS.discard(proc)
        result["wall_s"] = round(time.time() - started, 1)
        for trace in (run_dir / "ns3_out").glob("*.txt"):
            if trace.stat().st_size > 5_000_000:
                trace.unlink()  # large ns-3 traces are not needed for the KPI window
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


# ---------------------------------------------------------------- analysis
def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def analyse(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {(r["role"], r["seed"] if r["role"] == "twin" else r["seed"] - 100, r["workflow"]): r for r in results if r.get("ok")}
    pairs = sorted({k[1] for k in by})
    rows = []
    for pair in pairs:
        for wf in [w for w in WORKFLOWS if w != "noop"]:
            keys = [("twin", pair, wf), ("twin", pair, "noop"), ("live", pair, wf), ("live", pair, "noop")]
            if not all(k in by for k in keys):
                continue
            for kpi in KPIS:
                pred = by[keys[0]]["kpi"][kpi] - by[keys[1]]["kpi"][kpi]
                act = by[keys[2]]["kpi"][kpi] - by[keys[3]]["kpi"][kpi]
                rows.append({"pair": pair, "workflow": wf, "kpi": kpi, "predicted_delta": pred, "actual_delta": act,
                             "twin_noop": by[keys[1]]["kpi"][kpi], "live_noop": by[keys[3]]["kpi"][kpi],
                             "twin_commands": len(by[keys[0]].get("commands", [])), "live_commands": len(by[keys[2]].get("commands", []))})
    summary: Dict[str, Any] = {"rows": rows, "by_workflow_kpi": {}}
    for wf in [w for w in WORKFLOWS if w != "noop"]:
        for kpi in KPIS:
            sel = [r for r in rows if r["workflow"] == wf and r["kpi"] == kpi and not math.isnan(r["actual_delta"]) and not math.isnan(r["predicted_delta"])]
            if not sel:
                continue
            ape = [abs(r["predicted_delta"] - r["actual_delta"]) / abs(r["actual_delta"]) for r in sel if abs(r["actual_delta"]) > 1e-9]
            sign = [((r["predicted_delta"] > 0) - (r["predicted_delta"] < 0)) == ((r["actual_delta"] > 0) - (r["actual_delta"] < 0)) for r in sel]
            summary["by_workflow_kpi"][f"{wf}/{kpi}"] = {
                "pairs": len(sel),
                "mean_predicted_delta": sum(r["predicted_delta"] for r in sel) / len(sel),
                "mean_actual_delta": sum(r["actual_delta"] for r in sel) / len(sel),
                "mape_pct": 100 * sum(ape) / len(ape) if ape else None,
                "mape_pairs": len(ape),
                "sign_agreement": sum(sign) / len(sign),
                # predicted vs actual *relative* change (delta / same-instance noop level), percentage points;
                # robust where the actual delta is near zero and MAPE explodes
                "mean_predicted_rel_pct": _mean([100 * r["predicted_delta"] / r["twin_noop"] for r in sel if r["twin_noop"]]),
                "mean_abs_rel_error_pp": _mean([abs(100 * r["predicted_delta"] / r["twin_noop"] - 100 * r["actual_delta"] / r["live_noop"])
                                                for r in sel if r["twin_noop"] and r["live_noop"]]),
                # relative change of the live network (actual delta / live noop level)
                "mean_actual_rel_pct": 100 * sum(r["actual_delta"] / r["live_noop"] for r in sel if r["live_noop"]) / max(1, sum(1 for r in sel if r["live_noop"])),
            }
    return summary


def write_report(out: Path, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    failed = [r for r in results if not r.get("ok")]
    acted = defaultdict(int)
    for r in results:
        if r.get("ok") and r["workflow"] != "noop" and r.get("commands"):
            acted[(r["role"], r["workflow"])] += 1
    lines = [f"# Twin-vs-live results - `{out.name}`", "",
             f"Runs: {len(results)} ({len(failed)} failed). Pairs analysed per workflow/KPI in the table.", "",
             "| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for key, st in summary["by_workflow_kpi"].items():
        wf, kpi = key.split("/")
        fmt = lambda v: "--" if v is None else f"{v:+.1f}%"  # noqa: E731
        err = "--" if st.get("mean_abs_rel_error_pp") is None else f"{st['mean_abs_rel_error_pp']:.1f}"
        mape = "--" if st.get("mape_pct") is None else f"{st['mape_pct']:.0f}% (n={st['mape_pairs']})"
        lines.append(f"| {wf} | {kpi} | {st['pairs']} | {st['mean_predicted_delta']:+.2f} | {st['mean_actual_delta']:+.2f} | "
                     f"{fmt(st.get('mean_predicted_rel_pct'))} | "
                     f"{fmt(st.get('mean_actual_rel_pct'))} | {err} | {mape} | {100 * st['sign_agreement']:.0f}% |")
    lines += ["", "Runs in which the deployed policy produced RC commands:", ""]
    lines += [f"- {role} {wf}: {n}" for (role, wf), n in sorted(acted.items())]
    if failed:
        lines += ["", "Failed runs:", ""] + [f"- {r['role']} s{r['seed']} {r['workflow']}: {r.get('error')}" for r in failed]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--workflows", nargs="+", default=list(WORKFLOWS))
    parser.add_argument("--only", default="", help="role:seed:workflow for a single smoke run")
    parser.add_argument("--twin-ues", type=int, default=TWIN_UES,
                        help="UEs in the twin (default 8; set to the live count for a load-calibrated twin)")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _on_exit_signal)
    signal.signal(signal.SIGINT, _on_exit_signal)
    # A unit is (twin job, live job) of one (pair, workflow): the live run deploys the policy the twin
    # run decided, so the two run in order on the same slot.
    units: List[List[Tuple[str, int, int, str]]] = []
    if args.only:
        role, seed, wf = args.only.split(":")
        units.append([(role, int(seed), args.twin_ues if role == "twin" else LIVE_UES, wf)])
    else:
        for pair in range(1, args.pairs + 1):
            for wf in args.workflows:
                units.append([("twin", pair, args.twin_ues, wf), ("live", pair + 100, LIVE_UES, wf)])
    n_jobs = sum(len(u) for u in units)
    (out / "manifest.json").write_text(json.dumps({
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "scenario": SCENARIO, "ns3_bin": str(NS3_BIN),
        "flexric": str(FLEXRIC_TAAP), "n_gnb": N_GNB, "twin_ues": args.twin_ues, "live_ues": LIVE_UES,
        "sim_time_s": SIM_TIME, "t_act_s": T_ACT, "settle_s": SETTLE, "indication_period_s": IND_PERIOD,
        "workflows": WORKFLOWS, "jobs": n_jobs, "kpis": KPIS,
        "protocol": "policy decided on the twin at t_act, deployed unchanged on live; deltas vs same-instance noop",
    }, indent=2))
    results: List[Dict[str, Any]] = []
    done = [0]

    def run_unit(unit_slot):
        unit, slot = unit_slot
        out_results, policy = [], None
        for role, seed, n_ues, wf in unit:
            res = run_instance(role, seed, n_ues, wf, slot=slot, out_root=out, policy=policy)
            policy = res.get("policy") if role == "twin" else policy
            done[0] += 1
            print(f"[{done[0]}/{n_jobs}] {role} s{seed} {wf} ok={res.get('ok')} wall={res.get('wall_s')}s "
                  f"cmds={res.get('commands', [])} {res.get('error', '')}", flush=True)
            out_results.append(res)
        return out_results

    # Slot s only ever runs units s, s+P, ... so two simulations never share RIC / E2 ports.
    lanes = [[(u, s) for i, u in enumerate(units) if i % args.parallel == s] for s in range(args.parallel)]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for lane_results in pool.map(lambda lane: [r for unit in lane for r in run_unit(unit)], lanes):
            results.extend(lane_results)
    summary = analyse(results)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    write_report(out, summary, results)
    print(json.dumps(summary["by_workflow_kpi"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
