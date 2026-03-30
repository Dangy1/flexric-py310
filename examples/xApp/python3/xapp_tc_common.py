#!/usr/bin/env python3
import atexit
import fcntl
import os
import time
from typing import Iterable

import xapp_sdk as ric

TC_SM_ID = 146
_LOCK_FD = None
_LOCK_PATH = "/tmp/flexric_python_tc_xapp.lock"


def _acquire_single_instance_lock() -> None:
    global _LOCK_FD
    if _LOCK_FD is not None:
        return

    fd = os.open(_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise RuntimeError(
            "Another TC Python xApp is already running. "
            "Stop it first to avoid SCTP setup collisions."
        )
    _LOCK_FD = fd


def _release_single_instance_lock() -> None:
    global _LOCK_FD
    if _LOCK_FD is None:
        return
    try:
        fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
    finally:
        os.close(_LOCK_FD)
        _LOCK_FD = None


atexit.register(_release_single_instance_lock)


def init_first_node():
    _acquire_single_instance_lock()
    ric.init()
    time.sleep(1)
    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")
    node = nodes[0]
    print(f"Connected E2 nodes = {len(nodes)}")
    # Depending on SWIG typing, ran_func may be a proper vector wrapper or a raw SwigPyObject.
    # Keep this diagnostic best-effort only.
    try:
        ran_ids = [str(x) for x in ric.get_ran_func_ids(node)]
        print(f"Node 0 RAN functions: {', '.join(ran_ids)}")
    except Exception:
        print("Node 0 RAN functions: unavailable (SWIG raw object)")
    return node


def send_tc(node_id, msg) -> None:
    ric.control_tc_sm(node_id, msg)
    ric.free_tc_ctrl_msg(msg)
    time.sleep(0.01)


def send_many(node_id, msgs: Iterable) -> None:
    for msg in msgs:
        send_tc(node_id, msg)


def stop() -> None:
    while ric.try_stop() is False:
        time.sleep(0.1)
