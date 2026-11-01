#!/usr/bin/env python3
"""Demo D3: an AppWeaver TC action changes a real queue (bufferbloat -> CoDel), measured on the link.

Data plane (unprivileged: user + network namespaces, no root): namespace U holds veth v0 and the sender;
namespace N (inside U) holds v1 and the receiver. v0's egress is the bottleneck: tbf 10 Mbit/s with a deep
FIFO (pfifo 2000 packets, ~2.4 s of buffer), i.e. a bufferbloated transport link. Four bulk TCP flows U->N
fill it; ping U->N every 100 ms measures the queueing delay seen by everything else on the link.

Control plane: a private FlexRIC nearRT-RIC on 127.0.0.3 (never the live 127.0.0.1 or the twin 127.0.0.2)
and tc_dp_agent_gnb, whose E2SM-TC queue control runs tc_hook.sh on v0 (sm_tc_dp.c). At t = --act-s the
demo launches exactly what AppWeaver's TC card runs for action apply-codel
(backend/agents/tc.py: xapp_tc_suite.py --profile codel; CoDel target 20 ms, interval 400 ms), with
FLEXRIC_XAPP_CONF pointing at the private RIC. The only path from the xApp to the queue is E2.

Output per repeat (--out/rep<k>/): ping.txt (ping -D), rx.csv (receiver bytes per 100 ms), hook.log (the
tc change with its wall-clock time), xapp.log, agent.log, ric.log; summary.{json,md} over repeats: RTT
median/p95 and goodput before (act-10 s .. act) and after (act+2 s .. end) the control.

  python run_tc_demo.py --out <dir> [--repeats 3] [--duration-s 40] [--act-s 15]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY_DIR = HERE.parents[2]                                   # examples/xApp/python3
BUILD = PY_DIR.parents[2] / "build"                        # ~/flexric/build
BUILD_PY = BUILD / "examples" / "xApp" / "python3"
RIC_BIN = BUILD / "examples" / "ric" / "nearRT-RIC"
AGENT_BIN = BUILD / "examples" / "emulator" / "agent" / "tc_dp_agent_gnb"
LIBS = os.getenv("FLEXRIC_LIBS_DIR", "/usr/local/lib/flexric/")
RIC_IP = "127.0.0.3"
RATE = "10mbit"
FIFO_LIMIT = 2000
FLOWS = 4  # bulk TCP flows (CUBIC) through the bottleneck
XAPP_CMD = ["xapp_tc_suite.py", "--profile", "codel", "--duration-s", "10"]  # = AppWeaver apply-codel (tc.py)


def sh(*args, **kw):
    return subprocess.run(list(args), check=True, capture_output=True, text=True, **kw)


def ns(pid: int, *cmd: str) -> list:
    return ["nsenter", "-t", str(pid), "-U", "-n", "--preserve-credentials", *cmd]


def setup_net(log: Path):
    outer = subprocess.Popen(["unshare", "-rn", "sleep", "infinity"], start_new_session=True)
    time.sleep(0.3)
    inner = subprocess.Popen(ns(outer.pid, "unshare", "-n", "sleep", "infinity"), start_new_session=True)
    time.sleep(0.3)
    inner_pid = inner.pid  # nsenter (no pid namespace) and unshare (no --fork) exec: this pid is the sleep in N
    steps = [
        ns(outer.pid, "ip", "link", "set", "lo", "up"),
        ns(outer.pid, "ip", "link", "add", "v0", "type", "veth", "peer", "name", "v1"),
        ns(outer.pid, "ip", "link", "set", "v1", "netns", str(inner_pid)),
        ns(outer.pid, "ip", "addr", "add", "10.9.0.1/24", "dev", "v0"),
        ns(outer.pid, "ip", "link", "set", "v0", "up"),
        ns(inner_pid, "ip", "link", "set", "lo", "up"),
        ns(inner_pid, "ip", "addr", "add", "10.9.0.2/24", "dev", "v1"),
        ns(inner_pid, "ip", "link", "set", "v1", "up"),
        ns(outer.pid, "tc", "qdisc", "add", "dev", "v0", "root", "handle", "1:", "tbf", "rate", RATE, "burst", "32kbit", "limit", "4000000"),
        ns(outer.pid, "tc", "qdisc", "add", "dev", "v0", "parent", "1:1", "handle", "10:", "pfifo", "limit", str(FIFO_LIMIT)),
    ]
    with log.open("w") as handle:
        for cmd in steps:
            res = subprocess.run(cmd, capture_output=True, text=True)
            handle.write(f"{' '.join(cmd[5:])} -> {res.returncode} {res.stderr.strip()}\n")
            if res.returncode:
                raise RuntimeError(f"net setup failed: {' '.join(cmd)}: {res.stderr}")
    return outer, inner, inner_pid


RECEIVER = r"""
import socket, sys, threading, time
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("10.9.0.2", 5201)); s.listen(16)
acc = [0]; lock = threading.Lock()
def sink(c):
    while True:
        b = c.recv(65536)
        if not b: return
        with lock: acc[0] += len(b)
def log():
    out = open(sys.argv[1], "w"); out.write("t,bytes\n")
    while True:
        time.sleep(0.1)
        with lock: n, acc[0] = acc[0], 0
        out.write(f"{time.time():.3f},{n}\n"); out.flush()
threading.Thread(target=log, daemon=True).start()
while True:
    c, _ = s.accept(); threading.Thread(target=sink, args=(c,), daemon=True).start()
"""
SENDER = r"""
import socket, sys, threading, time
end = time.time() + float(sys.argv[1])
def flow():
    c = socket.create_connection(("10.9.0.2", 5201)); c.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20); buf = b"x" * 65536
    while time.time() < end: c.sendall(buf)
    c.close()
ts = [threading.Thread(target=flow) for _ in range(int(sys.argv[2]))]; [t.start() for t in ts]; [t.join() for t in ts]
"""


def one_repeat(out: Path, duration: float, act_s: float, python: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    procs = []
    outer, inner, inner_pid = setup_net(out / "net.log")
    procs += [outer, inner]
    conf = out / "flexric.conf"
    (out / "db").mkdir(exist_ok=True)
    conf.write_text(f"[NEAR-RIC]\nNEAR_RIC_IP = {RIC_IP}\n\n[XAPP]\nDB_DIR = {out / 'db'}/\n")
    hook_log = out / "hook.log"
    env = {**os.environ, "TC_DP_HOOK": str(HERE / "tc_hook.sh"), "TC_DP_NS_PID": str(outer.pid), "TC_DP_LOG": str(hook_log),
           "TC_DP_FIFO_LIMIT": str(FIFO_LIMIT)}
    try:
        ric = subprocess.Popen([str(RIC_BIN), "-c", str(conf), "-p", LIBS], cwd=out, stdout=(out / "ric.log").open("w"),
                               stderr=subprocess.STDOUT, start_new_session=True)
        procs.append(ric)
        time.sleep(1.5)
        agent = subprocess.Popen([str(AGENT_BIN), "-c", str(conf), "-p", LIBS], cwd=out, env=env,
                                 stdout=(out / "agent.log").open("w"), stderr=subprocess.STDOUT, start_new_session=True)
        procs.append(agent)
        time.sleep(2.0)
        rx = subprocess.Popen(ns(inner_pid, python, "-c", RECEIVER, str(out / "rx.csv")), start_new_session=True)
        procs.append(rx)
        time.sleep(0.5)
        t0 = time.time()
        ping = subprocess.Popen(ns(outer.pid, "ping", "-D", "-i", "0.1", "-w", str(int(duration)), "10.9.0.2"),
                                stdout=(out / "ping.txt").open("w"), stderr=subprocess.STDOUT, start_new_session=True)
        procs.append(ping)
        tx = subprocess.Popen(ns(outer.pid, python, "-c", SENDER, str(duration), str(FLOWS)), start_new_session=True)
        procs.append(tx)
        time.sleep(act_s)
        t_act = time.time()
        xenv = {**os.environ, "FLEXRIC_XAPP_CONF": str(conf), "PYTHONPATH": f"{BUILD_PY}:{os.environ.get('PYTHONPATH', '')}"}
        xapp = subprocess.run([python, *XAPP_CMD], cwd=BUILD_PY, env=xenv, capture_output=True, text=True, timeout=60)
        (out / "xapp.log").write_text(xapp.stdout + xapp.stderr)
        tx.wait(timeout=duration + 30)
        ping.wait(timeout=30)
        return {"t0": t0, "t_act_launch": t_act, "xapp_rc": xapp.returncode, "duration_s": duration, "act_s": act_s,
                "ns_pid": outer.pid}
    finally:
        for p in reversed(procs):
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except Exception:
                pass
        time.sleep(1.0)


def analyse(rep: Path, meta: dict) -> dict:
    rtts = []
    for line in (rep / "ping.txt").read_text(errors="replace").splitlines():
        m = re.match(r"\[(\d+\.\d+)\].*time=([\d.]+) ms", line)
        if m:
            rtts.append((float(m.group(1)), float(m.group(2))))
    hook = [l.split() for l in (rep / "hook.log").read_text().splitlines()] if (rep / "hook.log").exists() else []
    t_ctrl = float(hook[0][0]) if hook else None
    rx = [tuple(map(float, l.split(","))) for l in (rep / "rx.csv").read_text().splitlines()[1:] if l.strip()]
    t_end = meta["t0"] + meta["duration_s"]
    pivot = t_ctrl or meta["t_act_launch"]
    before = (pivot - 10.0, pivot)
    after = (pivot + 2.0, t_end - 0.5)
    sel = lambda xs, w: [v for t, v in xs if w[0] <= t < w[1]]  # noqa: E731
    def stats(v):
        if not v:
            return None
        v = sorted(v)
        return {"n": len(v), "median_ms": round(statistics.median(v), 2), "p95_ms": round(v[int(0.95 * (len(v) - 1))], 2),
                "mean_ms": round(statistics.fmean(v), 2)}
    def goodput(w):
        b = sel(rx, w)
        return round(8 * sum(b) / (w[1] - w[0]) / 1e6, 2) if b else None
    return {"hook": [" ".join(h[1:]) for h in hook], "control_applied_after_launch_s": round(t_ctrl - meta["t_act_launch"], 3) if t_ctrl else None,
            "control_at_s": round(t_ctrl - meta["t0"], 2) if t_ctrl else None,
            "rtt_before": stats(sel(rtts, before)), "rtt_after": stats(sel(rtts, after)),
            "goodput_before_mbps": goodput(before), "goodput_after_mbps": goodput(after),
            "rtt_series": [(round(t - meta["t0"], 2), v) for t, v in rtts]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--duration-s", type=float, default=40.0)
    ap.add_argument("--act-s", type=float, default=15.0)
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    reps = []
    for k in range(1, args.repeats + 1):
        meta = one_repeat(out / f"rep{k}", args.duration_s, args.act_s, args.python)
        res = {**meta, **analyse(out / f"rep{k}", meta)}
        (out / f"rep{k}" / "result.json").write_text(json.dumps(res, indent=2))
        reps.append(res)
        print(f"rep{k}: control {res['hook']} at {res['control_at_s']} s; RTT median {res['rtt_before']} -> {res['rtt_after']}; "
              f"goodput {res['goodput_before_mbps']} -> {res['goodput_after_mbps']} Mbit/s", flush=True)
    keys = ("rtt_before", "rtt_after")
    summary = {"setup": {"bottleneck": f"tbf {RATE}, child pfifo limit {FIFO_LIMIT} packets, {FLOWS} bulk TCP flows", "ric": RIC_IP,
                         "xapp": " ".join(XAPP_CMD), "agent": str(AGENT_BIN), "repeats": args.repeats,
                         "duration_s": args.duration_s, "act_s": args.act_s},
               "repeats": [{k: v for k, v in r.items() if k != "rtt_series"} for r in reps]}
    for k in keys:
        med = [r[k]["median_ms"] for r in reps if r.get(k)]
        p95 = [r[k]["p95_ms"] for r in reps if r.get(k)]
        summary[k] = {"median_ms_mean": round(statistics.fmean(med), 2) if med else None, "p95_ms_mean": round(statistics.fmean(p95), 2) if p95 else None}
    for k in ("goodput_before_mbps", "goodput_after_mbps"):
        v = [r[k] for r in reps if r.get(k) is not None]
        summary[k] = round(statistics.fmean(v), 2) if v else None
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    md = ["# D3: AppWeaver TC action on a real bottleneck", "",
          f"Bottleneck {summary['setup']['bottleneck']}; xApp `{summary['setup']['xapp']}` (AppWeaver apply-codel) via a private RIC.", "",
          "| Repeat | Control applied | RTT median before / after (ms) | RTT p95 before / after (ms) | Goodput before / after (Mbit/s) |",
          "|---|---|---|---|---|"]
    for i, r in enumerate(reps, 1):
        b, a = r.get("rtt_before") or {}, r.get("rtt_after") or {}
        md.append(f"| {i} | {'; '.join(r['hook']) or 'none'} at {r['control_at_s']} s | {b.get('median_ms')} / {a.get('median_ms')} | "
                  f"{b.get('p95_ms')} / {a.get('p95_ms')} | {r['goodput_before_mbps']} / {r['goodput_after_mbps']} |")
    (out / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
