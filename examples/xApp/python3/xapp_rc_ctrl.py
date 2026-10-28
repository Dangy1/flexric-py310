#!/usr/bin/env python3
"""E2SM-RC xApp: real RIC CONTROL (Radio Bearer Control) or RC REPORT subscription.

Profiles
--------
control  Sends one E2 RIC CONTROL REQUEST with E2SM-RC Control Service Style 1
         ("Radio Bearer Control"), Control Action 2 ("QoS flow mapping
         configuration"): DRB id, one QoS flow (QFI) and its mapping indication
         (UL/DL) for one UE (gNB UE ID, AMF UE NGAP ID). Prints
         "RC CONTROL-ACK received" when the E2 node's RIC CONTROL ACKNOWLEDGE
         reaches the xApp, "RC CONTROL-FAILED" otherwise.
report   Subscribes to E2SM-RC REPORT Service Style 4 ("UE Information", event
         trigger format 4 = UE information change, RRC state) and prints
         "RC indication received" for every RIC INDICATION, "RC REPORT-FAILED"
         when the subscription cannot be built or no indication arrives.

Both messages are built in C++ (src/xApp/swig/swig_wrapper.cpp:
control_rc_sm_qos_flow_map / report_rc_sm_auto) from the RAN function
definition the E2 node advertised at E2 Setup, and are sent only when the node
advertises the matching style/action.

Why two processes: in the Release build of the FlexRIC E2 library the
synchronous control call does not distinguish an ACK from a timeout (the
assert that would catch the timeout is compiled out) and a CONTROL FAILURE or
lost RIC aborts the process. A small supervisor therefore runs the E2 worker as
a child, watches the library's own "[xApp]: CONTROL ACK rx" line (printed only
by the RIC CONTROL ACKNOWLEDGE handler) and prints a single unambiguous
verdict line.

Targeting another nearRT-RIC (e.g. the emulator twin): --ric-conf PATH, or the
FLEXRIC_XAPP_CONF environment variable, selects the FlexRIC config file whose
NEAR_RIC_IP the xApp connects to (default /usr/local/etc/flexric/flexric.conf).
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

ACK_MARKER = "RC CONTROL-ACK received"
CONTROL_FAILED_MARKER = "RC CONTROL-FAILED"
IND_MARKER = "RC indication received"
REPORT_FAILED_MARKER = "RC REPORT-FAILED"
# Printed by the FlexRIC E2 library (src/xApp/msg_handler_xapp.c) only in the
# RIC CONTROL ACKNOWLEDGE handler.
LIB_CONTROL_ACK_LINE = "[xApp]: CONTROL ACK rx"
WORKER_CONTROL_SENT = "RC CONTROL sending:"

SM_RC_ID = 3


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FlexRIC E2SM-RC control/report xApp")
    p.add_argument("--profile", choices=["control", "report"], default="control")
    p.add_argument("--duration-s", type=float, default=10.0,
                   help="Keep the xApp connected for N s (control: after the ACK; report: subscription window). 0 = exit right after the control ACK / first indications.")
    p.add_argument("--ric-conf", default="", help="FlexRIC config file to use (sets FLEXRIC_XAPP_CONF for init())")
    p.add_argument("--node-timeout-s", type=float, default=5.0, help="Wait this long for a connected E2 node")
    p.add_argument("--amf-ue-ngap-id", type=int, default=1, help="Control: target UE (gNB UE ID, AMF UE NGAP ID)")
    p.add_argument("--drb-id", type=int, default=5, help="Control: DRB ID (RAN parameter 1)")
    p.add_argument("--qfi", type=int, default=10, help="Control: QoS Flow Identifier 0..63 (RAN parameter 4)")
    p.add_argument("--dir", choices=["ul", "dl"], default="dl", help="Control: QoS flow mapping indication (RAN parameter 5)")
    p.add_argument("--max-print", type=int, default=20, help="Report: print at most N indications")
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


# --------------------------------------------------------------------------- worker

def _line_buffer_c_stdout() -> None:
    """Make the C library's printf output line-buffered so its lines interleave
    with ours in order when stdout is a pipe or a log file."""
    try:
        import ctypes

        libc = ctypes.CDLL(None)
        c_stdout = ctypes.c_void_p.in_dll(libc, "stdout")
        libc.setvbuf(c_stdout, None, 1, 0)  # _IOLBF
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"RC worker: could not line-buffer C stdout ({exc})", flush=True)


def _worker(args: argparse.Namespace) -> int:
    _line_buffer_c_stdout()
    if args.ric_conf:
        os.environ["FLEXRIC_XAPP_CONF"] = args.ric_conf

    import xapp_sdk as ric

    stop = {"flag": False}

    def _on_signal(_sig, _frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    conf = os.environ.get("FLEXRIC_XAPP_CONF") or "/usr/local/etc/flexric/flexric.conf (default)"
    print(f"RC xApp starting: profile={args.profile} conf={conf}", flush=True)
    ric.init()

    nodes = []
    deadline = time.time() + max(0.5, args.node_timeout_s)
    while time.time() < deadline and not stop["flag"]:
        nodes = ric.conn_e2_nodes()
        if len(nodes) > 0:
            break
        time.sleep(0.2)

    rc_code = 1
    handle = None
    cb = None
    try:
        if len(nodes) == 0:
            fail = CONTROL_FAILED_MARKER if args.profile == "control" else REPORT_FAILED_MARKER
            print(f"{fail}: no E2 node connected to the nearRT-RIC within {args.node_timeout_s:.1f}s", flush=True)
            return 2

        target = None
        for i, node in enumerate(nodes):
            ran_ids = [int(x) for x in ric.get_ran_func_ids(node)]
            print(f"E2 node {i}: {ric.get_e2_node_id_summary(node)} ran_functions={ran_ids}", flush=True)
            if SM_RC_ID in ran_ids and target is None:
                target = node
                summary = ric.rc_ran_func_summary(node.id)
                print(f"E2 node {i} E2SM-RC: {summary}", flush=True)

        if target is None:
            fail = CONTROL_FAILED_MARKER if args.profile == "control" else REPORT_FAILED_MARKER
            print(f"{fail}: no connected E2 node advertises E2SM-RC (RAN function {SM_RC_ID})", flush=True)
            return 2

        if args.profile == "control":
            direction = 1 if args.dir == "dl" else 0
            print(
                f"{WORKER_CONTROL_SENT} E2SM-RC style 1 (Radio Bearer Control) action 2 (QoS flow mapping configuration) "
                f"amf_ue_ngap_id={args.amf_ue_ngap_id} drb_id={args.drb_id} qfi={args.qfi} dir={args.dir}",
                flush=True,
            )
            t0 = time.time()
            res = ric.control_rc_sm_qos_flow_map(target.id, args.amf_ue_ngap_id, args.drb_id, args.qfi, direction)
            dt_ms = (time.time() - t0) * 1000.0
            if res == -1:
                print(f"{CONTROL_FAILED_MARKER}: node does not advertise E2SM-RC", flush=True)
                return 2
            if res == -2:
                print(f"{CONTROL_FAILED_MARKER}: node does not advertise RC control style 1 / action 2", flush=True)
                return 2
            print(f"RC control call returned after {dt_ms:.1f} ms (res={res})", flush=True)
            rc_code = 0
        else:
            state = {"n": 0}

            class _RCCallback(ric.rc_cb):
                def handle(self, ind):  # noqa: D401 - SWIG director
                    state["n"] += 1
                    if state["n"] <= args.max_print:
                        print(f"{IND_MARKER}: #{state['n']} {ric.rc_ind_summary(ind)}", flush=True)

            cb = _RCCallback()
            t0 = time.time()
            handle = ric.report_rc_sm_auto(target.id, cb)
            if handle < 0:
                print(f"{REPORT_FAILED_MARKER}: node advertises no compatible RC REPORT style (need style 4, event trigger format 4, action format 1)", flush=True)
                handle = None
                return 2
            print(f"RC REPORT subscribed: style 4 (UE Information) handle={handle} in {(time.time() - t0) * 1000.0:.1f} ms", flush=True)
            rc_code = 0

        started = time.time()
        while not stop["flag"]:
            if args.profile == "report" and args.duration_s <= 0 and state["n"] > 0:
                break
            if args.duration_s > 0 and time.time() - started >= args.duration_s:
                break
            if args.duration_s <= 0 and args.profile == "control":
                break
            if args.duration_s <= 0 and time.time() - started >= 5.0:
                break
            time.sleep(0.05)

        if args.profile == "report":
            print(f"RC REPORT window closed: {state['n']} indication(s) received", flush=True)
            if state["n"] == 0:
                rc_code = 3
        return rc_code
    finally:
        if handle is not None:
            try:
                ric.rm_report_rc_sm(handle)
                print("RC REPORT subscription removed", flush=True)
            except Exception as exc:  # pragma: no cover
                print(f"RC worker warning: failed to remove RC subscription: {exc}", flush=True)
        while ric.try_stop() is False:
            time.sleep(0.1)
        _ = cb


# --------------------------------------------------------------------------- supervisor

def _supervise(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    if args.ric_conf:
        if not os.path.isfile(args.ric_conf):
            fail = CONTROL_FAILED_MARKER if args.profile == "control" else REPORT_FAILED_MARKER
            print(f"{fail}: config file {args.ric_conf} not found", flush=True)
            return 2
        env["FLEXRIC_XAPP_CONF"] = os.path.abspath(args.ric_conf)
    cmd = [sys.executable, "-u", os.path.abspath(__file__), *sys.argv[1:], "--worker"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                            text=True, bufsize=1, errors="replace")

    signals_seen = {"n": 0}

    def _forward(_sig, _frame):
        signals_seen["n"] += 1
        try:
            proc.send_signal(signal.SIGINT if signals_seen["n"] == 1 else signal.SIGKILL)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGINT, _forward)
    signal.signal(signal.SIGTERM, _forward)

    # Hard stop: init + node wait + one control/subscription + window + teardown.
    hard_deadline = time.time() + args.node_timeout_s + max(args.duration_s, 5.0) + 20.0
    acked = False
    sent_at = None
    n_ind = 0
    worker_failed_line = None
    import threading

    def _watchdog():
        while proc.poll() is None:
            if time.time() > hard_deadline:
                print("RC supervisor: worker exceeded its time budget, killing it", flush=True)
                proc.kill()
                return
            time.sleep(0.2)

    threading.Thread(target=_watchdog, daemon=True).start()

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        print(line, flush=True)
        if line.startswith(WORKER_CONTROL_SENT):
            sent_at = time.time()
        elif LIB_CONTROL_ACK_LINE in line and args.profile == "control" and not acked:
            acked = True
            lat = f"{(time.time() - sent_at) * 1000.0:.1f}" if sent_at else "n/a"
            print(f"{ACK_MARKER}: E2 RIC CONTROL ACKNOWLEDGE for E2SM-RC style 1 action 2 (QoS flow mapping) latency_ms={lat}", flush=True)
        elif line.startswith(IND_MARKER):
            n_ind += 1
        elif line.startswith(CONTROL_FAILED_MARKER) or line.startswith(REPORT_FAILED_MARKER):
            worker_failed_line = line
    code = proc.wait()

    if args.profile == "control":
        if not acked and worker_failed_line is None:
            print(f"{CONTROL_FAILED_MARKER}: no E2 RIC CONTROL ACKNOWLEDGE received (worker exit code {code})", flush=True)
        ok = acked
    else:
        if n_ind == 0 and worker_failed_line is None:
            print(f"{REPORT_FAILED_MARKER}: no RC indication received (worker exit code {code})", flush=True)
        ok = n_ind > 0
    print(f"RC xApp finished: profile={args.profile} ok={ok} control_acked={acked} indications={n_ind} worker_exit={code}", flush=True)
    return 0 if ok else 1


def main() -> None:
    args = _parse_args()
    if args.worker:
        sys.exit(_worker(args))
    sys.exit(_supervise(args))


if __name__ == "__main__":
    main()
