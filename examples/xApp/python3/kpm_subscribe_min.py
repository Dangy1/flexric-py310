#!/usr/bin/env python3
import time
import json
import xapp_sdk as ric

# ---- 1) init + connect
ric.init()
conn = ric.conn_e2_nodes()
assert len(conn) > 0, "No E2 nodes connected"

node_idx = 0
node_id = conn[node_idx].id

print(f"Connected nodes: {len(conn)} | using node_idx={node_idx}")

# ---- 2) KPM callback (base class name can differ across builds)
base_cb = None
for cand in ("kpm_cb", "kpm_cb_t"):
    if hasattr(ric, cand):
        base_cb = getattr(ric, cand)
        break
assert base_cb is not None, "Cannot find KPM callback base class (kpm_cb / kpm_cb_t)"

last = {"count": 0, "data": None}

class KPMCallback(base_cb):
    def __init__(self):
        base_cb.__init__(self)

    def handle(self, ind):
        last["count"] += 1
        # Keep it defensive: don't assume exact fields
        payload = {"tstamp": getattr(ind, "tstamp", None)}
        # Many builds print nicely via str(ind)
        payload["raw"] = str(ind)[:500]
        last["data"] = payload
        print("KPM ind:", json.dumps(payload, ensure_ascii=False))

cb = KPMCallback()

# ---- 3) pick interval enum
interval = getattr(ric, "Interval_ms_10", None) or getattr(ric, "Interval_ms_5", None)
assert interval is not None, "Cannot find Interval_ms_* in SDK"

# ---- 4) subscribe
assert hasattr(ric, "report_kpm_sm"), "SDK missing report_kpm_sm()"
h = ric.report_kpm_sm(node_id, interval, cb)

print("Subscribed. Sleeping 15s...")
time.sleep(15)

# ---- 5) unsubscribe
if hasattr(ric, "rm_report_kpm_sm"):
    ric.rm_report_kpm_sm(h)

print("Done. Received:", last["count"])