#!/usr/bin/env python3
import argparse
import signal
import time

import xapp_sdk as ric

stop_requested = False


def _on_sigint(_sig, _frame):
    global stop_requested
    stop_requested = True
    print("\nStopping KPM monitor gracefully...")


class KPMParsedCallback(ric.kpm_moni_cb):
    def __init__(self, metric_mode: str = "rru"):
        super().__init__()
        self.metric_mode = metric_mode

    def handle(self, msg):
        # Support the same metric filters used by the MCP KPM/RC suite.
        for rec in msg.records:
            if self.metric_mode == "all":
                print(rec)
            elif self.metric_mode == "rru":
                if "meas=RRU.PrbTotDl " in rec or "meas=RRU.PrbTotUl " in rec:
                    print(rec)
            elif self.metric_mode == "ue":
                if "meas=DRB." in rec:
                    print(rec)
            else:
                print(rec)


def main() -> None:
    parser = argparse.ArgumentParser(description="FlexRIC KPM monitor")
    parser.add_argument("--period-ms", type=int, default=1000, help="KPM reporting period in ms")
    parser.add_argument("--duration-s", type=int, default=30, help="Auto-stop after N seconds (0 = run forever)")
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

    node = nodes[0]
    period_ms = args.period_ms
    cb = KPMParsedCallback(metric_mode=args.kpm_metrics)
    handle = ric.report_kpm_sm_auto_py(node.id, period_ms, cb)
    if handle < 0:
        raise RuntimeError("Failed to build/subscribe KPM auto-monitor for this E2 node")

    print(
        f"KPM monitor subscribed on node[0], handle={handle}, period={period_ms}ms, "
        f"metrics={args.kpm_metrics}"
    )
    if args.kpm_metrics == "rru":
        print("Waiting for KPM indications (RRU.PrbTotDl / RRU.PrbTotUl only).")
    elif args.kpm_metrics == "ue":
        print("Waiting for KPM indications (DRB.* UE metrics only).")
    else:
        print("Waiting for KPM indications (all parsed records).")
    print("Avoid Ctrl+C when possible; use --duration-s for graceful exit.")
    started = time.time()
    last_hint = started

    try:
        while stop_requested is False:
            time.sleep(0.1)
            now = time.time()
            if args.duration_s > 0 and (now - started) >= args.duration_s:
                print(f"Auto-stop after {args.duration_s}s")
                break
            if (now - last_hint) >= 10:
                print("Still waiting for KPM indications...")
                last_hint = now
    finally:
        try:
            ric.rm_report_kpm_sm(handle)
        except Exception as e:
            print(f"Warning: failed to remove KPM subscription cleanly: {e}")
        while ric.try_stop() is False:
            time.sleep(0.1)


if __name__ == "__main__":
    main()
