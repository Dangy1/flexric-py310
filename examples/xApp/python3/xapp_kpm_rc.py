#!/usr/bin/env python3
import time

import xapp_sdk as ric


class KPMCallback(ric.kpm_cb):
    def __init__(self):
        super().__init__()

    def handle(self, ind):
        print(f"KPM ind proc_id={ind.proc_id}")


def main() -> None:
    ric.init()
    time.sleep(1)

    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")

    print("KPM+RC demo scaffold ready.")
    print("1) Build kpm_sub_data_t from KPM report style")
    print("2) Build rc_ctrl_req_data_t from RC control style")
    print("3) Call report_kpm_sm(...) and control_rc_sm(...)")

    _ = (nodes, KPMCallback)

    while ric.try_stop() is False:
        time.sleep(0.1)


if __name__ == "__main__":
    main()
