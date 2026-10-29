"""Unit tests for run_twin_validation.py (no simulator needed).

  cd examples/xApp/python3 && python -m pytest -q evaluation/twin/test_twin_validation.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_twin_validation as tv  # noqa: E402

HEADER = "wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value\n"


def _kpm(tmp_path: Path, rows) -> tv.KpmState:
    path = tmp_path / "kpm.csv"
    path.write_text(HEADER + "".join(",".join(str(x) for x in r) + "\n" for r in rows))
    state = tv.KpmState(path)
    state.poll()
    return state


def test_sim_time_clock_and_novalue(tmp_path):
    rows = []
    for k in range(5, 80):  # reports at 0.525 s ... 7.925 s, one per 100 ms
        stamp = k * 100_000 + 25_000
        rows.append((1, stamp, 2, 1, 1, "DRB.PdcpSduVolumeDl_Filter.UEID", 0, 5))  # LTE eNB: clock only
        rows.append((1, stamp, 7, 2, 1, "RRU.PrbUsedDl.UEID", 0, 10))
        rows.append((1, stamp, 7, 2, 2, "RRU.PrbUsedDl.UEID", 0, 5))
        rows.append((1, stamp, 7, 2, 1, "DRB.UEThpDl.UEID", 0, 2000))
        rows.append((1, stamp, 7, 3, 3, "RRU.PrbUsedDl.UEID", 0, ""))  # noValue: period marked, not summed
        rows.append((1, stamp, 7, 2, 1, "L3neighSINRListOf_UEID_1_of_Cell_2", 0, ""))  # no neighbour
    state = _kpm(tmp_path, rows)
    assert math.isclose(state.sim_time(), 7.925)
    assert state.first_du_stamp_us == 525_000
    assert state.novalue_rows == 150
    assert state.cells() == [2, 3]
    assert len(state.bins[3]) == 75
    assert state.ue_neigh == {}
    win = state.window_kpis(2.5, 7.9, [2, 3, 4, 5])
    assert win["bins"] == 54 and win["bins_reported"] == 54
    assert math.isclose(win["prb_used_dl"], 15.0)
    assert math.isclose(win["dl_throughput_mbps"], 2.0)
    assert win["per_cell"]["3"]["prb_used_dl"] == 0.0 and win["per_cell"]["5"]["prb_used_dl"] == 0.0


def test_window_counts_missing_reports_as_zero(tmp_path):
    rows = [(1, k * 100_000 + 25_000, 7, 2, 1, "RRU.PrbUsedDl.UEID", 0, 10) for k in range(5, 80)]
    rows += [(1, k * 100_000 + 25_000, 7, 3, 2, "RRU.PrbUsedDl.UEID", 0, 20) for k in range(5, 40)]  # cell 3 off at 4 s
    state = _kpm(tmp_path, rows)
    win = state.window_kpis(2.5, 7.9, [2, 3])
    assert math.isclose(win["per_cell"]["3"]["prb_used_dl"], 20 * 15 / 54)
    assert math.isclose(win["prb_used_dl"], 10 + 20 * 15 / 54)


def test_ue_positions_roundtrip(tmp_path):
    simid = 1793124066177
    lines = ["timestamp,id,x,y,type,cell,simid"]
    for ms in (0, 1900, 2000, 2100):
        for imsi in (1, 2, 3):
            lines.append(f"{simid + ms},{imsi},{1000 + imsi + ms / 1000:.2f},{2000 - imsi:.2f},mc,2,{simid}")
    src = tmp_path / "ue_position.txt"
    src.write_text("\n".join(lines) + "\n")
    t, pos = tv.ue_positions_at(src, 2.0)
    assert t == 2.0 and pos[2] == (1004.0, 1998.0)
    t, pos = tv.ue_positions_at(src, 2.05)  # last print not after t
    assert t == 2.0
    out = tmp_path / "pos.csv"
    tv.write_ue_position_file(out, pos, 3)
    assert out.read_text().splitlines() == ["ue_index,x,y,z", "0,1003.0000,1999.0000,0", "1,1004.0000,1998.0000,0",
                                            "2,1005.0000,1997.0000,0"]
    try:
        tv.write_ue_position_file(out, pos, 4)
    except ValueError:
        pass
    else:
        raise AssertionError("missing UE must raise")


def _run(energy, thp, prb_cells, commands=()):
    return {"kpi": {"energy_j_per_s": energy, "dl_throughput_mbps": thp},
            "kpi_per_cell": {str(c): {"prb_used_dl": v} for c, v in prb_cells.items()}, "commands": list(commands)}


def test_gate_energy_saving():
    noop = _run(1000, 20, {2: 50, 3: 10, 4: 10, 5: 30})
    wf = _run(900, 19, {2: 60, 3: 0, 4: 10, 5: 30}, ["HO 1 2", "OFF 3"])
    g = tv.gate_metrics("energy_saving", wf, noop, {"sleep_cells": [3]})
    assert math.isclose(g["energy_saving_pct"], 10.0)
    assert g["remaining_cells"] == [2, 4, 5]
    assert math.isclose(g["remaining_prb_increase_pct"], 100 * 10 / 90)
    assert g["accept"]
    wf_bad = _run(990, 20, {2: 50, 3: 10, 4: 10, 5: 30})  # 1 % saving
    assert not tv.gate_metrics("energy_saving", wf_bad, noop, {"sleep_cells": [3]})["accept"]


def test_gate_steering():
    noop = _run(1000, 20, {2: 100, 3: 10})
    policy = {"shed": [{"from": 2, "to": 3, "share": 0.2}]}
    g = tv.gate_metrics("traffic_steering", _run(1000, 19.5, {2: 80, 3: 30}, ["HO 4 3"]), noop, policy)
    assert math.isclose(g["hot_prb_reduction_pct"], 20.0) and math.isclose(g["throughput_loss_pct"], 2.5) and g["accept"]
    g = tv.gate_metrics("qoe_steering", _run(1000, 18, {2: 80, 3: 30}), noop, policy)
    assert not g["accept"]  # 10 % throughput loss
    g = tv.gate_metrics("qoe_steering", _run(1000, 20, {2: 100, 3: 10}), noop, {"shed": []})
    assert g["hot_prb_reduction_pct"] is None and not g["accept"]


def test_confusion_and_wilson():
    rows = [{"twin": {"accept": t}, "live": {"accept": l}} for t, l in
            [(True, True)] * 4 + [(True, False)] * 1 + [(False, True)] * 2 + [(False, False)] * 3]
    c = tv.confusion(rows)
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (4, 1, 2, 3)
    assert math.isclose(c["precision"], 0.8) and math.isclose(c["recall"], 4 / 6) and math.isclose(c["accuracy"], 0.7)
    lo, hi = tv.wilson(4, 5)
    assert math.isclose(lo, 0.3755, abs_tol=1e-3) and math.isclose(hi, 0.9638, abs_tol=1e-3)
    assert tv.wilson(0, 0) is None
    assert tv.confusion([])["precision"] is None


def test_pairs_spec():
    assert tv.parse_pairs("1,2,4-6") == [1, 2, 4, 5, 6]


def test_trace_kpis(tmp_path):
    base = 4603843735564501298
    cols = ["timestamp", "ueImsiComplete", "plmId"] + [f"c{i}" for i in range(36)] + ["RRU.PrbUsedDl.UEID"] + \
           [f"d{i}" for i in range(13)] + ["DRB.BufferSize.Qos.UEID", "DRB.UEThpDl.UEID"]
    i_prb, i_buf = cols.index("RRU.PrbUsedDl.UEID"), cols.index("DRB.BufferSize.Qos.UEID")
    for cell in (2, 3):
        lines = [",".join(cols)]
        for ms in range(100, 8000, 100):
            if cell == 3 and ms > 4000:
                break  # switched off with no UE: no rows
            for imsi in (1, 2):
                row = ["0"] * len(cols)
                row[0], row[1], row[2] = str(base + ms), f"0000{imsi}", "\x00\x01"
                row[i_prb], row[i_buf] = "10", "1000"
                lines.append(",".join(row))
        (tmp_path / f"du-cell-{cell}.txt").write_text("\n".join(lines) + "\n")
    du = tv.du_trace_kpis(tmp_path, [2, 3, 4], 2.5, 7.9)
    assert du["writes"] == 54
    assert math.isclose(du["per_cell"]["2"]["prb_used_dl"], 20.0)
    assert math.isclose(du["per_cell"]["3"]["prb_used_dl"], 20.0 * 15 / 54)  # writes 2.6 ... 4.0
    assert du["per_cell"]["4"]["prb_used_dl"] == 0.0
    pd = ["% start\tend\tCellId\tIMSI\tRNTI\tLCID\tnTxPDUs\tTxBytes\tnRxPDUs\tRxBytes\tdelay\tstdDev"]
    for k in range(32):
        s, e = k * 0.25, (k + 1) * 0.25
        for imsi in (1, 2):
            pd.append(f"{s:g}\t{e:g}\t1\t{imsi}\t1\t3\t10\t1000\t10\t{100000 if imsi == 1 else 0}\t{0.001 * imsi}\t0\t")
    (tmp_path / "DlPdcpStats.txt").write_text("\n".join(pd) + "\n")
    p = tv.pdcp_kpis(tmp_path, 2.5, 7.9)
    assert p["pdcp_window_s"] == [2.5, 7.75]
    assert math.isclose(p["dl_throughput_mbps"], 21 * 100000 * 8 / 5.25 / 1e6)
    assert math.isclose(p["dl_delay_ms"], 1.5)


def test_prb_rebuilt_from_e2_and_logger(tmp_path):
    base = 4603843735564501298
    cols = ["timestamp", "ueImsiComplete", "plmId", "RRU.PrbUsedDl.UEID", "DRB.BufferSize.Qos.UEID"]
    lines = [",".join(cols)] + [f"{base + ms},00001,x,20,0" for ms in range(100, 8000, 100)]
    (tmp_path / "du-cell-2.txt").write_text("\n".join(lines) + "\n")
    # E2 reports 25 ms after each boundary, each covering the 25 ms since the logger's reset
    state = _kpm(tmp_path, [(1, k * 100_000 + 25_000, 7, 2, 1, "RRU.PrbUsedDl.UEID", 0, 40) for k in range(2, 80)])
    du = tv.du_trace_kpis(tmp_path, [2], 2.5, 7.9, state)
    assert du["prb_method"].startswith("e2+logger, phi=25.000")
    assert math.isclose(du["per_cell"]["2"]["prb_used_dl"], (25 * 40 + 75 * 20) / 100)
    assert math.isclose(tv.du_trace_kpis(tmp_path, [2], 2.5, 7.9)["per_cell"]["2"]["prb_used_dl"], 20.0)


def test_grid_aligned_window_and_simid_base(tmp_path):
    # simulator fix 8: gNB stamps on the 100 ms tick, each covering the window that ends there
    rows = [(1, k * 100_000, 7, 2, 1, "RRU.PrbUsedDl.UEID", 0, k) for k in range(6, 81)]
    state = _kpm(tmp_path, rows)
    assert state.grid_aligned()
    bins = state.window_bins(2.5, 7.9)
    assert bins[0] == 26 and bins[-1] == 79 and len(bins) == 54
    win = state.window_kpis(2.5, 7.9, [2])
    assert math.isclose(win["prb_used_dl"], sum(range(26, 80)) / 54)
    # simulator fix 9: trace timestamp = simid + sim ms
    simid = 1793124066177
    (tmp_path / "ue_position.txt").write_text(f"timestamp,id,x,y,type,cell,simid\n{simid},1,1.0,2.0,mc,2,{simid}\n")
    cols = ["timestamp", "ueImsiComplete", "plmId", "RRU.PrbUsedDl.UEID", "DRB.BufferSize.Qos.UEID"]
    lines = [",".join(cols)] + [f"{simid + ms},00001,x,{ms // 100},0" for ms in range(100, 8000, 100)]
    (tmp_path / "du-cell-2.txt").write_text("\n".join(lines) + "\n")
    du = tv.du_trace_kpis(tmp_path, [2], 2.5, 7.9, state)
    assert du["prb_method"].startswith("logger (E2 reports grid-aligned")
    assert math.isclose(du["per_cell"]["2"]["prb_used_dl"], sum(range(26, 80)) / 54)  # same windows as E2
