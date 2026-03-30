#!/usr/bin/env python3
import argparse

import xapp_sdk as ric
from xapp_tc_common import init_first_node, send_tc, stop


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-port", type=int, default=9091)
    args = ap.parse_args()

    node = init_first_node()

    for _ in range(3):
        send_tc(node.id, ric.tc_gen_add_fifo_queue())

    send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port, -1, -1, -1, -1, 2))
    send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port + 1, -1, -1, -1, -1, 2))
    send_tc(node.id, ric.tc_gen_add_osi_cls(args.src_port + 2, -1, -1, -1, -1, 2))
    send_tc(node.id, ric.tc_gen_mod_shaper(2, 100, 15000, 1))

    stop()
    print("TC shaper demo finished")


if __name__ == "__main__":
    main()
