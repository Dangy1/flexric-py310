#!/usr/bin/env bash
# Regression test for KPM indications larger than 8 KiB (APPWEAVER_SETUP.md §11, fix 10).
# scenario-zero 4 gNB + LTE eNB, 10 UEs, RngRun=3 (the AppWeaver T6v2/T6v3 seed-3 configuration): one
# cell's DU report of ~10 UEs is ~8.4 KB, which overflowed e2sim's fixed 8192-byte indication buffer
# ("malloc(): invalid size", ns-3 aborted at ~0.3 s sim).
# Expected: ns-3 reaches simTime, no malloc/abort message, the capture xApp receives gNB reports until
# the end. Usage: tools/regress_large_indication.sh  (logs in $LOG_DIR)
set -u
export LC_ALL=C
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export LOG_DIR="${LOG_DIR:-/tmp/ns_oran_regress_large}"
SIM_TIME="${SIM_TIME:-3}"
fail=0
check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

"$HERE/stop_sim_stack.sh" >/dev/null 2>&1
rm -rf "$LOG_DIR"
CENTER_FREQ=3.5e9 BANDWIDTH=20e6 ISD_UES=500 ISD_CELLS=600 \
  "$HERE/start_sim_stack.sh" -g 4 -u 10 -t "$SIM_TIME" -x capture -- --RngRun=3 --hoSinrDifference=3 || exit 1
NS3_PID=$(cat "$LOG_DIR/ns3.pid")
while kill -0 "$NS3_PID" 2>/dev/null; do sleep 2; done
"$HERE/stop_sim_stack.sh" >/dev/null 2>&1

check "no heap corruption abort" "! grep -qi 'malloc()\|free()\|double free\|corrupted\|Aborted' $LOG_DIR/ns3.log"
check "no PDU dropped as too large" "! grep -q 'exceeds MAX_SCTP_BUFFER' $LOG_DIR/ns3.log"
last=$(awk -F, 'NR > 1 && $4 >= 2 && $2 > m {m = $2} END {print m + 0}' "$LOG_DIR/kpm.csv")
check "gNB reports until simTime (last stamp ${last} us)" "[[ $last -ge $(( (SIM_TIME * 10 - 1) * 100000 )) ]]"
# largest per-UE report count of one cell in one period: > ~9 UEs means a message above 8 KiB
max_ues=$(awk -F, 'NR > 1 && $4 >= 2 && $6 == "RRU.PrbUsedDl.UEID" {n[$4 "," $2]++} END {for (k in n) if (n[k] > m) m = n[k]; print m + 0}' "$LOG_DIR/kpm.csv")
echo "  max UEs in one gNB DU report: $max_ues"
check "a cell reported >= 9 UEs in one DU report (message above 8 KiB exercised)" "[[ $max_ues -ge 9 ]]"
[[ $fail -eq 0 ]] && echo "ALL PASS" || echo "SOME CHECKS FAILED"
exit $fail
