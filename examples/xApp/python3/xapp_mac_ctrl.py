#!/usr/bin/env python3
import time

import xapp_sdk as ric


def main() -> None:
    ric.init()
    time.sleep(1)

    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")

    print(f"Connected E2 nodes = {len(nodes)}")

    for i, node in enumerate(nodes):
        try:
            ran_ids = [str(x) for x in ric.get_ran_func_ids(node)]
            print(f"Node {i} RAN functions: {', '.join(ran_ids)}")
        except Exception:
            print(f"Node {i} RAN functions: unavailable (SWIG raw object)")

        ctrl = ric.mac_ctrl_msg_t()
        ctrl.action = 42
        ric.control_mac_sm(node.id, ctrl)
        print(f"Sent MAC control action=42 to node {i}")

    while ric.try_stop() is False:
        time.sleep(0.1)

    print("Test xApp run SUCCESSFULLY")


if __name__ == "__main__":
    main()
