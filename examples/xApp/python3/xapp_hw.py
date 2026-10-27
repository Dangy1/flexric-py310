#!/usr/bin/env python3
import time

import xapp_sdk as ric


def _safe_node_id_summary(node) -> str:
    try:
        return ric.get_e2_node_id_summary(node)
    except Exception:
        return "id_fields=unavailable (SWIG raw object)"


def main() -> None:
    ric.init()
    time.sleep(1)

    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")

    print(f"Connected E2 nodes = {len(nodes)}")
    for i, node in enumerate(nodes):
        print(f"E2 node {i}: {_safe_node_id_summary(node)}")
        try:
            ran_ids = [str(x) for x in ric.get_ran_func_ids(node)]
            print(f"E2 node {i} supported RAN function IDs: {', '.join(ran_ids)}")
        except Exception:
            print(f"E2 node {i} supported RAN function IDs: unavailable (SWIG raw object)")

    print("Hello World")

    while ric.try_stop() is False:
        time.sleep(0.1)

    print("Test xApp run SUCCESSFULLY")


if __name__ == "__main__":
    main()
