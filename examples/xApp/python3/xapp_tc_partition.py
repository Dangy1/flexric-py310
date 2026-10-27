#!/usr/bin/env python3
import argparse
import time

import xapp_sdk as ric
from xapp_tc_common import init_first_node, send_tc, stop


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-port", type=int, default=9091)
    args = ap.parse_args()

    node = init_first_node()

    send_tc(node.id, ric.tc_gen_mod_bdp_pcr(20000, int(time.time_ns() / 1000)))
    for _ in range(2):
        send_tc(node.id, ric.tc_gen_add_fifo_queue())

    send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port, -1, -1, -1, -1, 1))

    stop()
    print("TC partition demo finished")


if __name__ == "__main__":
    main()
