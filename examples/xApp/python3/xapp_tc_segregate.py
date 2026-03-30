#!/usr/bin/env python3

import xapp_sdk as ric
from xapp_tc_common import init_first_node, send_tc, stop


def main() -> None:
    node = init_first_node()

    send_tc(node.id, ric.tc_gen_add_fifo_queue())
    send_tc(node.id, ric.tc_gen_add_osi_cls(-1, -1, -1, -1, -1, 1))

    stop()
    print("TC segregate demo finished")


if __name__ == "__main__":
    main()
