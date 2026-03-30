#!/usr/bin/env python3
import time

import xapp_sdk as ric


class RCCallback(ric.rc_cb):
    def __init__(self):
        super().__init__()

    def handle(self, ind):
        print(f"RC indication received: proc_id={ind.proc_id}")


def main() -> None:
    ric.init()
    time.sleep(1)

    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")

    # NOTE:
    # The RC subscription payload depends on node-advertised RC report style and
    # parameters (same as xapp_rc_moni.c). Build rc_sub_data_t accordingly.
    sub = ric.rc_sub_data_t()
    print("RC demo scaffold ready. Populate rc_sub_data_t before report_rc_sm().")

    _ = (nodes, sub, RCCallback)

    while ric.try_stop() is False:
        time.sleep(0.1)


if __name__ == "__main__":
    main()
