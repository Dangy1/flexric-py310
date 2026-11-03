"""Bounded xApp shutdown shared by the portal suites.

Removing a subscription (`rm_report_*`) or stopping the FlexRIC xApp SDK (`try_stop`) can block
indefinitely after the RIC has answered the delete (seen on the SLICE suite in about one run of three).
The blocking SWIG call holds the GIL, so a Python thread or signal handler never runs; the process then
keeps its portal lease for minutes. faulthandler's watchdog is a native thread that needs no GIL: if
cleanup has not finished in time it writes where the process was stuck and exits (code 1). The xApp's
work is already done at that point, and its acknowledgement markers are already in the log.
"""
from __future__ import annotations

import faulthandler
import sys
import time


def arm_exit_watchdog(timeout_s: float = 12.0, label: str = "xApp") -> None:
    """Arm at the start of cleanup; `disarm_exit_watchdog` (or `stop_with_watchdog`) cancels it."""
    print(f"{label}: cleanup started (exit watchdog {timeout_s:.0f}s)", flush=True)
    faulthandler.dump_traceback_later(timeout_s, exit=True, file=sys.stdout)


def disarm_exit_watchdog() -> None:
    faulthandler.cancel_dump_traceback_later()


def stop_with_watchdog(ric, timeout_s: float = 12.0, label: str = "xApp") -> bool:
    """Stop the xApp SDK within `timeout_s` (the watchdog covers a call that never returns)."""
    faulthandler.dump_traceback_later(timeout_s, exit=True, file=sys.stdout)
    deadline = time.monotonic() + timeout_s
    try:
        while ric.try_stop() is False:
            if time.monotonic() > deadline:
                return False
            time.sleep(0.1)
        return True
    finally:
        faulthandler.cancel_dump_traceback_later()
