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


def _apply_profile(node, args) -> None:
    now_us = int(time.time_ns() / 1000)

    if args.profile == "segregate":
        send_tc(node.id, ric.tc_gen_add_fifo_queue())
        send_tc(node.id, ric.tc_gen_add_osi_cls(-1, -1, -1, -1, -1, 1))
        return

    if args.profile == "partition":
        send_tc(node.id, ric.tc_gen_mod_bdp_pcr(args.pcr_drb_sz, now_us))
        for _ in range(2):
            send_tc(node.id, ric.tc_gen_add_fifo_queue())
        send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port, -1, -1, -1, -1, 1))
        return

    if args.profile == "shaper":
        for _ in range(3):
            send_tc(node.id, ric.tc_gen_add_fifo_queue())
        send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port, -1, -1, -1, -1, 2))
        send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port + 1, -1, -1, -1, -1, 2))
        send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port + 2, -1, -1, -1, -1, 2))
        send_tc(node.id, ric.tc_gen_mod_shaper(args.shaper_id, args.shaper_window_ms, args.shaper_rate_kbps, 1))
        return

    if args.profile == "codel":
        send_tc(node.id, ric.tc_gen_mod_bdp_pcr(args.pcr_drb_sz, now_us))
        send_tc(node.id, ric.tc_gen_add_codel_queue(args.codel_interval_ms, args.codel_target_ms))
        send_tc(node.id, ric.tc_gen_add_osi_cls(-1, -1, -1, -1, -1, 1))
        return

    if args.profile == "ecn":
        send_tc(node.id, ric.tc_gen_mod_bdp_pcr(args.pcr_drb_sz, now_us))
        send_tc(node.id, ric.tc_gen_add_ecn_queue(args.codel_interval_ms, args.codel_target_ms))
        send_tc(node.id, ric.tc_gen_add_osi_cls(-1, -1, -1, -1, -1, 1))
        return

    if args.profile == "osi_codel":
        send_tc(node.id, ric.tc_gen_mod_bdp_pcr(args.pcr_drb_sz, now_us))
        send_tc(node.id, ric.tc_gen_add_codel_queue(args.codel_interval_ms, args.codel_target_ms))
        send_tc(node.id, ric.tc_gen_add_osi_cls(-1, args.dst_port, args.protocol, -1, -1, 1))
        return

    if args.profile == "all":
        send_tc(node.id, ric.tc_gen_mod_bdp_pcr(args.pcr_drb_sz, now_us))
        send_tc(node.id, ric.tc_gen_add_codel_queue(args.codel_interval_ms, args.codel_target_ms))
        send_tc(node.id, ric.tc_gen_add_osi_cls(-1, args.dst_port, args.protocol, -1, -1, 1))
        return

    raise ValueError(f"Unsupported profile: {args.profile}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Unified TC xApp demo runner (Python/SWIG)")
    ap.add_argument(
        "--profile",
        required=True,
        choices=["segregate", "partition", "shaper", "codel", "ecn", "osi_codel", "all"],
        help="TC demo profile to apply",
    )
    ap.add_argument("--duration-s", type=int, default=180, help="Run duration after applying profile (default: 180)")
    ap.add_argument("--src-port", type=int, default=9091, help="Source port used by partition/shaper profiles")
    ap.add_argument("--dst-port", type=int, default=5201, help="Destination port used by all/osi_codel profiles")
    ap.add_argument("--protocol", type=int, default=-1, help="L4 protocol filter (e.g., 6 for TCP); -1 means any")
    ap.add_argument("--pcr-drb-sz", type=int, default=25000, help="PCR BDP DRB size")
    ap.add_argument("--codel-interval-ms", type=int, default=400, help="CoDel/ECN interval ms")
    ap.add_argument("--codel-target-ms", type=int, default=20, help="CoDel/ECN target ms")
    ap.add_argument("--shaper-id", type=int, default=2, help="Shaper ID for shaper profile")
    ap.add_argument("--shaper-window-ms", type=int, default=100, help="Shaper time window in ms")
    ap.add_argument("--shaper-rate-kbps", type=int, default=15000, help="Shaper max rate kbps")
    ap.add_argument("--monitor-rlc", action="store_true", help="Subscribe to RLC SM and print RLC indications")
    args = ap.parse_args()

    node = init_first_node()

    rlc_cb = None
    hnd = None
    if args.monitor_rlc or args.profile == "all":
        rlc_cb = RLCCallback()
        hnd = ric.report_rlc_sm(node.id, ric.Interval_ms_5, rlc_cb)

    _apply_profile(node, args)

    print(f"Applied TC profile '{args.profile}'. Running for {args.duration_s}s (Ctrl+C to stop early)")
    try:
        time.sleep(max(0, args.duration_s))
    except KeyboardInterrupt:
        pass

    if hnd is not None:
        ric.rm_report_rlc_sm(hnd)

    stop()
    print(f"TC suite profile '{args.profile}' finished")


if __name__ == "__main__":
    main()
