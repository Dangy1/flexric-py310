#!/usr/bin/env bash
# Regression test for the KPM subscription fixes (APPWEAVER_SETUP.md §11, fixes 1, 2, 4, 5, 6):
#   A = capture xApp started with the stack; B = second capture xApp while A runs (-t 15);
#   then A is stopped with SIGINT (sends its deletes) and C is started (re-arm).
# Expected: B gets no gNB rows and its deletes do not stop A; ns-3 survives A's deletes;
# C receives indications again; ns-3 reaches simTime. 2 gNB / 4 UE also exercises the
# empty-neighbour-list case (noValue records).
# Usage: tools/regress_kpm_subscriptions.sh   (about 6 wall-minutes; logs in $LOG_DIR)
set -u
export LC_ALL=C   # awk/printf decimals with a dot
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLEXRIC_TAAP="${FLEXRIC_TAAP:-$HOME/flexric-taap}"
export LOG_DIR="${LOG_DIR:-/tmp/ns_oran_regress_subs}"
CONF="$FLEXRIC_TAAP/install/etc/flexric/flexric.conf"
LIBS="$FLEXRIC_TAAP/install/lib/flexric/"
CAP="$FLEXRIC_TAAP/build/examples/xApp/c/appweaver/xapp_kpm_capture"
SIM_TIME="${SIM_TIME:-60}"

gnb_rows() { awk -F, 'NR > 1 && $4 >= 2' "$1" 2>/dev/null | wc -l; }
wait_gnb_rows() {  # file min_rows timeout_s
  for _ in $(seq "$3"); do [[ $(gnb_rows "$1") -ge $2 ]] && return 0; sleep 1; done; return 1
}
fail=0
check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

"$HERE/stop_sim_stack.sh" >/dev/null 2>&1
rm -rf "$LOG_DIR"
"$HERE/start_sim_stack.sh" -g 2 -u 4 -t "$SIM_TIME" -x capture || exit 1
NS3_PID=$(cat "$LOG_DIR/ns3.pid")
A_PID=$(cat "$LOG_DIR/xapp.pid")

wait_gnb_rows "$LOG_DIR/kpm.csv" 200 300 || echo "xApp A got no gNB rows"
echo "--- start xApp B (15 s) while A is subscribed"
KPM_CSV="$LOG_DIR/kpm_B.csv" stdbuf -oL "$CAP" -c "$CONF" -p "$LIBS" -t 15 > "$LOG_DIR/xapp_B.log" 2>&1
B_RC=$?
a_before=$(gnb_rows "$LOG_DIR/kpm.csv"); sleep 20; a_after=$(gnb_rows "$LOG_DIR/kpm.csv")
check "xApp B exited cleanly (rc=$B_RC)" "[[ $B_RC -eq 0 ]]"
check "xApp B got no gNB rows (one served subscription per node)" "[[ \$(gnb_rows $LOG_DIR/kpm_B.csv) -eq 0 ]]"
check "xApp A still alive after B's deletes" "kill -0 $A_PID 2>/dev/null"
check "xApp A keeps receiving after B's deletes ($a_before -> $a_after rows)" "[[ $a_after -gt $a_before ]]"
check "ns-3 ignored B's deletes" "grep -q 'is not the served subscription' $LOG_DIR/ns3.log"

echo "--- stop xApp A (SIGINT -> subscription deletes)"
kill -INT "$A_PID"; for _ in $(seq 30); do kill -0 "$A_PID" 2>/dev/null || break; sleep 0.5; done
rm -f "$LOG_DIR/xapp.pid"
sleep 15
check "ns-3 alive after A's deletes" "kill -0 $NS3_PID 2>/dev/null"
check "ns-3 stopped reporting for A" "grep -q 'deleted, reporting stopped' $LOG_DIR/ns3.log"
check "no 'Bad file descriptor' in ns3.log" "! grep -q 'Bad file descriptor' $LOG_DIR/ns3.log"

echo "--- start xApp C (re-arm after delete)"
KPM_CSV="$LOG_DIR/kpm_C.csv" stdbuf -oL "$CAP" -c "$CONF" -p "$LIBS" > "$LOG_DIR/xapp_C.log" 2>&1 &
C_PID=$!; echo $C_PID > "$LOG_DIR/xapp.pid"
check "xApp C receives gNB indications" "wait_gnb_rows $LOG_DIR/kpm_C.csv 200 300"

echo "--- wait for ns-3 to reach simTime $SIM_TIME s"
while kill -0 "$NS3_PID" 2>/dev/null; do sleep 5; done
check "ns-3 ran to the end" "! grep -qi 'sctp_send_data, error\|terminate called\|Segmentation' $LOG_DIR/ns3.log"
kill -INT "$C_PID" 2>/dev/null; sleep 2
"$HERE/stop_sim_stack.sh" >/dev/null 2>&1

echo "--- indication clock and records (xApp A)"
python3 - "$LOG_DIR/kpm.csv" "$LOG_DIR/kpm_C.csv" <<'EOF'
import csv, sys
from collections import defaultdict
for path in sys.argv[1:]:
    stamps = defaultdict(set); novalue = 0; neigh = 0
    for r in csv.DictReader(open(path)):
        if not r["wall_us"].isdigit(): continue
        stamps[int(r["nb_id"])].add(int(r["collect_start_us"]))
        if r["meas"].startswith("L3neighSINRListOf"):
            neigh += 1; novalue += r["value"] == ""
    print(path)
    for nb, s in sorted(stamps.items()):
        s = sorted(s); steps = sorted({b - a for a, b in zip(s, s[1:])})
        print(f"  nb {nb}: {len(s)} stamps, first {s[0]/1e6:.3f} s, last {s[-1]/1e6:.3f} s (sim), steps(us) {steps[:5]}")
    print(f"  L3neighSINRListOf rows {neigh}, noValue {novalue}")
EOF
[[ $fail -eq 0 ]] && echo "ALL PASS" || echo "SOME CHECKS FAILED"
exit $fail
