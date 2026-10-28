#!/usr/bin/env bash
# Start the ns-O-RAN-flexric simulated RAN for AppWeaver:
#   nearRT-RIC (FlexRIC oie-ric-taap-xapps, E2AP v1.01 / KPM v3.00) on E2 port 36423, E42 port 36424
#   ns-3 mmwave-LENA-oran scenario (1 LTE eNB + N_GNB gNBs + UEs) connecting to that RIC.
#   N_UE is total UEs in scenario-zero*, but UEs PER CELL in Energy_saving_* (3 -> 15 UEs).
#   Flags are the mmWave scenarios' (scenario-zero*, Energy_*); 5G-LENA scenarios take other flags.
# Optionally also starts an xApp: capture = AppWeaver KPM->CSV capture ($LOG_DIR/kpm.csv),
# kpm = shipped xapp_kpm_rc_Enhanced, es = shipped energy-saving xapp_es_with_cell_util.
#
# Usage:  ./start_sim_stack.sh [-g N_GNB] [-u N_UE] [-t SIM_TIME_S] [-s SCENARIO] [-p IND_PERIOD_S]
#                              [-x capture|kpm|es|none] [-P UE_POS_CSV] [-- extra ns-3 flags]
# -P: initial UE positions (scenario-zero* only), CSV ue_index,x,y[,z] (0-based) or imsi,x,y[,z] with header
# Env overrides: PROFILE (optimized|default), E2_HELPER (MmWaveHelper|NrHelper), FLEXRIC_TAAP, NS3_DIR, LOG_DIR, E2_PORT, ISD_CELLS, ISD_UES, CENTER_FREQ, BANDWIDTH
#
# Logs + PID files go to $LOG_DIR (default /tmp/ns_oran_stack/). Stop with ./stop_sim_stack.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLEXRIC_TAAP="${FLEXRIC_TAAP:-$HOME/flexric-taap}"
NS3_DIR="${NS3_DIR:-$HERE/mmwave-LENA-oran}"
LOG_DIR="${LOG_DIR:-/tmp/ns_oran_stack}"
CONF="$FLEXRIC_TAAP/install/etc/flexric/flexric.conf"
LIBS="$FLEXRIC_TAAP/install/lib/flexric/"

N_GNB=4
N_UE=10
SIM_TIME=100
SCENARIO=scenario-zero-with_parallel_loging
IND_PERIOD=0.1
XAPP=none
UE_POS_FILE=""
ISD_CELLS="${ISD_CELLS:-600}"
ISD_UES="${ISD_UES:-500}"
CENTER_FREQ="${CENTER_FREQ:-3.5e9}"
BANDWIDTH="${BANDWIDTH:-20e6}"

while getopts "g:u:t:s:p:x:P:h" opt; do
  case $opt in
    g) N_GNB=$OPTARG ;;
    u) N_UE=$OPTARG ;;
    t) SIM_TIME=$OPTARG ;;
    s) SCENARIO=$OPTARG ;;
    p) IND_PERIOD=$OPTARG ;;
    x) XAPP=$OPTARG ;;
    P) UE_POS_FILE=$(realpath "$OPTARG") || exit 1; [[ -f "$UE_POS_FILE" ]] || { echo "no such file: $OPTARG"; exit 1; } ;;
    h) sed -n 2,16p "$0"; exit 0 ;;
    *) exit 1 ;;
  esac
done
shift $((OPTIND - 1))
EXTRA_NS3_ARGS=("$@")

# E2 port: taken from the RIC's flexric.conf so both sides always agree
E2_PORT="${E2_PORT:-$(awk -F= '/^ *NEAR_RIC_PORT *=/{gsub(/ /,"",$2);print $2}' "$CONF")}"
E2_PORT="${E2_PORT:-36423}"

PROFILE="${PROFILE:-optimized}"   # ns-3 build profile suffix: optimized | default
# Which ns-3 helper owns the E2 attributes: MmWaveHelper (scenario-*, Energy_*) or NrHelper (5G-LENA: RF_*, orange-*)
case "$SCENARIO" in
  RF_*|rf-*|orange-*|opl_nr_*) E2_HELPER="${E2_HELPER:-NrHelper}" ;;
  *) E2_HELPER="${E2_HELPER:-MmWaveHelper}" ;;
esac
NS3_BIN=$(ls "$NS3_DIR"/build/scratch/ns3.*-"$SCENARIO"-"$PROFILE" 2>/dev/null | head -1 || true)
[[ -x "$NS3_BIN" ]] || { echo "ns-3 scenario binary for '$SCENARIO' not found under $NS3_DIR/build/scratch (build ns-3 first)"; exit 1; }
RIC_BIN="$FLEXRIC_TAAP/build/examples/ric/nearRT-RIC"
[[ -x "$RIC_BIN" ]] || { echo "nearRT-RIC not found: $RIC_BIN"; exit 1; }

if [[ -f "$LOG_DIR/ric.pid" ]] && kill -0 "$(cat "$LOG_DIR/ric.pid")" 2>/dev/null; then
  echo "Stack already running (ric.pid=$(cat "$LOG_DIR/ric.pid")); run stop_sim_stack.sh first"; exit 1
fi
if ss -lnS 2>/dev/null | grep -q ":$E2_PORT "; then
  echo "SCTP port $E2_PORT already in use"; exit 1
fi

mkdir -p "$LOG_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
echo "$STAMP" > "$LOG_DIR/run_id"

# 1) nearRT-RIC
stdbuf -oL -eL "$RIC_BIN" -c "$CONF" -p "$LIBS" > "$LOG_DIR/ric.log" 2>&1 &
echo $! > "$LOG_DIR/ric.pid"
for _ in $(seq 50); do
  grep -q "Initializing Task Manager" "$LOG_DIR/ric.log" 2>/dev/null && break
  sleep 0.1
done
echo "nearRT-RIC pid $(cat "$LOG_DIR/ric.pid") on E2 port $E2_PORT (log $LOG_DIR/ric.log)"

# 2) ns-3 scenario. Scenarios write trace files (gnbs.txt, ue_position.txt, energyfilecell*.csv,
#    cu-*/du-* E2 logs) to their CWD, so run them in $LOG_DIR/ns3_out instead of the source tree.
NS3_ARGS=(
  --e2TermIp=127.0.0.1
  --ns3::"$E2_HELPER"::E2Port="$E2_PORT"
  --hoSinrDifference=3
  --indicationPeriodicity="$IND_PERIOD"
  --simTime="$SIM_TIME"
  --KPM_E2functionID=2
  --RC_E2functionID=3
  --N_MmWaveEnbNodes="$N_GNB"
  --N_Ues="$N_UE"
  --CenterFrequency="$CENTER_FREQ"
  --Bandwidth="$BANDWIDTH"
  --IntersideDistanceUEs="$ISD_UES"
  --IntersideDistanceCells="$ISD_CELLS"
)
# absolute path: ns-3 runs in $LOG_DIR/ns3_out
[[ -n "$UE_POS_FILE" ]] && NS3_ARGS+=(--uePositionFile="$UE_POS_FILE")
echo "$NS3_BIN ${NS3_ARGS[*]} ${EXTRA_NS3_ARGS[*]:-}" > "$LOG_DIR/ns3.cmd"
mkdir -p "$LOG_DIR/ns3_out"
(cd "$LOG_DIR/ns3_out" && exec env LD_LIBRARY_PATH="$NS3_DIR/build/lib:${LD_LIBRARY_PATH:-}" \
  "$NS3_BIN" "${NS3_ARGS[@]}" "${EXTRA_NS3_ARGS[@]}") > "$LOG_DIR/ns3.log" 2>&1 &
echo $! > "$LOG_DIR/ns3.pid"
echo "ns-3 $SCENARIO pid $(cat "$LOG_DIR/ns3.pid"): $N_GNB gNB + 1 eNB, $N_UE UEs, simTime ${SIM_TIME}s (log $LOG_DIR/ns3.log)"

# Wait until every E2 node (N_GNB gNBs + 1 LTE eNB) completed E2 Setup with the RIC
want=$((N_GNB + 1))
for _ in $(seq 600); do
  got=$(grep -c "Received SETUP-RESPONSE-SUCCESS" "$LOG_DIR/ns3.log" 2>/dev/null || true)
  [[ "$got" -ge "$want" ]] && break
  kill -0 "$(cat "$LOG_DIR/ns3.pid")" 2>/dev/null || { echo "ns-3 exited early, see $LOG_DIR/ns3.log"; exit 1; }
  sleep 0.5
done   # gives up after 300 s and continues
echo "E2 nodes connected: $(grep -c "Received SETUP-RESPONSE-SUCCESS" "$LOG_DIR/ns3.log" || true)/$want"

# 3) optional xApp (each node serves ONE KPM subscription at a time; further subscribers get no data)
case "$XAPP" in
  none) ;;
  capture) XBIN="$FLEXRIC_TAAP/build/examples/xApp/c/appweaver/xapp_kpm_capture" ;;
  kpm) XBIN="$FLEXRIC_TAAP/build/examples/xApp/c/orange/xapp_kpm_rc_Enhanced" ;;
  es)  XBIN="$FLEXRIC_TAAP/build/examples/xApp/c/orange/xapp_es_with_cell_util" ;;
  *) echo "unknown xApp '$XAPP'"; exit 1 ;;
esac
if [[ "$XAPP" == capture ]]; then
  KPM_CSV="$LOG_DIR/kpm.csv" stdbuf -oL "$XBIN" -c "$CONF" -p "$LIBS" > "$LOG_DIR/xapp_capture.log" 2>&1 &
  echo $! > "$LOG_DIR/xapp.pid"
  echo "xApp capture pid $(cat "$LOG_DIR/xapp.pid") -> $LOG_DIR/kpm.csv"
elif [[ "$XAPP" != none ]]; then
  stdbuf -oL -eL "$XBIN" -c "$CONF" -p "$LIBS" > "$LOG_DIR/xapp_$XAPP.log" 2>&1 &
  echo $! > "$LOG_DIR/xapp.pid"
  echo "xApp $XAPP pid $(cat "$LOG_DIR/xapp.pid") (log $LOG_DIR/xapp_$XAPP.log)"
fi
