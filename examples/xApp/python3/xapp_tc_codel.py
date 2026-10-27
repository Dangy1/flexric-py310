#!/usr/bin/env python3
import time

import xapp_sdk as ric
from xapp_tc_common import init_first_node, send_tc, stop


def main() -> None:
    node = init_first_node()

    send_tc(node.id, ric.tc_gen_mod_bdp_pcr(25000, int(time.time_ns() / 1000)))
    send_tc(node.id, ric.tc_gen_add_codel_queue(100, 5))
    send_tc(node.id, ric.tc_gen_add_osi_cls(-1, -1, -1, -1, -1, 1))

    stop()
    print("TC CODEL demo finished")


if __name__ == "__main__":
    main()
