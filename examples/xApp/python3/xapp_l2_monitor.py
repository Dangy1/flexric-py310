#!/usr/bin/env python3
"""Read-only L2 monitor xApp: subscribe to one FlexRIC stats service model and print indications.

One script serves the four FlexRIC L2 monitor cards (MAC, RLC, PDCP, GTP). It subscribes to the
chosen service model on the first E2 node that advertises it, prints a per-indication marker
(rate-limited so a 1 ms report period does not flood the run log), unsubscribes after
``--duration-s`` and exits. It never sends an E2 CONTROL.

Ack markers (one per indication printed; the harness counts the first one):
    MAC ind tstamp=<us> ues=<n> ...
    RLC ind tstamp=<us> bearers=<n> ...
    PDCP ind tstamp=<us> bearers=<n> ...
    GTP ind tstamp=<us> tunnels=<n> ...
Closing line:  "<SM> monitor finished: <k> indications in <s> s"
No-data line:  "<SM> monitor received no indications"  (not an ack)

Usage:
    python xapp_l2_monitor.py --sm mac --duration-s 10
    FLEXRIC_XAPP_CONF=/tmp/flexric_twin_emu/flexric_twin.conf python xapp_l2_monitor.py --sm gtp --duration-s 5

RAN function ids of the FlexRIC emulator: MAC 142, RLC 143, PDCP 144, GTP 148.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

import xapp_sdk as ric

RAN_FUNCTION_IDS = {"mac": 142, "rlc": 143, "pdcp": 144, "gtp": 148}
INTERVALS = {1: "Interval_ms_1", 2: "Interval_ms_2", 5: "Interval_ms_5", 10: "Interval_ms_10"}


class _Printer:
    """Rate-limits indication lines (thread-safe: callbacks arrive on the SDK's thread)."""

    def __init__(self, label: str, min_gap_s: float):
        self.label = label
        self.min_gap_s = min_gap_s
        self.count = 0
        self.last_print = 0.0
        self.lock = threading.Lock()

    def emit(self, line_fn) -> None:
        with self.lock:
            self.count += 1
            now = time.monotonic()
            if self.count > 1 and now - self.last_print < self.min_gap_s:
                return
            self.last_print = now
        print(line_fn(), flush=True)


def _latency_us(tstamp) -> float:
    return round(time.time_ns() / 1000.0 - float(tstamp), 1)


def make_callback(sm: str, printer: _Printer):
    if sm == "mac":
        class MACCallback(ric.mac_cb):
            def __init__(self):
                ric.mac_cb.__init__(self)

            def handle(self, ind):
                ues = list(ind.ue_stats)
                if not ues:
                    return
                printer.emit(lambda: (
                    f"MAC ind tstamp={ind.tstamp} ues={len(ues)} rnti={ues[0].rnti} "
                    f"dl_sched_rb={ues[0].dl_sched_rb} ul_sched_rb={ues[0].ul_sched_rb} wb_cqi={ues[0].wb_cqi} "
                    f"dl_mcs={ues[0].dl_mcs1} dl_bler={ues[0].dl_bler:.3f} pusch_snr={ues[0].pusch_snr:.1f} "
                    f"latency_us={_latency_us(ind.tstamp)}"))
        return MACCallback()
    if sm == "rlc":
        class RLCCallback(ric.rlc_cb):
            def __init__(self):
                ric.rlc_cb.__init__(self)

            def handle(self, ind):
                rbs = list(ind.rb_stats)
                if not rbs:
                    return
                printer.emit(lambda: (
                    f"RLC ind tstamp={ind.tstamp} bearers={len(rbs)} rnti={rbs[0].rnti} rbid={rbs[0].rbid} "
                    f"txbuf_occ_bytes={rbs[0].txbuf_occ_bytes} txpdu_retx_pkts={rbs[0].txpdu_retx_pkts} "
                    f"txsdu_wt_us={rbs[0].txsdu_wt_us} latency_us={_latency_us(ind.tstamp)}"))
        return RLCCallback()
    if sm == "pdcp":
        class PDCPCallback(ric.pdcp_cb):
            def __init__(self):
                ric.pdcp_cb.__init__(self)

            def handle(self, ind):
                rbs = list(ind.rb_stats)
                if not rbs:
                    return
                printer.emit(lambda: (
                    f"PDCP ind tstamp={ind.tstamp} bearers={len(rbs)} rnti={rbs[0].rnti} rbid={rbs[0].rbid} "
                    f"txpdu_bytes={rbs[0].txpdu_bytes} rxpdu_bytes={rbs[0].rxpdu_bytes} "
                    f"rxpdu_dd_pkts={rbs[0].rxpdu_dd_pkts} latency_us={_latency_us(ind.tstamp)}"))
        return PDCPCallback()
    if sm == "gtp":
        class GTPCallback(ric.gtp_cb):
            def __init__(self):
                ric.gtp_cb.__init__(self)

            def handle(self, ind):
                tunnels = list(ind.gtp_stats)
                if not tunnels:
                    return
                printer.emit(lambda: (
                    f"GTP ind tstamp={ind.tstamp} tunnels={len(tunnels)} rnti={tunnels[0].rnti} qfi={tunnels[0].qfi} "
                    f"teid_gnb={tunnels[0].teidgnb} teid_upf={tunnels[0].teidupf} latency_us={_latency_us(ind.tstamp)}"))
        return GTPCallback()
    raise ValueError(f"unsupported service model {sm}")


SUBSCRIBE = {
    "mac": ("report_mac_sm", "rm_report_mac_sm"),
    "rlc": ("report_rlc_sm", "rm_report_rlc_sm"),
    "pdcp": ("report_pdcp_sm", "rm_report_pdcp_sm"),
    "gtp": ("report_gtp_sm", "rm_report_gtp_sm"),
}


def _pick_node(nodes, ran_function_id: int):
    for node in nodes:
        try:
            if ran_function_id in [int(x) for x in ric.get_ran_func_ids(node)]:
                return node
        except Exception:
            break  # SWIG raw object: cannot inspect, fall back to the first node
    return nodes[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only FlexRIC L2 monitor xApp (MAC/RLC/PDCP/GTP stats).")
    ap.add_argument("--sm", choices=sorted(SUBSCRIBE), required=True)
    ap.add_argument("--duration-s", type=int, default=10)
    ap.add_argument("--interval-ms", type=int, choices=sorted(INTERVALS), default=10)
    ap.add_argument("--print-every-s", type=float, default=0.5, help="minimum gap between printed indications")
    args = ap.parse_args(argv)
    label = args.sm.upper()

    ric.init()
    nodes = ric.conn_e2_nodes()
    if len(nodes) <= 0:
        print(f"{label} monitor: no E2 nodes connected")
        return 2
    node = _pick_node(list(nodes), RAN_FUNCTION_IDS[args.sm])
    print(f"Connected E2 nodes = {len(nodes)}; {label} monitor subscribing (RAN function {RAN_FUNCTION_IDS[args.sm]}, "
          f"period {args.interval_ms} ms, {args.duration_s} s)", flush=True)

    printer = _Printer(label, args.print_every_s)
    callback = make_callback(args.sm, printer)
    report_fn, remove_fn = (getattr(ric, name) for name in SUBSCRIBE[args.sm])
    handle = report_fn(node.id, getattr(ric, INTERVALS[args.interval_ms]), callback)
    started = time.monotonic()
    try:
        time.sleep(max(0, args.duration_s))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            remove_fn(handle)
        except Exception:
            pass
    elapsed = round(time.monotonic() - started, 1)
    if printer.count:
        print(f"{label} monitor finished: {printer.count} indications in {elapsed} s", flush=True)
    else:
        print(f"{label} monitor received no indications", flush=True)
    while ric.try_stop() is False:
        time.sleep(0.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
