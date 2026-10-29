#!/usr/bin/env python3
"""Twin-vs-live KPI validation and deploy gate for AppWeaver workflows on ns-O-RAN-flexric (T6 / T6v2).

Substrate: ns-3 + mmWave/5G-LENA (`scenario-zero-with_parallel_loging`) attached to the pinned FlexRIC
(`~/flexric-taap`, E2AP v1.01, KPM v3, RC v1.03) through `xapp_appweaver_actuator` (KPM capture + RC
command execution). Each run gets its own nearRT-RIC on its own ports (36500 + 10*slot) so runs can
execute in parallel next to the simulator session's RIC (36423) and AppWeaver's live stack (36421).

  twin  = ns-3 instance A: RngRun = pair, N_Ues = --twin-ues
  live  = ns-3 instance B: RngRun = pair + 100 (independent UE drop, mobility, fading) and
          N_Ues = LIVE_UES (every UE carries a fixed 3.2 Mb/s CBR flow)

State sync levels of the twin (--sync):
  none       twin knows topology/configuration only (twin 8 UEs vs live 10: load unknown)
  load       twin UE count = live UE count (--twin-ues 10)
  positions  load + the live run's UE positions at t_act as the twin's initial UE positions
             (scenario GlobalValue uePositionFile, CSV ue_index,x,y,z in the ue_position.txt frame)

Workflows (chains from intents_v2.json; decisions by the AppWeaver rApp models in rapps/runtime.py):
  energy_saving    KPM -> RAPP.ENERGY_SAVING -> RC                        (handover + cell switch-off)
  traffic_steering KPM -> RAPP.TRAFFIC_STEERING -> RC                     (handover of 20% of the hot cell)
  qoe_steering     KPM -> RAPP.QOE_PREDICTION -> RAPP.TRAFFIC_STEERING -> RC (handover out of at-risk cells)
  noop             KPM only (counterfactual baseline)

Clock: since the simulator fixes of 2026-10-28 the KPM header `collectStartTime` is the simulated time
(us) and reporting starts at subscription, so t_act and the KPI window are absolute simulated times:
the workflow runs at T_ACT and KPIs are averaged over [T_ACT + SETTLE, SIM_TIME - IND_PERIOD).
KPI delta of a workflow on an instance = workflow run - noop run of the same instance (same seed).
Predicted delta = twin delta; actual delta = live delta.

Deploy gate (Validate-2): per (pair, workflow) the twin verdict accept/reject is computed from the
predicted deltas with the pre-declared thresholds in GATE (written to the manifest before any run) and
compared with the live outcome under the same thresholds; accuracy, precision/recall of "accept" with
Wilson 95% CIs per workflow and pooled go to summary.json/.md.

Usage (flexric-py310 env):
  python run_twin_validation.py --out <dir> --pairs 1-9 --parallel 2 [--twin-ues 10] [--sync positions]
         [--reuse-live-noop <base batch dir>] [--host-context "..."]
  python run_twin_validation.py --out <dir>/aa_noop_repeat --aa-of <batch dir> --pairs 1-4   # A/A noise
  python run_twin_validation.py --out <dir> --report-only                                  # re-analyse
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
GNBS = list(range(2, N_GNB + 2))  # cell ids of the mmWave gNBs (cell 1 = LTE anchor)
TWIN_UES = 8
LIVE_UES = 10
IND_PERIOD = 0.1
PERIOD_US = int(round(IND_PERIOD * 1e6))
SIM_TIME = 8.0
T_ACT = 2.0           # absolute simulated time (s) at which the composed workflow runs
MIN_HISTORY = 0.5     # KPM history (s) the decision snapshot needs before T_ACT
SETTLE = 0.5          # handover / switch-off settling before the KPI window opens
WINDOW = (T_ACT + SETTLE, SIM_TIME - IND_PERIOD)  # traffic stops at SIM_TIME - 0.1 s
CELL_OFF_DELAY = 0.3  # sim seconds between the handovers and the switch-off of a sleeping cell
PORT_BASE = 36500     # per-slot RIC ports (E2 = PORT_BASE + 10*slot, E42 = +1); never 36421/36422/36423

WORKFLOWS: Dict[str, List[str]] = {
    "noop": ["KPM"],
    "energy_saving": ["KPM", "RAPP.ENERGY_SAVING", "RC"],
    "traffic_steering": ["KPM", "RAPP.TRAFFIC_STEERING", "RC"],
    "qoe_steering": ["KPM", "RAPP.QOE_PREDICTION", "RAPP.TRAFFIC_STEERING", "RC"],
}
DU_MEAS = {"RRU.PrbUsedDl.UEID", "DRB.UEThpDl.UEID", "DRB.BufferSize.Qos.UEID"}
KPIS = ["prb_used_dl", "dl_throughput_mbps", "dl_delay_ms", "dl_buffer_kbytes", "energy_j_per_s"]
E2_KPIS = ["prb_used_dl", "dl_throughput_mbps", "dl_buffer_kbytes", "energy_j_per_s"]
# KPI source of the analysis (decisions always use the E2 KPM stream, as a RIC would). The E2 DU report's
# PRB/throughput window is the time since ns-3's own 100 ms DU logger last reset the shared calculator, i.e.
# the report phase, which since immediate reporting depends on the wall-clock time of the subscription:
# same-seed runs then differ by up to 13x in cell PRB. The ns-3 traces below do not depend on the phase.
KPI_SOURCE = {
    "version": "ns3-trace-v2",
    "prb_used_dl": "full-period PRB per 100 ms period (k*100, (k+1)*100] ms rebuilt from the two consumers of ns-3's shared DU "
                   "calculator: the E2 report at k*100+phi ms (window phi, kpm.csv) and the DU logger write at (k+1)*100 ms "
                   "(window 100-phi, du-cell-<c>.txt), weighted phi/100 and (100-phi)/100; sum of RRU.PrbUsedDl.UEID over UEs, "
                   "mean over the periods inside (t0, t1] (a cell with no UE = 0). Runs without sim-time KPM stamps (pre-fix): "
                   "DU logger alone",
    "dl_buffer_kbytes": "du-cell-<c>.txt: sum of DRB.BufferSize.Qos.UEID over UEs, same writes",
    "dl_throughput_mbps": "DlPdcpStats.txt (ns-3 PDCP stats at the LTE anchor, 0.25 s epochs): RxBytes received by all UEs "
                          "in the epochs inside [t0, t1], i.e. UE-received DL goodput incl. UEs left without service",
    "dl_delay_ms": "DlPdcpStats.txt: PDCP DL delay, mean weighted by nRxPDUs over the same epochs",
    "energy_j_per_s": "energyfilecell<c>.csv (ns-3 radio energy model), unchanged",
    "e2_kpm": "kpi_e2 / kpi_per_cell_e2: the same window from the E2 KPM stream (pre-2026-10-28 KPI source), reported in summary_e2kpm.*",
}

# Deploy-gate thresholds, declared before the T6v2 batches ran (copied into every manifest).
GATE: Dict[str, Dict[str, Any]] = {
    "energy_saving": {
        "accept_if": "energy_saving_pct >= 5 AND remaining_prb_increase_pct <= 30",
        "energy_saving_min_pct": 5.0,
        "remaining_prb_increase_max_pct": 30.0,
    },
    "traffic_steering": {
        "accept_if": "hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5",
        "hot_prb_reduction_min_pct": 5.0,
        "throughput_loss_max_pct": 5.0,
    },
    "qoe_steering": {
        "accept_if": "hot_prb_reduction_pct >= 5 AND throughput_loss_pct <= 5",
        "hot_prb_reduction_min_pct": 5.0,
        "throughput_loss_max_pct": 5.0,
    },
}
GATE_DEFINITIONS = {
    "energy_saving_pct": "-100 * (energy_wf - energy_noop) / energy_noop, all gNBs, J per simulated s in the KPI window",
    "remaining_prb_increase_pct": "100 * (PRB_wf - PRB_noop) / PRB_noop summed over the gNBs this instance did not switch off "
                                  "(its own OFF commands); noop sum 0 -> 0 if wf sum is 0 else +inf",
    "hot_prb_reduction_pct": "-100 * (PRB_wf - PRB_noop) / PRB_noop summed over the policy's source cells (shed.from); "
                             "no source cell or noop sum 0 -> undefined -> reject",
    "throughput_loss_pct": "-100 * (thp_wf - thp_noop) / thp_noop, all gNBs",
    "verdict": "accept iff every criterion of the workflow holds; twin verdict from predicted (twin) deltas, "
               "live outcome from measured (live) deltas, same thresholds",
}
EXCLUSION_RULE = ("a pair is excluded from the analysis iff one of its runs still fails after one automatic retry "
                  "(ns-3 abort, E2 setup timeout, no KPM before t_act); no replacement pairs are added")


# ---------------------------------------------------------------- KPM parsing
class KpmState:
    """Incrementally parses the actuator's KPM CSV (wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value).

    `collect_start_us` is simulated time; one DU report per gNB per indication period. A report is put in
    period bin floor(collect_start_us / PERIOD_US). Empty `value` = KPM noValue record: the report still
    marks the period, the value is not aggregated."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.header_seen = False
        self.bins: Dict[int, set] = defaultdict(set)  # nb_id -> period bins with a DU report
        self.per_bin: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.max_stamp_us = -1
        self.first_du_stamp_us: Optional[int] = None
        self.novalue_rows = 0
        self.ue_serving: Dict[int, int] = {}
        self.ue_serving_sinr: Dict[int, float] = {}
        self.ue_neigh: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.ue_thp: Dict[int, float] = {}
        self.ue_prb: Dict[int, float] = {}
        self._pending_neigh: Dict[Tuple[int, int], float] = {}

    def sim_time(self) -> float:
        """Simulated time of the latest report seen (s); -1 before the first report."""
        return self.max_stamp_us / 1e6 if self.max_stamp_us >= 0 else -1.0

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
        if len(row) < 8:
            return
        try:
            start, nb_id, imsi, idx = int(row[1]), int(row[3]), int(row[4]), int(row[6])
        except ValueError:
            return
        value: Optional[float]
        if row[7] == "":
            value = None
            self.novalue_rows += 1
        else:
            try:
                value = float(row[7])
            except ValueError:
                return
        self.max_stamp_us = max(self.max_stamp_us, start)
        meas = row[5]
        if nb_id < 2:  # LTE eNB (cell 1): anchor only, not a capacity cell
            return
        k = start // PERIOD_US
        if meas in DU_MEAS:
            self.bins[nb_id].add(k)
            if self.first_du_stamp_us is None or start < self.first_du_stamp_us:
                self.first_du_stamp_us = start
        if value is None:
            return
        if meas == "RRU.PrbUsedDl.UEID":
            self.per_bin[(nb_id, k)]["prb"] += value
            self.ue_prb[imsi] = value
        elif meas == "DRB.UEThpDl.UEID":
            self.per_bin[(nb_id, k)]["thp_kbps"] += value
            self.ue_thp[imsi] = value
        elif meas == "DRB.BufferSize.Qos.UEID":
            self.per_bin[(nb_id, k)]["buffer_bytes"] += value
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
        return sorted(self.bins)

    def snapshot(self, window_s: float = 0.5) -> Dict[str, Any]:
        """Per-cell KPM over each cell's last `window_s` of reports, in the shape rapps/runtime.decide() consumes."""
        n = max(1, int(round(window_s / IND_PERIOD)))
        cells: Dict[str, Dict[str, float]] = {}
        for nb_id, bins in self.bins.items():
            ks = sorted(bins)[-n:]
            prb = [self.per_bin.get((nb_id, k), {}).get("prb", 0.0) for k in ks]
            thp = [self.per_bin.get((nb_id, k), {}).get("thp_kbps", 0.0) for k in ks]
            ues = [u for u, c in self.ue_serving.items() if c == nb_id]
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

    def grid_aligned(self) -> bool:
        """True with the simulator's report-window fix (2026-10-28 fix 8): gNB reports are stamped on the
        100 ms tick and cover the window that ends there; before it, the stamp started a phi-ms window."""
        return self.first_du_stamp_us is not None and self.first_du_stamp_us % PERIOD_US == 0

    def window_bins(self, t0: float, t1: float) -> range:
        """Period bins of the KPI window (t0, t1]."""
        k0, k1 = int(round(t0 / IND_PERIOD)), int(round(t1 / IND_PERIOD))
        return range(k0 + 1, k1 + 1) if self.grid_aligned() else range(k0, k1)

    def window_kpis(self, t0: float, t1: float, gnbs: List[int]) -> Dict[str, Any]:
        """Mean over the period bins of [t0, t1) of the per-period sum over `gnbs` (a gNB without a report in
        a period, e.g. switched off with no UE, contributes 0). Also per-cell means for the gate."""
        bins = self.window_bins(t0, t1)
        keys = (("prb", "prb_used_dl", 1.0), ("thp_kbps", "dl_throughput_mbps", 1000.0), ("buffer_bytes", "dl_buffer_kbytes", 1000.0))
        per_cell: Dict[str, Dict[str, float]] = {}
        for g in gnbs:
            per_cell[str(g)] = {
                out: (sum(self.per_bin.get((g, k), {}).get(field, 0.0) for k in bins) / len(bins) / scale) if len(bins) else float("nan")
                for field, out, scale in keys
            }
        totals = {out: sum(per_cell[str(g)][out] for g in gnbs) for _, out, _ in keys}
        reported = sum(1 for k in bins if any(k in self.bins.get(g, ()) for g in gnbs))
        return {**totals, "per_cell": per_cell, "bins": len(bins), "bins_reported": reported}


def energy_window(out_dir: Path, gnbs: List[int], t0: float, t1: float, per_cell: bool = False):
    """Joules per simulated second consumed by the gNBs in [t0, t1] (energyfilecell<c>.csv: t,total_J,diff_J)."""
    total, cells = 0.0, {}
    for cell in gnbs:
        path = out_dir / f"energyfilecell{cell}.csv"
        if not path.exists():
            return (float("nan"), {}) if per_cell else float("nan")
        series = []
        for row in csv.reader(path.open()):
            try:
                series.append((float(row[0]), float(row[1])))
            except (ValueError, IndexError):
                continue
        if not series:
            return (float("nan"), {}) if per_cell else float("nan")
        at = lambda t: min(series, key=lambda p: abs(p[0] - t))[1]  # noqa: E731
        cells[str(cell)] = (at(t1) - at(t0)) / max(1e-9, t1 - t0)
        total += at(t1) - at(t0)
    value = total / max(1e-9, t1 - t0)
    return (value, cells) if per_cell else value


def _trace_simid(out_dir: Path) -> Optional[int]:
    """Run id (simid column of ue_position.txt), the time base of the ns-3 traces after simulator fix 9."""
    path = out_dir / "ue_position.txt"
    if not path.exists():
        return None
    with path.open() as handle:
        for row in csv.reader(handle):
            if len(row) >= 7 and row[6].isdigit():
                return int(row[6])
    return None


def du_trace_kpis(out_dir: Path, gnbs: List[int], t0: float, t1: float, e2: Optional["KpmState"] = None) -> Dict[str, Any]:
    """Per-cell PRB and RLC buffer from the ns-3 DU logger files du-cell-<c>.txt. Their timestamp is an
    uninitialised constant (m_startTime) + simulated ms; the logger writes every 100 ms from t = 0.1 s, so the
    constant is the smallest stamp of the run minus 100.

    The logger and the E2 DU report read and reset the same per-UE calculator. With `e2` (the run's KPM with
    sim-time stamps at phase phi ms after each 100 ms boundary) the PRB of period k is
    (phi * E2[k] + (100 - phi) * logger[(k+1)*100]) / 100; without it, the logger value alone."""
    rows: Dict[int, List[Tuple[int, float, float]]] = {}
    stamps: List[int] = []
    for cell in gnbs:
        path = out_dir / f"du-cell-{cell}.txt"
        rows[cell] = []
        if not path.exists():
            continue
        with path.open(errors="replace") as handle:
            reader = csv.reader(line.replace("\0", "") for line in handle)  # plmId carries raw bytes
            header = next(reader, [])
            try:
                i_prb, i_buf = header.index("RRU.PrbUsedDl.UEID"), header.index("DRB.BufferSize.Qos.UEID")
            except ValueError:
                raise RuntimeError(f"{path}: unexpected header")
            for row in reader:
                try:
                    rows[cell].append((int(row[0]), float(row[i_prb]), float(row[i_buf])))
                except (ValueError, IndexError):
                    continue
        stamps += [r[0] for r in rows[cell]]
    if not stamps:
        raise RuntimeError("no DU logger rows")
    base = min(stamps) - int(round(IND_PERIOD * 1000))
    simid = _trace_simid(out_dir)
    if simid is not None and all(0 < ts - simid <= SIM_TIME * 1000 and (ts - simid) % 100 == 0 for ts in stamps):
        base = simid  # simulator fix 9: trace timestamp = run id + sim ms (as ue_position.txt)
    span = max(stamps) - min(stamps)
    expected_span = int(round((SIM_TIME - 2 * IND_PERIOD) * 1000))
    if span != expected_span:  # no cell logged from 0.1 s to SIM_TIME - 0.1 s: the anchor is not trustworthy
        raise RuntimeError(f"DU logger span {span} ms != {expected_span} ms")
    writes = [w for w in range(int(round(t0 * 1000)) + 100, int(round(t1 * 1000)) + 1, 100)]
    phi = None
    if e2 is not None and e2.first_du_stamp_us is not None and not e2.grid_aligned():
        phi = (e2.first_du_stamp_us % PERIOD_US) / 1000.0  # ms after the 100 ms boundary (constant per run)
    per_cell: Dict[str, Dict[str, float]] = {}
    for cell in gnbs:
        prb, buf = defaultdict(float), defaultdict(float)
        for ts, p, b in rows[cell]:
            prb[ts - base] += p
            buf[ts - base] += b
        if phi is None:
            prb_periods = [prb.get(w, 0.0) for w in writes]
        else:
            prb_periods = [(phi * e2.per_bin.get((cell, w // 100 - 1), {}).get("prb", 0.0) + (100.0 - phi) * prb.get(w, 0.0)) / 100.0
                           for w in writes]
        per_cell[str(cell)] = {"prb_used_dl": sum(prb_periods) / len(writes),
                               "dl_buffer_kbytes": sum(buf.get(w, 0.0) for w in writes) / len(writes) / 1000.0}
    method = "logger" if phi is None else f"e2+logger, phi={phi:.3f} ms"
    if e2 is not None and e2.grid_aligned():
        method = "logger (E2 reports grid-aligned: same window)"
    return {"per_cell": per_cell, "writes": len(writes), "prb_method": method,
            "prb_used_dl": sum(c["prb_used_dl"] for c in per_cell.values()),
            "dl_buffer_kbytes": sum(c["dl_buffer_kbytes"] for c in per_cell.values())}


def pdcp_kpis(out_dir: Path, t0: float, t1: float) -> Dict[str, Any]:
    """UE-received DL throughput and PDCP delay from ns-3's DlPdcpStats.txt (start end CellId IMSI RNTI LCID
    nTxPDUs TxBytes nRxPDUs RxBytes delay ...), epochs inside [t0, t1]."""
    path = out_dir / "DlPdcpStats.txt"
    rx_bytes, pdus, delay_w, epochs = 0.0, 0.0, 0.0, set()
    with path.open() as handle:
        for line in handle:
            f = line.split()
            if len(f) < 11 or line.startswith("%"):
                continue
            start, end = float(f[0]), float(f[1])
            if start < t0 - 1e-9 or end > t1 + 1e-9:
                continue
            epochs.add((start, end))
            n, rx, delay = float(f[8]), float(f[9]), float(f[10])
            rx_bytes += rx
            pdus += n
            delay_w += delay * n
    span = sum(e - s for s, e in epochs)
    if span <= 0:
        raise RuntimeError(f"{path}: no epoch inside [{t0}, {t1}]")
    return {"dl_throughput_mbps": rx_bytes * 8 / span / 1e6, "dl_delay_ms": 1000 * delay_w / pdus if pdus else float("nan"),
            "pdcp_window_s": [min(s for s, _ in epochs), max(e for _, e in epochs)]}


def apply_trace_kpis(run_dir: Path, result: Dict[str, Any]) -> Dict[str, Any]:
    """Set result['kpi'] / ['kpi_per_cell'] from the ns-3 traces (KPI_SOURCE); the E2-KPM values move to
    kpi_e2 / kpi_per_cell_e2."""
    if (result.get("kpi_source") or {}).get("version") == KPI_SOURCE["version"]:
        return result
    t0, t1 = result["kpi_window_sim_s"]
    out_dir = run_dir / "ns3_out"
    result.setdefault("kpi_e2", dict(result["kpi"]))
    if "kpi_per_cell" in result:
        result.setdefault("kpi_per_cell_e2", result["kpi_per_cell"])
    e2 = None
    if result.get("clock") == "sim-time collectStartTime" and (run_dir / "kpm.csv").exists():
        e2 = KpmState(run_dir / "kpm.csv")
        e2.poll()
    du = du_trace_kpis(out_dir, GNBS, t0, t1, e2)
    pd = pdcp_kpis(out_dir, t0, t1)
    energy, energy_cells = energy_window(out_dir, GNBS, t0, t1, per_cell=True)
    per_cell = du["per_cell"]
    for cell, e in energy_cells.items():
        per_cell[cell]["energy_j_per_s"] = e
    result["kpi"] = {"prb_used_dl": du["prb_used_dl"], "dl_buffer_kbytes": du["dl_buffer_kbytes"],
                     "dl_throughput_mbps": pd["dl_throughput_mbps"], "dl_delay_ms": pd["dl_delay_ms"], "energy_j_per_s": energy}
    result["kpi_per_cell"] = per_cell
    result["kpi_trace_window"] = {"du_logger_writes": du["writes"], "prb_method": du["prb_method"], "pdcp_epochs_s": pd["pdcp_window_s"]}
    result["kpi_source"] = {"version": KPI_SOURCE["version"]}
    return result


# ---------------------------------------------------------------- UE placement sync
def ue_positions_at(ue_position_txt: Path, t_s: float) -> Tuple[float, Dict[int, Tuple[float, float]]]:
    """UE positions from a scenario's ue_position.txt (timestamp,id,x,y,type,cell,simid; timestamp =
    simid + simulated ms) at the last print not after t_s. Returns (print time in s, {imsi: (x, y)})."""
    prints: Dict[int, Dict[int, Tuple[float, float]]] = defaultdict(dict)
    with ue_position_txt.open() as handle:
        for row in csv.reader(handle):
            if len(row) < 7:
                continue
            try:
                ts, imsi, x, y, simid = int(row[0]), int(row[1]), float(row[2]), float(row[3]), int(row[6])
            except ValueError:
                continue  # header rows
            prints[ts - simid][imsi] = (x, y)
    target = int(round(t_s * 1000))
    eligible = [ms for ms in prints if ms <= target]
    if not eligible:
        raise ValueError(f"{ue_position_txt}: no UE position print at or before {t_s} s")
    ms = max(eligible)
    return ms / 1000.0, dict(prints[ms])


def write_ue_position_file(path: Path, positions: Dict[int, Tuple[float, float]], n_ues: int, z: float = 0.0) -> None:
    """CSV for the scenario's uePositionFile: header ue_index,x,y,z; ue_index = IMSI - 1 (z of the disc
    allocator is 0)."""
    missing = [i for i in range(1, n_ues + 1) if i not in positions]
    if missing:
        raise ValueError(f"no position for IMSI {missing}")
    lines = ["ue_index,x,y,z"] + [f"{imsi - 1},{positions[imsi][0]:.4f},{positions[imsi][1]:.4f},{z:g}" for imsi in range(1, n_ues + 1)]
    path.write_text("\n".join(lines) + "\n")


def ns3_has_global(name: str) -> bool:
    """True if the scenario binary declares the GlobalValue `name` (checked in the binary's strings, so no
    simulation is started)."""
    try:
        data = NS3_BIN.read_bytes()
    except OSError:
        return False
    if name.encode() not in data:  # GlobalValues may live in the scenario binary itself
        return False
    return True


# ---------------------------------------------------------------- workflow -> RC commands
def _rapp(family: str) -> Dict[str, Any]:
    return rapp_runtime.load_catalog()[f"rapp.{family}"]


def _best_target(state: KpmState, ue: int, exclude: set, prefer: Optional[int] = None) -> Optional[int]:
    neigh = {c: s for c, s in state.ue_neigh.get(ue, {}).items() if c not in exclude and c in state.bins}
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


def run_name(role: str, seed: int, workflow: str) -> str:
    return f"{role}_s{seed}_{workflow}"


def run_instance(role: str, seed: int, n_ues: int, workflow: str, slot: int, out_root: Path,
                 policy: Optional[Dict[str, Any]] = None, ue_position_file: Optional[Path] = None) -> Dict[str, Any]:
    run_dir = out_root / "runs" / run_name(role, seed, workflow)
    result_path = run_dir / "result.json"
    if result_path.exists():
        cached = json.loads(result_path.read_text())
        if cached.get("ok"):
            return cached  # failed runs are retried
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "ns3_out").mkdir(parents=True)
    e2_port, e42_port = PORT_BASE + 10 * slot, PORT_BASE + 1 + 10 * slot
    # FlexRIC keeps conf paths in a short fixed buffer (FR_CONF_FILE_LEN): use a short per-slot path.
    short = Path(f"/tmp/aw_t6/s{slot}")
    short.mkdir(parents=True, exist_ok=True)
    conf = short / "flexric.conf"
    conf.write_text(f"[NEAR-RIC]\nNEAR_RIC_IP = 127.0.0.1\n\n[XAPP]\nDB_DIR = {short}/\n\n[PORTS]\nNEAR_RIC_PORT = {e2_port}\nE42_PORT = {e42_port}\n")
    shutil.copy(conf, run_dir / "flexric.conf")
    procs: List[subprocess.Popen] = []
    started = time.time()
    result: Dict[str, Any] = {"role": role, "seed": seed, "n_ues": n_ues, "workflow": workflow,
                              "chain": WORKFLOWS[workflow], "sim_time_s": SIM_TIME, "t_act_s": T_ACT,
                              "clock": "sim-time collectStartTime", "load_avg_start": os.getloadavg()[0]}
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
        if ue_position_file is not None:
            local = run_dir / "ue_positions_in.csv"
            shutil.copy(ue_position_file, local)
            ns3_args.append(f"--uePositionFile={local}")
            result["ue_position_file"] = str(ue_position_file)
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
        dispatched: List[List[Any]] = []
        acted = False
        if policy is not None:
            result["policy_from"] = "twin"
        while ns3.poll() is None:
            state.poll()
            t = state.sim_time()
            if not acted and t >= T_ACT:
                acted = True
                result["act_sim_time_s"] = round(t, 4)
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
                dispatched += [[round(t, 4), c] for c in due]
                pending = [(w, c) for w, c in pending if c not in due]
            if actuator.poll() is not None:
                raise RuntimeError(f"actuator exited (rc={actuator.returncode})")
            time.sleep(0.2)
        state.poll()
        t0, t1 = WINDOW
        win = state.window_kpis(t0, t1, GNBS)
        energy, energy_cells = energy_window(run_dir / "ns3_out", GNBS, t0, t1, per_cell=True)
        per_cell = win.pop("per_cell")
        for cell, e in energy_cells.items():
            per_cell.setdefault(cell, {})["energy_j_per_s"] = e
        bins, bins_reported = win.pop("bins"), win.pop("bins_reported")
        result["kpi"] = {**win, "energy_j_per_s": energy}
        result["kpi_per_cell"] = per_cell
        result["kpi_window_sim_s"] = [t0, t1]
        result["kpi_window_bins"] = [bins, bins_reported]
        for trace in (run_dir / "ns3_out").glob("*.txt"):
            if trace.stat().st_size > 5_000_000:
                trace.unlink()  # large ns-3 traces are not needed for the KPI window
        trace_error = None
        try:
            apply_trace_kpis(run_dir, result)
        except Exception as exc:  # e.g. ns-3 aborted: reported with the other problems below
            trace_error = f"trace KPIs: {exc}"
        result["first_report_sim_s"] = None if state.first_du_stamp_us is None else round(state.first_du_stamp_us / 1e6, 4)
        result["last_report_sim_s"] = round(state.sim_time(), 4)
        result["kpm_history_at_act_s"] = (None if state.first_du_stamp_us is None or "act_sim_time_s" not in result
                                          else round(result["act_sim_time_s"] - state.first_du_stamp_us / 1e6, 4))
        result["novalue_rows"] = state.novalue_rows
        result["commands_dispatched_sim_s"] = dispatched
        result["indications_per_gnb"] = {str(g): len(state.bins.get(g, ())) for g in GNBS}
        result["rc_acks"] = ack_file.read_text().splitlines() if ack_file.exists() else []
        result["ns3_returncode"] = ns3.returncode
        problems = [trace_error] if trace_error else []
        if ns3.returncode != 0:
            problems.append(f"ns-3 rc={ns3.returncode}")
        if result.get("act_sim_time_s") is None:
            problems.append("no KPM report at or after t_act")
        elif (result["kpm_history_at_act_s"] or 0) < MIN_HISTORY - 1e-6:
            problems.append(f"only {result['kpm_history_at_act_s']} s of KPM before t_act (< {MIN_HISTORY})")
        if bins_reported < bins - 1:
            problems.append(f"KPI window has reports in {bins_reported}/{bins} periods")
        if workflow != "noop" and len(dispatched) != len(result.get("commands", [])):
            problems.append("not every RC command was dispatched before the end of the run")
        result["ok"] = not problems
        if problems:
            result["error"] = "; ".join(problems)
    except Exception as exc:  # recorded, never hidden
        result["ok"] = False
        result["error"] = str(exc)
    finally:
        for proc in reversed(procs):
            _kill_group(proc)
            LIVE_PROCS.discard(proc)
        result["wall_s"] = round(time.time() - started, 1)
        result["load_avg_end"] = os.getloadavg()[0]
        for trace in (run_dir / "ns3_out").glob("*.txt"):
            if trace.stat().st_size > 5_000_000:
                trace.unlink()  # large ns-3 traces are not needed for the KPI window
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def run_with_retry(*args, **kwargs) -> Dict[str, Any]:
    res = run_instance(*args, **kwargs)
    if not res.get("ok"):
        first_error = res.get("error")
        res = run_instance(*args, **kwargs)
        res["first_attempt_error"] = first_error
        res["attempts"] = 2
        run_dir = kwargs["out_root"] / "runs" / run_name(args[0], args[1], args[3])
        (run_dir / "result.json").write_text(json.dumps(res, indent=2, sort_keys=True))
    return res


# ---------------------------------------------------------------- analysis
def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def wilson(k: int, n: int, z: float = 1.959964) -> Optional[List[float]]:
    """Wilson score 95% interval for k successes in n trials."""
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, centre - half), min(1.0, centre + half)]


def _pct_change(wf: float, noop: float) -> Optional[float]:
    if noop is None or wf is None or math.isnan(wf) or math.isnan(noop):
        return None
    if noop == 0:
        return 0.0 if wf == 0 else math.copysign(math.inf, wf)
    return 100.0 * (wf - noop) / noop


def _off_cells(run: Dict[str, Any]) -> List[int]:
    return [int(c.split()[1]) for c in run.get("commands") or [] if c.startswith("OFF ")]


def gate_metrics(workflow: str, wf_run: Dict[str, Any], noop_run: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    """Gate quantities and verdict of one instance (twin or live) for one workflow run vs its no-op."""
    th = GATE[workflow]
    pc_wf, pc_noop = wf_run.get("kpi_per_cell") or {}, noop_run.get("kpi_per_cell") or {}
    out: Dict[str, Any] = {}
    if workflow == "energy_saving":
        change = _pct_change(wf_run["kpi"]["energy_j_per_s"], noop_run["kpi"]["energy_j_per_s"])
        out["energy_saving_pct"] = None if change is None else -change
        remaining = [str(c) for c in GNBS if c not in _off_cells(wf_run)]
        out["remaining_cells"] = [int(c) for c in remaining]
        out["remaining_prb_increase_pct"] = _pct_change(sum(pc_wf.get(c, {}).get("prb_used_dl", 0.0) for c in remaining),
                                                        sum(pc_noop.get(c, {}).get("prb_used_dl", 0.0) for c in remaining))
        ok = (out["energy_saving_pct"] is not None and out["energy_saving_pct"] >= th["energy_saving_min_pct"]
              and out["remaining_prb_increase_pct"] is not None
              and out["remaining_prb_increase_pct"] <= th["remaining_prb_increase_max_pct"])
    else:
        hot = sorted({str(s["from"]) for s in (policy or {}).get("shed", [])})
        out["hot_cells"] = [int(c) for c in hot]
        noop_hot = sum(pc_noop.get(c, {}).get("prb_used_dl", 0.0) for c in hot)
        if hot and noop_hot > 0:
            out["hot_prb_reduction_pct"] = -_pct_change(sum(pc_wf.get(c, {}).get("prb_used_dl", 0.0) for c in hot), noop_hot)
        else:
            out["hot_prb_reduction_pct"] = None
        change = _pct_change(wf_run["kpi"]["dl_throughput_mbps"], noop_run["kpi"]["dl_throughput_mbps"])
        out["throughput_loss_pct"] = None if change is None else -change
        ok = (out["hot_prb_reduction_pct"] is not None and out["hot_prb_reduction_pct"] >= th["hot_prb_reduction_min_pct"]
              and out["throughput_loss_pct"] is not None and out["throughput_loss_pct"] <= th["throughput_loss_max_pct"])
    out["commands"] = len(wf_run.get("commands") or [])
    out["accept"] = bool(ok)
    return out


def confusion(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    tp = sum(1 for r in rows if r["twin"]["accept"] and r["live"]["accept"])
    fp = sum(1 for r in rows if r["twin"]["accept"] and not r["live"]["accept"])
    fn = sum(1 for r in rows if not r["twin"]["accept"] and r["live"]["accept"])
    tn = sum(1 for r in rows if not r["twin"]["accept"] and not r["live"]["accept"])
    n = len(rows)
    frac = lambda k, m: (k / m) if m else None  # noqa: E731
    return {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": frac(tp + tn, n), "accuracy_ci95": wilson(tp + tn, n),
        "precision": frac(tp, tp + fp), "precision_ci95": wilson(tp, tp + fp),
        "recall": frac(tp, tp + fn), "recall_ci95": wilson(tp, tp + fn),
        "specificity": frac(tn, tn + fp), "specificity_ci95": wilson(tn, tn + fp),
        # deploy-everything baseline: its precision is the live accept rate
        "live_accept_rate": frac(tp + fn, n), "live_accept_rate_ci95": wilson(tp + fn, n),
        "twin_accept_rate": frac(tp + fp, n),
    }


def load_results(out: Path, write_back: bool = True) -> List[Dict[str, Any]]:
    """All run results of a batch; ok runs analysed before KPI_SOURCE existed get the trace KPIs added
    (written back to result.json unless write_back is False)."""
    results = []
    for path in sorted((out / "runs").glob("*/result.json")):
        res = json.loads(path.read_text())
        if res.get("ok") and (res.get("kpi_source") or {}).get("version") != KPI_SOURCE["version"]:
            try:
                apply_trace_kpis(path.parent, res)
            except Exception as exc:
                res["ok"] = False
                res["error"] = f"trace KPIs: {exc}"
            if write_back:
                path.write_text(json.dumps(res, indent=2, sort_keys=True))
        results.append(res)
    return results


def e2_view(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Copies of the results whose kpi / kpi_per_cell are the E2-KPM values (secondary analysis)."""
    view = []
    for r in results:
        r = dict(r)
        if "kpi_e2" in r:
            r["kpi"] = r["kpi_e2"]
            r["kpi_per_cell"] = r.get("kpi_per_cell_e2") or {}
        view.append(r)
    return view


def analyse(results: List[Dict[str, Any]], excluded_pairs: Iterable[int] = ()) -> Dict[str, Any]:
    excluded = set(excluded_pairs)
    by = {(r["role"], r["seed"] if r["role"] == "twin" else r["seed"] - 100, r["workflow"]): r
          for r in results if r.get("ok")}
    pairs = sorted({k[1] for k in by} - excluded)
    rows, gate_rows = [], []
    for pair in pairs:
        for wf in [w for w in WORKFLOWS if w != "noop"]:
            keys = [("twin", pair, wf), ("twin", pair, "noop"), ("live", pair, wf), ("live", pair, "noop")]
            if not all(k in by for k in keys):
                continue
            tw, tn, lw, ln = (by[k] for k in keys)
            for kpi in [k for k in KPIS if all(k in r["kpi"] for r in (tw, tn, lw, ln))]:
                pred = tw["kpi"][kpi] - tn["kpi"][kpi]
                act = lw["kpi"][kpi] - ln["kpi"][kpi]
                rows.append({"pair": pair, "workflow": wf, "kpi": kpi, "predicted_delta": pred, "actual_delta": act,
                             "twin_noop": tn["kpi"][kpi], "live_noop": ln["kpi"][kpi],
                             "twin_commands": len(tw.get("commands") or []), "live_commands": len(lw.get("commands") or [])})
            if "kpi_per_cell" in tw and "kpi_per_cell" in lw:
                policy = tw.get("policy") or {}
                gate_rows.append({"pair": pair, "workflow": wf,
                                  "sleep_cells": policy.get("sleep_cells", []),
                                  "shed": [{k: v for k, v in s.items() if k != "avoid"} for s in policy.get("shed", [])],
                                  "twin_commands": tw.get("commands") or [], "live_commands": lw.get("commands") or [],
                                  "twin": gate_metrics(wf, tw, tn, policy), "live": gate_metrics(wf, lw, ln, policy)})
    summary: Dict[str, Any] = {"pairs": pairs, "excluded_pairs": sorted(excluded), "rows": rows, "by_workflow_kpi": {}}
    for wf in [w for w in WORKFLOWS if w != "noop"]:
        for kpi in KPIS:
            sel = [r for r in rows if r["workflow"] == wf and r["kpi"] == kpi and not math.isnan(r["actual_delta"]) and not math.isnan(r["predicted_delta"])]
            if not sel:
                continue
            ape = [abs(r["predicted_delta"] - r["actual_delta"]) / abs(r["actual_delta"]) for r in sel if abs(r["actual_delta"]) > 1e-9]
            same_sign = lambda r: ((r["predicted_delta"] > 0) - (r["predicted_delta"] < 0)) == ((r["actual_delta"] > 0) - (r["actual_delta"] < 0))  # noqa: E731
            sign = [same_sign(r) for r in sel]
            acted = [r for r in sel if r["twin_commands"] and r["live_commands"]]
            sign_acted = [same_sign(r) for r in acted]
            summary["by_workflow_kpi"][f"{wf}/{kpi}"] = {
                "pairs": len(sel),
                "mean_predicted_delta": sum(r["predicted_delta"] for r in sel) / len(sel),
                "mean_actual_delta": sum(r["actual_delta"] for r in sel) / len(sel),
                "mape_pct": 100 * sum(ape) / len(ape) if ape else None,
                "mape_pairs": len(ape),
                "sign_agreement": sum(sign) / len(sign),
                # pairs where the policy produced RC commands on both twin and live (elsewhere deltas are noise)
                "pairs_acted": len(acted),
                "sign_agreement_acted": (sum(sign_acted) / len(sign_acted)) if sign_acted else None,
                "mean_abs_rel_error_pp_acted": _mean([abs(100 * r["predicted_delta"] / r["twin_noop"] - 100 * r["actual_delta"] / r["live_noop"])
                                                      for r in acted if r["twin_noop"] and r["live_noop"]]),
                # predicted vs actual *relative* change (delta / same-instance noop level), percentage points;
                # robust where the actual delta is near zero and MAPE explodes
                "mean_predicted_rel_pct": _mean([100 * r["predicted_delta"] / r["twin_noop"] for r in sel if r["twin_noop"]]),
                "mean_abs_rel_error_pp": _mean([abs(100 * r["predicted_delta"] / r["twin_noop"] - 100 * r["actual_delta"] / r["live_noop"])
                                                for r in sel if r["twin_noop"] and r["live_noop"]]),
                # relative change of the live network (actual delta / live noop level)
                "mean_actual_rel_pct": _mean([100 * r["actual_delta"] / r["live_noop"] for r in sel if r["live_noop"]]),
            }
    gate: Dict[str, Any] = {"thresholds": GATE, "definitions": GATE_DEFINITIONS, "rows": gate_rows, "by_workflow": {}}
    for wf in GATE:
        sel = [r for r in gate_rows if r["workflow"] == wf]
        if sel:
            gate["by_workflow"][wf] = confusion(sel)
    if gate_rows:
        gate["pooled"] = confusion(gate_rows)
    summary["gate"] = gate
    return summary


def _fmt_ci(v: Optional[float], ci: Optional[List[float]], k: Optional[int] = None, n: Optional[int] = None) -> str:
    if v is None:
        return "-- (0/0)"
    frac = f" ({k}/{n})" if k is not None else ""
    return f"{100 * v:.0f}%{frac} [{100 * ci[0]:.0f}, {100 * ci[1]:.0f}]"


def _num(v: Optional[float]) -> str:
    if v is None:
        return "--"
    if math.isinf(v):
        return "+inf" if v > 0 else "-inf"
    return f"{v + 0.0:+.1f}"  # + 0.0: no "-0.0"


def source_agreement(results: List[Dict[str, Any]], trace: Dict[str, Any], e2: Dict[str, Any]) -> Dict[str, Any]:
    """How far the E2-KPM KPIs are from the trace KPIs: per-run relative difference of the same KPI
    (PRB per cell and total; throughput is a different measurement: gNB RLC rate vs UE-received PDCP),
    sign agreement of the predicted/actual deltas, and agreement of the gate verdicts."""
    rel: Dict[str, List[float]] = defaultdict(list)
    for r in results:
        if not r.get("ok") or "kpi_e2" not in r:
            continue
        for kpi in ("prb_used_dl", "dl_throughput_mbps", "dl_buffer_kbytes"):
            a, b = r["kpi"].get(kpi), r["kpi_e2"].get(kpi)
            if a and b is not None:
                rel[kpi].append(100.0 * (b - a) / a)
        for cell, vals in (r.get("kpi_per_cell") or {}).items():
            a, b = vals.get("prb_used_dl"), (r.get("kpi_per_cell_e2") or {}).get(cell, {}).get("prb_used_dl")
            if a and b is not None and a > 1.0:
                rel["prb_used_dl_per_cell"].append(100.0 * (b - a) / a)
    out: Dict[str, Any] = {"e2_minus_trace_pct": {k: {"n": len(v), "mean": _mean(v), "min": min(v), "max": max(v)} for k, v in rel.items() if v}}
    signs = {}
    for key in ("predicted_delta", "actual_delta"):
        tr = {(x["pair"], x["workflow"], x["kpi"]): x[key] for x in trace["rows"]}
        ee = {(x["pair"], x["workflow"], x["kpi"]): x[key] for x in e2["rows"]}
        for kpi in ("prb_used_dl", "dl_throughput_mbps", "energy_j_per_s"):
            common = [k for k in tr if k in ee and k[2] == kpi]
            same = [((tr[k] > 0) - (tr[k] < 0)) == ((ee[k] > 0) - (ee[k] < 0)) for k in common]
            signs[f"{key}/{kpi}"] = (sum(same) / len(same)) if same else None
    out["delta_sign_agreement"] = signs
    tg = {(r["pair"], r["workflow"]): r for r in trace["gate"]["rows"]}
    eg = {(r["pair"], r["workflow"]): r for r in e2["gate"]["rows"]}
    common = [k for k in tg if k in eg]
    out["gate_verdict_agreement"] = {
        side: (sum(tg[k][side]["accept"] == eg[k][side]["accept"] for k in common) / len(common)) if common else None
        for side in ("twin", "live")}
    out["gate_cases"] = len(common)
    return out


def write_summaries(out: Path, results: List[Dict[str, Any]], excluded: Iterable[int]) -> Dict[str, Any]:
    """summary.json/.md (KPIs from the ns-3 traces, KPI_SOURCE) and summary_e2kpm.json/.md (E2 KPM KPIs)."""
    summary = analyse(results, excluded)
    summary["kpi_source"] = KPI_SOURCE
    e2 = analyse(e2_view(results), excluded)
    summary["source_agreement"] = source_agreement(results, summary, e2)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    write_report(out, summary, results)
    e2["kpi_source"] = "E2 KPM stream (report-phase dependent PRB/throughput window; see summary.json kpi_source)"
    (out / "summary_e2kpm.json").write_text(json.dumps(e2, indent=2, sort_keys=True))
    write_report(out, e2, results, report_name="summary_e2kpm",
                 note="KPIs from the E2 KPM stream (secondary; its PRB/throughput window depends on the report phase).")
    return summary


def write_report(out: Path, summary: Dict[str, Any], results: List[Dict[str, Any]], report_name: str = "summary",
                 note: str = "KPIs from the ns-3 traces (PRB/buffer: DU logger; throughput/delay: PDCP stats; energy: energy model).") -> None:
    failed = [r for r in results if not r.get("ok")]
    acted = defaultdict(int)
    for r in results:
        if r.get("ok") and r["workflow"] != "noop" and r.get("commands"):
            acted[(r["role"], r["workflow"])] += 1
    lines = [f"# Twin-vs-live results - `{out.name}`", "",
             f"Runs: {len(results)} ({len(failed)} failed). Pairs analysed: {summary['pairs']}; excluded: {summary['excluded_pairs']}.", "",
             note, "",
             "## KPI fidelity", "",
             "| Workflow | KPI | Pairs | Predicted delta | Measured delta | Predicted change | Measured change | Abs. error of relative change (pp) | MAPE of deltas | Sign agreement | Sign agreement, pairs with RC commands on both |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, st in summary["by_workflow_kpi"].items():
        wf, kpi = key.split("/")
        fmt = lambda v: "--" if v is None else f"{v:+.1f}%"  # noqa: E731
        err = "--" if st.get("mean_abs_rel_error_pp") is None else f"{st['mean_abs_rel_error_pp']:.1f}"
        mape = "--" if st.get("mape_pct") is None else f"{st['mape_pct']:.0f}% (n={st['mape_pairs']})"
        lines.append(f"| {wf} | {kpi} | {st['pairs']} | {st['mean_predicted_delta']:+.2f} | {st['mean_actual_delta']:+.2f} | "
                     f"{fmt(st.get('mean_predicted_rel_pct'))} | "
                     f"{fmt(st.get('mean_actual_rel_pct'))} | {err} | {mape} | {100 * st['sign_agreement']:.0f}% | "
                     + ("--" if st.get("sign_agreement_acted") is None else f"{100 * st['sign_agreement_acted']:.0f}% (n={st['pairs_acted']})") + " |")
    gate = summary.get("gate") or {}
    if gate.get("rows"):
        lines += ["", "## Deploy gate (Validate-2)", "",
                  "Thresholds (declared in the manifest before the runs): "
                  + "; ".join(f"{wf}: {th['accept_if']}" for wf, th in GATE.items()) + ". Percentages are relative to the "
                  "same instance's no-op; brackets are Wilson 95% CIs. Deploy-everything baseline precision = live accept rate.", "",
                  "| Workflow | n | TP | FP | FN | TN | Accuracy | Precision (accept) | Recall (accept) | Specificity (reject) | Live accept rate |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, c in list(gate["by_workflow"].items()) + [("pooled", gate["pooled"])]:
            lines.append(f"| {name} | {c['n']} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | "
                         f"{_fmt_ci(c['accuracy'], c['accuracy_ci95'], c['tp'] + c['tn'], c['n'])} | "
                         f"{_fmt_ci(c['precision'], c['precision_ci95'], c['tp'], c['tp'] + c['fp'])} | "
                         f"{_fmt_ci(c['recall'], c['recall_ci95'], c['tp'], c['tp'] + c['fn'])} | "
                         f"{_fmt_ci(c['specificity'], c['specificity_ci95'], c['tn'], c['tn'] + c['fp'])} | "
                         f"{_fmt_ci(c['live_accept_rate'], c['live_accept_rate_ci95'], c['tp'] + c['fn'], c['n'])} |")
        lines += ["", "Per pair (twin = predicted, live = measured):", "",
                  "| Pair | Workflow | Policy | Twin: criteria | Twin | Live: criteria | Live |", "|---|---|---|---|---|---|---|"]
        for r in gate["rows"]:
            pol = (f"sleep {r['sleep_cells']}" if r["workflow"] == "energy_saving"
                   else "shed " + ",".join(f"{s['from']}->{s.get('to')}" for s in r["shed"]) if r["shed"] else "none")

            def crit(g):
                if r["workflow"] == "energy_saving":
                    return f"E {_num(g['energy_saving_pct'])}% saved, PRB(rem) {_num(g['remaining_prb_increase_pct'])}%, {g['commands']} cmd"
                return f"hot PRB {_num(g['hot_prb_reduction_pct'])}% cut, thp {_num(g['throughput_loss_pct'])}% lost, {g['commands']} cmd"
            lines.append(f"| {r['pair']} | {r['workflow']} | {pol} | {crit(r['twin'])} | {'accept' if r['twin']['accept'] else 'reject'} | "
                         f"{crit(r['live'])} | {'accept' if r['live']['accept'] else 'reject'} |")
    agree = summary.get("source_agreement")
    if agree:
        lines += ["", "## E2 KPM vs ns-3 trace KPIs", "",
                  "Per-run difference E2 - trace (% of trace): " + "; ".join(
                      f"{k} mean {v['mean']:+.1f} (min {v['min']:+.1f}, max {v['max']:+.1f}, n={v['n']})"
                      for k, v in agree["e2_minus_trace_pct"].items()) + ".",
                  "Delta sign agreement between sources: " + "; ".join(
                      f"{k} {100 * v:.0f}%" for k, v in agree["delta_sign_agreement"].items() if v is not None) + ".",
                  f"Gate verdicts identical under both sources: twin {100 * (agree['gate_verdict_agreement']['twin'] or 0):.0f}%, "
                  f"live {100 * (agree['gate_verdict_agreement']['live'] or 0):.0f}% of {agree['gate_cases']} cases."]
    lines += ["", "Runs in which the deployed policy produced RC commands:", ""]
    lines += [f"- {role} {wf}: {n}" for (role, wf), n in sorted(acted.items())]
    if failed:
        lines += ["", "Failed runs:", ""] + [f"- {r['role']} s{r['seed']} {r['workflow']}: {r.get('error')}" for r in failed]
    (out / f"{report_name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def aa_compare(first: Path, repeat: Path) -> Dict[str, Any]:
    """A/A noise: every no-op in `repeat` vs the same run in `first` (same inputs)."""
    rows = []
    for res_path in sorted((repeat / "runs").glob("*_noop/result.json")):
        name = res_path.parent.name
        a_path = first / "runs" / name / "result.json"
        if not a_path.exists():
            continue
        a, b = json.loads(a_path.read_text()), json.loads(res_path.read_text())
        if not (a.get("ok") and b.get("ok")):
            continue
        for prefix, kpi_key, cell_key in (("", "kpi", "kpi_per_cell"), ("e2:", "kpi_e2", "kpi_per_cell_e2")):
            for kpi in KPIS:
                x, y = (a.get(kpi_key) or {}).get(kpi), (b.get(kpi_key) or {}).get(kpi)
                if x is None or y is None:
                    continue
                rows.append({"run": name, "kpi": prefix + kpi, "first": x, "repeat": y,
                             "rel_diff_pct": 100 * abs(y - x) / abs(x) if x else None})
            for cell in (a.get(cell_key) or {}):
                x, y = a[cell_key][cell].get("prb_used_dl"), (b.get(cell_key) or {}).get(cell, {}).get("prb_used_dl")
                if x is not None and y is not None:
                    rows.append({"run": name, "kpi": f"{prefix}prb_used_dl@cell{cell}", "first": x, "repeat": y,
                                 "rel_diff_pct": 100 * abs(y - x) / abs(x) if x else None,
                                 "abs_diff": abs(y - x)})
    worst: Dict[str, float] = {}
    for r in rows:
        key = r["kpi"].split("@")[0] + ("_per_cell" if "@" in r["kpi"] else "")
        if r["rel_diff_pct"] is not None:
            worst[key] = max(worst.get(key, 0.0), r["rel_diff_pct"])
    return {"rows": rows, "max_rel_diff_pct": worst}


def write_aa(out: Path, first: Path) -> None:
    load_results(first)  # adds the trace KPIs to both sides where missing
    load_results(out)
    noise = aa_compare(first, out)
    (out / "noise.json").write_text(json.dumps(noise, indent=2))
    lines = [f"A/A no-op repeat: `{out}` vs `{first}`", "", "| Run | KPI | First run | Repeat | Rel. diff |", "|---|---|---|---|---|"]
    for r in noise["rows"]:
        rel = "--" if r["rel_diff_pct"] is None else f"{r['rel_diff_pct']:.2f}%"
        lines.append(f"| {r['run']} | {r['kpi']} | {r['first']:.3f} | {r['repeat']:.3f} | {rel} |")
    lines += ["", "Max relative difference per KPI: " + ", ".join(f"{k} {v:.2f}%" for k, v in sorted(noise["max_rel_diff_pct"].items()))]
    (out / "noise.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- batch driver
def parse_pairs(spec: str) -> List[int]:
    pairs: List[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pairs += list(range(int(a), int(b) + 1))
        elif part:
            pairs.append(int(part))
    return pairs


def host_snapshot() -> Dict[str, Any]:
    """Load average and the AppWeaver / simulator processes running on the host (for the manifest)."""
    snap: Dict[str, Any] = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "loadavg": list(os.getloadavg()),
                            "cpu_count": os.cpu_count()}
    try:
        ps = subprocess.run(["ps", "-eo", "pid,etimes,args"], capture_output=True, text=True, timeout=10).stdout.splitlines()
    except Exception:
        ps = []
    procs = []
    for line in ps[1:]:
        args = line.split(None, 2)
        if len(args) < 3:
            continue
        cmd = args[2]
        if any(tag in cmd for tag in ("run_harness.py", "flexric_agent_portal", "nearRT-RIC", "emu_agent", "ns3.42-", "xapp_")):
            label = cmd.split("--label", 1)[1].split()[0].rstrip(",;") if "--label" in cmd else None
            procs.append({"pid": int(args[0]), "elapsed_s": int(args[1]), "cmd": cmd[:300], **({"label": label} if label else {})})
    snap["processes"] = procs
    snap["harness_labels"] = sorted({p["label"] for p in procs if p.get("label")})
    return snap


def _sha256(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pairs", default="1-9", help="pair list, e.g. 1-9 or 1,2,4-9 (twin RngRun = pair, live = pair+100)")
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--workflows", nargs="+", default=list(WORKFLOWS))
    parser.add_argument("--only", default="", help="role:seed:workflow for a single smoke run")
    parser.add_argument("--twin-ues", type=int, default=TWIN_UES,
                        help="UEs in the twin (default 8; set to the live count for a load-calibrated twin)")
    parser.add_argument("--sync", choices=["none", "load", "positions"], default=None,
                        help="twin state sync level (default: none for 8 twin UEs, load for twin UEs = live UEs)")
    parser.add_argument("--reuse-live-noop", default="", help="batch dir whose live no-op runs (identical inputs) are copied in")
    parser.add_argument("--aa-of", default="", help="A/A mode: re-run the no-ops of this batch dir (--aa-roles) and compare")
    parser.add_argument("--aa-roles", nargs="+", default=["twin", "live"])
    parser.add_argument("--host-context", default="", help="what else runs on the host (recorded in the manifest)")
    parser.add_argument("--note", default="")
    parser.add_argument("--report-only", action="store_true", help="re-analyse the runs already in --out")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"

    if args.report_only:
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        results = load_results(out)
        excluded = {int(p) for p in (manifest.get("excluded_pairs") or {})}
        if manifest.get("aa_of"):
            write_aa(out, Path(manifest["aa_of"]))
            return 0
        write_summaries(out, results, excluded)
        return 0

    sync = args.sync or ("load" if args.twin_ues == LIVE_UES else "none")
    if sync == "positions":
        if args.twin_ues != LIVE_UES:
            parser.error("--sync positions needs --twin-ues equal to the live UE count")
        if not ns3_has_global("uePositionFile"):
            parser.error(f"{NS3_BIN} has no uePositionFile GlobalValue yet (simulator input pending)")
    pairs = parse_pairs(args.pairs)
    signal.signal(signal.SIGTERM, _on_exit_signal)
    signal.signal(signal.SIGINT, _on_exit_signal)

    # Phases run one after the other; inside a phase, units run on --parallel lanes. A unit is a list of jobs
    # run in order on one slot: (twin wf, live wf) of one (pair, workflow), since live deploys the twin's policy.
    Job = Tuple[str, int, int, str]
    phases: List[List[List[Job]]] = []
    if args.aa_of:
        units = [[(role, p if role == "twin" else p + 100, args.twin_ues if role == "twin" else LIVE_UES, "noop")]
                 for p in pairs for role in args.aa_roles]
        phases.append(units)
    elif args.only:
        role, seed, wf = args.only.split(":")
        phases.append([[(role, int(seed), args.twin_ues if role == "twin" else LIVE_UES, wf)]])
    else:
        if args.reuse_live_noop:
            src = Path(args.reuse_live_noop).resolve()
            for p in pairs:
                name = run_name("live", p + 100, "noop")
                res = src / "runs" / name / "result.json"
                if res.exists() and json.loads(res.read_text()).get("ok") and not (out / "runs" / name).exists():
                    shutil.copytree(src / "runs" / name, out / "runs" / name)
        if sync == "positions":  # the live no-op supplies the UE positions at t_act: run it first
            phases.append([[("live", p + 100, LIVE_UES, "noop")] for p in pairs if "noop" in args.workflows])
            phases.append([[("twin", p, args.twin_ues, "noop")] for p in pairs if "noop" in args.workflows]
                          + [[("twin", p, args.twin_ues, wf), ("live", p + 100, LIVE_UES, wf)]
                             for p in pairs for wf in args.workflows if wf != "noop"])
        else:
            phases.append([[("twin", p, args.twin_ues, wf), ("live", p + 100, LIVE_UES, wf)]
                           for p in pairs for wf in args.workflows])
    n_jobs = sum(len(u) for ph in phases for u in ph)

    manifest: Dict[str, Any] = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.update({
        "created_at": manifest.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scenario": SCENARIO, "ns3_bin": str(NS3_BIN), "ns3_bin_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(NS3_BIN.stat().st_mtime)) if NS3_BIN.exists() else None,
        "ns3_bin_sha256": _sha256(NS3_BIN), "actuator": str(ACTUATOR), "actuator_sha256": _sha256(ACTUATOR),
        "rapps_runtime_sha256": _sha256(REPO / "rapps" / "runtime.py"), "rapps_catalog_sha256": _sha256(REPO / "rapps" / "catalog.json"),
        "flexric": str(FLEXRIC_TAAP), "ric_ports": f"E2 {PORT_BASE}+10*slot, E42 {PORT_BASE + 1}+10*slot (one RIC per run)",
        "n_gnb": N_GNB, "twin_ues": args.twin_ues, "live_ues": LIVE_UES, "sync": sync,
        "sim_time_s": SIM_TIME, "t_act_s": T_ACT, "t_act_definition": "absolute simulated time (KPM collectStartTime is sim time)",
        "min_kpm_history_s": MIN_HISTORY, "settle_s": SETTLE, "kpi_window_sim_s": list(WINDOW), "indication_period_s": IND_PERIOD,
        "workflows": {w: WORKFLOWS[w] for w in args.workflows}, "jobs": n_jobs, "kpis": KPIS, "pairs": pairs,
        "protocol": ("policy decided on the twin at t_act, deployed unchanged on live; deltas vs same-instance noop"
                     + ("; twin initial UE positions = live no-op UE positions at t_act (uePositionFile)" if sync == "positions" else "")),
        "gate": {"thresholds": GATE, "definitions": GATE_DEFINITIONS},
        "exclusion_rule": EXCLUSION_RULE, "parallel": args.parallel, "nice": os.nice(0),
        "host_context": args.host_context, "host_at_start": manifest.get("host_at_start") or host_snapshot(),
    })
    if args.reuse_live_noop:
        manifest["reused_live_noop_from"] = str(Path(args.reuse_live_noop).resolve())
    if args.aa_of:
        manifest["aa_of"] = str(Path(args.aa_of).resolve())
        manifest["protocol"] = "A/A: no-op runs of aa_of re-run with identical inputs"
    if args.note:
        manifest["note"] = args.note
    manifest_path.write_text(json.dumps(manifest, indent=2))

    results: List[Dict[str, Any]] = []
    done = [0]
    pos_dir = out / "ue_positions"

    def position_file(pair: int) -> Optional[Path]:
        if sync != "positions":
            return None
        path = pos_dir / f"pair{pair}_live_s{pair + 100}_t{T_ACT:g}.csv"
        if not path.exists():
            src = out / "runs" / run_name("live", pair + 100, "noop") / "ns3_out" / "ue_position.txt"
            t_print, positions = ue_positions_at(src, T_ACT)
            pos_dir.mkdir(exist_ok=True)
            write_ue_position_file(path, positions, LIVE_UES)
            (path.with_suffix(".json")).write_text(json.dumps({"source": str(src), "print_sim_s": t_print}, indent=2))
        return path

    def run_unit(unit_slot):
        unit, slot = unit_slot
        out_results: List[Dict[str, Any]] = []
        policy, twin_failed = None, False
        for role, seed, n_ues, wf in unit:
            if role == "live" and twin_failed and wf != "noop":
                res = {"role": role, "seed": seed, "n_ues": n_ues, "workflow": wf, "ok": False, "error": "twin run failed: no policy to deploy"}
            else:
                pos = None
                if role == "twin":
                    try:
                        pos = position_file(seed)
                    except Exception as exc:
                        res = {"role": role, "seed": seed, "n_ues": n_ues, "workflow": wf, "ok": False, "error": f"position sync: {exc}"}
                        twin_failed = True
                        out_results.append(res)
                        continue
                res = run_with_retry(role, seed, n_ues, wf, slot=slot, out_root=out, policy=policy, ue_position_file=pos)
            if role == "twin":
                policy = res.get("policy")
                twin_failed = not res.get("ok")
            done[0] += 1
            print(f"[{done[0]}/{n_jobs}] {time.strftime('%H:%M:%S')} {role} s{seed} {wf} ok={res.get('ok')} wall={res.get('wall_s')}s "
                  f"cmds={res.get('commands', [])} {res.get('error', '')}", flush=True)
            out_results.append(res)
        return out_results

    for units in phases:
        # Slot s only ever runs units s, s+P, ... of a phase, so two simulations never share RIC / E2 ports.
        lanes = [[(u, s) for i, u in enumerate(units) if i % args.parallel == s] for s in range(args.parallel)]
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            for lane_results in pool.map(lambda lane: [r for unit in lane for r in run_unit(unit)], lanes):
                results.extend(lane_results)

    all_results = load_results(out)
    failed_pairs: Dict[str, str] = {}
    for r in all_results:
        if not r.get("ok"):
            pair = r["seed"] if r["role"] == "twin" else r["seed"] - 100
            failed_pairs.setdefault(str(pair), f"{run_name(r['role'], r['seed'], r['workflow'])}: {r.get('error')}")
    manifest = json.loads(manifest_path.read_text())
    manifest["excluded_pairs"] = failed_pairs if not args.aa_of else {}
    manifest["host_at_end"] = host_snapshot()
    manifest["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if args.aa_of:
        write_aa(out, Path(args.aa_of).resolve())
        print((out / "noise.md").read_text())
        return 0
    write_summaries(out, all_results, {int(p) for p in manifest["excluded_pairs"]})
    print((out / "summary.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
