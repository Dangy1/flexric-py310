#!/usr/bin/env bash
# Regression test for the RC fixes (APPWEAVER_SETUP.md §11, fix 3): cell ids > 9, CELL_ON.
# 10 gNBs (cells 2..11) + 3 UEs; the patched AppWeaver actuator (tools/actuator, built from
# patches/appweaver-actuator-0001-*) sends, timed on the KPM sim clock (collect_start_us):
#   OFF 11  ->  ON 11 (+1 s)  ->  HO <imsi> 11 (+1.5 s)  ->  OFF 5 (+2 s)
# Expected ns3.log: "Cell turned off 11", "Cell turned on 11 txPower 30", "Initiate handover ... CellId 11",
# "Cell turned off 5"; the handed-over UE then reports from nb_id 11.
# Usage: tools/regress_rc_controls.sh   (logs in $LOG_DIR)
set -u
export LC_ALL=C   # awk/printf decimals with a dot
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLEXRIC_TAAP="${FLEXRIC_TAAP:-$HOME/flexric-taap}"
export LOG_DIR="${LOG_DIR:-/tmp/ns_oran_regress_rc}"
CONF="$FLEXRIC_TAAP/install/etc/flexric/flexric.conf"
LIBS="$FLEXRIC_TAAP/install/lib/flexric/"
ACT="${ACTUATOR:-$HERE/tools/actuator/build/xapp_appweaver_actuator}"
N_GNB="${N_GNB:-10}"; N_UE="${N_UE:-3}"; SIM_TIME="${SIM_TIME:-6}"
TGT=$((N_GNB + 1))

fail=0
check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
sim_now() {  # latest gNB indication stamp, seconds of simulated time
  awk -F, 'NR>1 && $4>=2 && $2>m {m=$2} END {printf "%.3f", m/1e6}' "$LOG_DIR/kpm.csv" 2>/dev/null
}
wait_sim() {  # wait until the KPM sim clock reaches $1 s
  for _ in $(seq 1800); do
    awk -v a="$(sim_now)" -v b="$1" 'BEGIN{exit !(a>=b)}' && return 0
    kill -0 "$NS3_PID" 2>/dev/null || return 1; sleep 1
  done; return 1
}
cmd() { echo "$*" >> "$LOG_DIR/rc_cmd.txt"; echo "sim $(sim_now) s: $*"; }

"$HERE/stop_sim_stack.sh" >/dev/null 2>&1
rm -rf "$LOG_DIR"
"$HERE/start_sim_stack.sh" -g "$N_GNB" -u "$N_UE" -t "$SIM_TIME" -x none || exit 1
NS3_PID=$(cat "$LOG_DIR/ns3.pid")
: > "$LOG_DIR/rc_cmd.txt"
KPM_CSV="$LOG_DIR/kpm.csv" RC_CMD_FILE="$LOG_DIR/rc_cmd.txt" RC_ACK_FILE="$LOG_DIR/rc_ack.txt" \
  stdbuf -oL "$ACT" -c "$CONF" -p "$LIBS" > "$LOG_DIR/xapp_actuator.log" 2>&1 &
echo $! > "$LOG_DIR/xapp.pid"

wait_sim 0.05 || { echo "no gNB indications"; exit 1; }
T0=$(sim_now)
cmd OFF "$TGT"
wait_sim "$(awk -v t="$T0" 'BEGIN{print t+1.0}')"; cmd ON "$TGT"
wait_sim "$(awk -v t="$T0" 'BEGIN{print t+1.5}')"
IMSI=$(awk -F, -v c="$TGT" 'NR>1 && $4>=2 && $4!=c && $6=="DRB.UEThpDl.UEID" {i=$5} END {print i}' "$LOG_DIR/kpm.csv")
cmd HO "$IMSI" "$TGT"
wait_sim "$(awk -v t="$T0" 'BEGIN{print t+2.0}')"; cmd OFF 5
wait_sim "$(awk -v t="$T0" 'BEGIN{print t+3.5}')"

echo "--- wait for ns-3 to reach simTime $SIM_TIME s"
while kill -0 "$NS3_PID" 2>/dev/null; do sleep 5; done
"$HERE/stop_sim_stack.sh" >/dev/null 2>&1

check "all RC commands sent" "[[ \$(grep -c ' sent$' $LOG_DIR/rc_ack.txt) -eq 4 ]]"
check "cell $TGT switched off" "grep -q 'Cell turned off $TGT ' $LOG_DIR/ns3.log"
check "cell $TGT switched on with saved TX power" "grep -q 'Cell turned on $TGT txPower 30' $LOG_DIR/ns3.log"
check "handover of IMSI $IMSI to cell $TGT initiated" "grep -q 'Initiate handover for rnti .* to  CellId $TGT\$' $LOG_DIR/ns3.log"
check "IMSI $IMSI reports from cell $TGT after the handover" \
  "awk -F, -v c=$TGT -v u=$IMSI 'NR>1 && \$4==c && \$5==u && \$6==\"DRB.UEThpDl.UEID\" {f=1} END {exit !f}' $LOG_DIR/kpm.csv"
check "single-digit cell 5 still switched off" "grep -q 'Cell turned off 5 ' $LOG_DIR/ns3.log"
grep -E "Cell turned|Initiate handover" "$LOG_DIR/ns3.log"
[[ $fail -eq 0 ]] && echo "ALL PASS" || echo "SOME CHECKS FAILED"
exit $fail
