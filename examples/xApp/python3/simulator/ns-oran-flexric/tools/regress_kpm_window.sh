#!/usr/bin/env bash
# Regression test for the E2 report window (APPWEAVER_SETUP.md §11, fix 8) and the trace start time
# (fix 9). Two runs with the same seed (2 gNB + LTE eNB, 4 UEs, no RC); the capture xApp subscribes
# early in run "early" and ~SUB_DELAY wall-seconds later in run "late".
# Expected: every E2 gNB stamp is on the 100 ms grid; the DU values (RRU.PrbUsedDl.UEID,
# DRB.UEThpDl.UEID, TB.TotNbrDl.1.UEID) agree between the two runs at every common stamp; PRB and
# TB counts equal the du-cell-<id>.txt trace row of the same tick; du-cell timestamps are run id (simid of
# ue_position.txt) + simulated ms. Usage: tools/regress_kpm_window.sh  (logs in $LOG_DIR)
set -u
export LC_ALL=C
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLEXRIC_TAAP="${FLEXRIC_TAAP:-$HOME/flexric-taap}"
export LOG_DIR="${LOG_DIR:-/tmp/ns_oran_regress_window}"
CONF="$FLEXRIC_TAAP/install/etc/flexric/flexric.conf"
LIBS="$FLEXRIC_TAAP/install/lib/flexric/"
CAP="$FLEXRIC_TAAP/build/examples/xApp/c/appweaver/xapp_kpm_capture"
SIM_TIME="${SIM_TIME:-20}"; SUB_DELAY="${SUB_DELAY:-30}"
fail=0
check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

run() {  # name xapp_mode delay_s
  local name=$1 mode=$2 delay=$3 d="$LOG_DIR/$1"
  "$HERE/stop_sim_stack.sh" >/dev/null 2>&1
  rm -rf "$d"; mkdir -p "$LOG_DIR"
  LOG_DIR="$d" "$HERE/start_sim_stack.sh" -g 2 -u 4 -t "$SIM_TIME" -x "$mode" >/dev/null || return 1
  local pid; pid=$(cat "$d/ns3.pid")
  if [[ $mode == none ]]; then
    sleep "$delay"
    KPM_CSV="$d/kpm.csv" stdbuf -oL "$CAP" -c "$CONF" -p "$LIBS" > "$d/xapp_capture.log" 2>&1 &
    echo $! > "$d/xapp.pid"
  fi
  while kill -0 "$pid" 2>/dev/null; do sleep 2; done
  LOG_DIR="$d" "$HERE/stop_sim_stack.sh" >/dev/null 2>&1
  return 0
}

if [[ -z "${ANALYZE_ONLY:-}" ]]; then   # ANALYZE_ONLY=1: re-check the runs already in $LOG_DIR
  run early capture 0 || echo "run early did not start"
  run late none "$SUB_DELAY" || echo "run late did not start"
fi
check "ns-3 did not crash in either run" "! grep -qi 'terminate called\|Segmentation\|malloc' $LOG_DIR/early/ns3.log $LOG_DIR/late/ns3.log"

python3 - "$LOG_DIR/early" "$LOG_DIR/late" <<'EOF'
import csv, glob, os, sys
MEAS = {"RRU.PrbUsedDl.UEID": "RRU.PrbUsedDl.UEID", "DRB.UEThpDl.UEID": "DRB.UEThpDl.UEID",
        "TB.TotNbrDl.1.UEID": "TB.TotNbrDl.1.UEID"}
def e2(d):
    out = {}
    for r in csv.DictReader(open(os.path.join(d, "kpm.csv"))):
        if not r["wall_us"].isdigit() or int(r["nb_id"]) < 2 or r["meas"] not in MEAS: continue
        out[(int(r["nb_id"]), int(r["collect_start_us"]), int(r["ue_imsi"]), r["meas"])] = float(r["value"])
    return out
def trace(d):
    simid = int(next(csv.DictReader(open(os.path.join(d, "ns3_out", "ue_position.txt"))))["simid"])
    out, offgrid = {}, 0
    for f in glob.glob(os.path.join(d, "ns3_out", "du-cell-*.txt")):
        rows = csv.reader(open(f, encoding="latin-1")); hdr = [h.strip() for h in next(rows)]
        ue_cols = hdr[9 + 23:]  # header_csv (9) + cell_header (23), then the UE columns
        for r in rows:
            if len(r) < len(hdr): continue
            ms = int(r[0]) - simid
            offgrid += not (0 <= ms <= 100000 and ms % 100 == 0)
            for m in MEAS:
                out[(int(r[3]), ms * 1000, int(r[1]), m)] = float(r[9 + 23 + ue_cols.index(m)])
    return out, offgrid
res = {}
a, b = e2(sys.argv[1]), e2(sys.argv[2])
stamps = {k[1] for k in a} | {k[1] for k in b}
res["E2 stamps on the 100 ms grid"] = bool(stamps) and all(s % 100000 == 0 for s in stamps)
common = sorted(set(a) & set(b))
diff = [k for k in common if abs(a[k] - b[k]) > 1e-6]
print(f"  early: {len(a)} DU values from {min(k[1] for k in a)/1e6:.1f} s; late: {len(b)} from {min(k[1] for k in b)/1e6:.1f} s; common {len(common)}, differing {len(diff)}")
for k in diff[:5]: print("   ", k, a[k], b[k])
nonzero = sum(1 for k in common if k[3] == "RRU.PrbUsedDl.UEID" and a[k] > 0)
print(f"  common RRU.PrbUsedDl.UEID values > 0: {nonzero}")
res["DU values equal between early and late subscription"] = len(common) > 50 and not diff and nonzero > 0
for name, d, e in (("early", sys.argv[1], a), ("late", sys.argv[2], b)):
    t, offgrid = trace(d)
    # E2 carries integers (the trace prints PRB with decimals); DRB.UEThpDl.UEID is not compared:
    # the trace's DU row takes it from the previous tick's CU-UP logger
    both = [k for k in e if k in t and k[3] != "DRB.UEThpDl.UEID"]
    bad = [k for k in both if abs(e[k] - int(t[k])) > 0.5]
    print(f"  {name}: {len(both)} E2 values matched to du-cell rows, {len(bad)} differ, {offgrid} trace rows off the simid+ms grid")
    for k in bad[:5]: print("   ", k, e[k], t[k])
    res[f"{name}: E2 DU values equal the du-cell trace"] = len(both) > 50 and not bad
    res[f"{name}: du-cell timestamps are simid + sim ms"] = offgrid == 0
for k, v in res.items(): print(("PASS " if v else "FAIL ") + k)
sys.exit(0 if all(res.values()) else 1)
EOF
[[ $? -ne 0 ]] && fail=1
grep -h "not served\|not the served" "$LOG_DIR"/*/ns3.log | head -3
[[ $fail -eq 0 ]] && echo "ALL PASS" || echo "SOME CHECKS FAILED"
exit $fail
