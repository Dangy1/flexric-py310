#!/usr/bin/env python3
import argparse
import signal
import time

import xapp_sdk as ric


stop_requested = False


def _on_sigint(_sig, _frame):
    global stop_requested
    stop_requested = True
    print("\nStopping KPM/RC suite gracefully...")


class KPMParsedCallback(ric.kpm_moni_cb):
    def __init__(self, metric_mode: str = "rru"):
        super().__init__()
        self.metric_mode = metric_mode

    def handle(self, msg):
        for rec in msg.records:
            if self.metric_mode == "all":
                print(rec)
            elif self.metric_mode == "rru":
                if "meas=RRU.PrbTotDl " in rec or "meas=RRU.PrbTotUl " in rec:
                    print(rec)
            elif self.metric_mode == "ue":
                if "meas=DRB." in rec:
                    print(rec)


class RCCallback(ric.rc_cb):
    def __init__(self):
        super().__init__()

    def handle(self, ind):
        # This callback is here for future RC auto-subscription support.
        print(f"RC indication received: proc_id={ind.proc_id}")


def _print_nodes(nodes) -> None:
    print(f"Connected E2 nodes = {len(nodes)}")
    for i, node in enumerate(nodes):
        try:
            print(f"E2 node {i}: {ric.get_e2_node_id_summary(node)}")
        except Exception:
            print(f"E2 node {i}: id_fields=unavailable (SWIG raw object)")
        try:
            ran_ids = [str(x) for x in ric.get_ran_func_ids(node)]
            print(f"E2 node {i} supported RAN function IDs: {', '.join(ran_ids)}")
        except Exception:
            print(f"E2 node {i} supported RAN function IDs: unavailable (SWIG raw object)")


def _run_rc_scaffold(node) -> None:
    print("RC profile selected.")
    print("RC SWIG API is available, but an RC auto-subscription builder is not exposed yet.")
    print("Current Python RC demo is a scaffold because rc_sub_data_t must be built from node-advertised RC report styles.")
    print("Next step (optional): add a C++ SWIG helper like report_rc_sm_auto(...) similar to KPM.")
    _ = (node, RCCallback)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified FlexRIC KPM + RC Python suite")
    parser.add_argument(
        "--profile",
        choices=["kpm", "rc", "both"],
        default="kpm",
        help="Run KPM monitor, RC scaffold, or both",
    )
    parser.add_argument("--period-ms", type=int, default=1000, help="KPM reporting period (ms)")
    parser.add_argument("--duration-s", type=int, default=180, help="Auto-stop after N seconds (0=forever)")
    parser.add_argument(
        "--kpm-metrics",
        choices=["rru", "ue", "all"],
        default="rru",
        help="KPM output filter: RRU-only, UE/DRB-only, or all parsed records",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _on_sigint)

    ric.init()
    time.sleep(1)

    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")
    _print_nodes(nodes)
    node = nodes[0]

    kpm_handle = None
    if args.profile in ("kpm", "both"):
        kpm_cb = KPMParsedCallback(metric_mode=args.kpm_metrics)
        kpm_handle = ric.report_kpm_sm_auto_py(node.id, args.period_ms, kpm_cb)
        if kpm_handle < 0:
            raise RuntimeError("Failed to build/subscribe KPM auto-monitor for this E2 node")
        print(
            f"KPM subscribed on node[0], handle={kpm_handle}, period={args.period_ms}ms, "
            f"metrics={args.kpm_metrics}"
        )

    if args.profile in ("rc", "both"):
        _run_rc_scaffold(node)

    started = time.time()
    print(f"KPM/RC suite running profile='{args.profile}' for {args.duration_s}s (Ctrl+C to stop early)")
    try:
        while not stop_requested:
            time.sleep(0.1)
            if args.duration_s > 0 and (time.time() - started) >= args.duration_s:
                print(f"Auto-stop after {args.duration_s}s")
                break
    finally:
        if kpm_handle is not None:
            try:
                ric.rm_report_kpm_sm(kpm_handle)
            except Exception as e:
                print(f"Warning: failed to remove KPM subscription cleanly: {e}")
        while ric.try_stop() is False:
            time.sleep(0.1)
        print("KPM/RC suite finished")


if __name__ == "__main__":
    main()
