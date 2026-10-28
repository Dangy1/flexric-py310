#!/usr/bin/env python3
"""Sample host and per-component resource use while evaluation batches run.

Every --interval-s seconds one CSV row per component: wall time, CPU% (sum over the component's
processes, 100 = one core), RSS MiB, process count, plus host CPU%, used memory and load average.
Components are recognised from the process command line, so the monitor needs no hooks in the
harness and does not change what is measured. Rows are later joined to evaluation records by time
(`summarize_resources.py`) to attribute consumption to batches and methods.

  python resource_monitor.py --out /tmp/appweaver_batches/resources.csv --interval-s 5
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

import psutil

TWIN_CONF = "flexric_twin_emu"


def component(cmd: str) -> str | None:
    if "nearRT-RIC" in cmd:
        if TWIN_CONF in cmd:
            return "twin_ric"
        return "sim_ric" if "flexric-taap" in cmd else "live_ric"
    if "emu_agent_gnb" in cmd:
        return "twin_emulator" if TWIN_CONF in cmd else "live_emulator"
    if "scenario-zero" in cmd or "ns3." in cmd:
        return "ns3"
    if "run_harness.py" in cmd:
        return "harness"  # in-process portal, planner client and LangGraph AppWeaver
    if "run_twin_validation.py" in cmd:
        return "twin_validation"
    if "flexric_agent_portal" in cmd:
        return "portal_server"
    if "kpm_bus" in cmd or "xapp_kpm_capture" in cmd:
        return "kpm_bus"
    if "rapps/runtime.py" in cmd or "rapps.runtime" in cmd:
        return "rapp_runtime"
    for name in ("xapp_tc_suite", "xapp_slice_suite", "xapp_rc_ctrl", "xapp_l2_monitor", "xapp_kpm_rc_suite",
                 "xapp_kpm_bus_reader", "xapp_appweaver_actuator"):
        if name in cmd:
            return "xapp:" + name.replace("xapp_", "")
    if "probe_e42" in cmd or ("python" in cmd and "conn_e2_nodes" in cmd):
        return "health_probe"
    if "mcp_flexric" in cmd or "xapp_rpc_server" in cmd:
        return "mcp_rpc"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval-s", type=float, default=5.0)
    args = parser.parse_args()
    out = Path(args.out)
    new = not out.exists()
    procs: dict[int, psutil.Process] = {}
    with out.open("a", newline="") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(["t", "component", "cpu_pct", "rss_mib", "nproc", "host_cpu_pct", "host_mem_used_mib", "load1"])
        psutil.cpu_percent(None)
        while True:
            seen = set()
            totals: dict[str, list[float]] = {}
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmd = " ".join(proc.info["cmdline"] or [])
                    name = component(cmd)
                    if name is None:
                        continue
                    pid = proc.info["pid"]
                    seen.add(pid)
                    tracked = procs.setdefault(pid, proc)
                    cpu = tracked.cpu_percent(None)  # since the previous sample of this process
                    rss = tracked.memory_info().rss / 2**20
                    agg = totals.setdefault(name, [0.0, 0.0, 0])
                    agg[0] += cpu
                    agg[1] += rss
                    agg[2] += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            for pid in list(procs):
                if pid not in seen:
                    procs.pop(pid, None)
            now = time.time()
            host_cpu = psutil.cpu_percent(None)
            mem = psutil.virtual_memory().used / 2**20
            load1 = os.getloadavg()[0]
            for name, (cpu, rss, n) in sorted(totals.items()):
                writer.writerow([f"{now:.1f}", name, f"{cpu:.1f}", f"{rss:.1f}", n, f"{host_cpu:.1f}", f"{mem:.0f}", f"{load1:.2f}"])
            writer.writerow([f"{now:.1f}", "_host", f"{host_cpu * psutil.cpu_count():.1f}", f"{mem:.0f}", 0, f"{host_cpu:.1f}", f"{mem:.0f}", f"{load1:.2f}"])
            handle.flush()
            time.sleep(args.interval_s)


if __name__ == "__main__":
    raise SystemExit(main())
