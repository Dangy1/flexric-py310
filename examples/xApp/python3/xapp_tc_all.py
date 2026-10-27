#!/usr/bin/env python3
import argparse
import time

import xapp_sdk as ric
from xapp_tc_common import init_first_node, send_tc, stop


class RLCCallback(ric.rlc_cb):
    def __init__(self):
        super().__init__()

    def handle(self, ind):
        if len(ind.rb_stats) > 0:
            print(f"RLC len={len(ind.rb_stats)} tstamp={ind.tstamp}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-s", type=int, default=180, help="Monitoring duration in seconds (default: 180)")
    args = ap.parse_args()

    node = init_first_node()

    rlc_cb = RLCCallback()
    hnd = ric.report_rlc_sm(node.id, ric.Interval_ms_5, rlc_cb)

    send_tc(node.id, ric.tc_gen_mod_bdp_pcr(25000, int(time.time_ns() / 1000)))
    send_tc(node.id, ric.tc_gen_add_codel_queue(400, 20))
    send_tc(node.id, ric.tc_gen_add_osi_cls(-1, 5201, -1, -1, -1, 1))

    print(f"TC all demo running for {args.duration_s}s (Ctrl+C to stop early)")
    try:
        time.sleep(max(0, args.duration_s))
    except KeyboardInterrupt:
        pass
    ric.rm_report_rlc_sm(hnd)

    stop()
    print("TC all demo finished")


if __name__ == "__main__":
    main()
