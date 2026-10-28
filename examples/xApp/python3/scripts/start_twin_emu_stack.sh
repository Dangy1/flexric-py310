#!/usr/bin/env bash
# Start the AppWeaver tier-1 twin: a second, independent FlexRIC nearRT-RIC and
# emu_agent_gnb (E2 interface emulator) used to dry-run composed steps before
# they are deployed on the live stack. It never touches the live stack
# (nearRT-RIC on 127.0.0.1:36421/36422, portal, KPM bus).
#
#   scripts/start_twin_emu_stack.sh            # start (idempotent)
#   TWIN_RIC_IP=127.0.0.3 scripts/start_twin_emu_stack.sh
#
# Logs and pids: ${TWIN_LOG_DIR:-/tmp/flexric_twin_emu}
# xApps reach the twin with FLEXRIC_XAPP_CONF=${TWIN_LOG_DIR}/flexric_twin.conf
# (or `xapp_rc_ctrl.py --ric-conf ...`).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
TWIN_LOG_DIR="${TWIN_LOG_DIR:-/tmp/flexric_twin_emu}"
TWIN_RIC_IP="${TWIN_RIC_IP:-127.0.0.2}"
LIBS_DIR="${FLEXRIC_LIBS_DIR:-/usr/local/lib/flexric/}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-20}"

find_build_dir() {
  if [[ -n "${BUILD_DIR:-}" ]]; then readlink -f "${BUILD_DIR}"; return; fi
  local d="${SCRIPT_DIR}"
  while [[ "${d}" != "/" ]]; do
    if [[ -x "${d}/build/examples/ric/nearRT-RIC" ]]; then printf '%s/build\n' "${d}"; return; fi
    if [[ -x "${d}/examples/ric/nearRT-RIC" && -x "${d}/examples/emulator/agent/emu_agent_gnb" ]]; then printf '%s\n' "${d}"; return; fi
    d="$(dirname "${d}")"
  done
  printf '%s/flexric/build\n' "${HOME}"
}
BUILD_DIR="$(find_build_dir)"
RIC_BIN="${BUILD_DIR}/examples/ric/nearRT-RIC"
EMU_BIN="${BUILD_DIR}/examples/emulator/agent/emu_agent_gnb"
for f in "${RIC_BIN}" "${EMU_BIN}"; do
  [[ -x "${f}" ]] || { echo "Missing ${f} (set BUILD_DIR)" >&2; exit 1; }
done

if [[ "${TWIN_RIC_IP}" == "127.0.0.1" ]]; then
  echo "Refusing to start the twin on 127.0.0.1: that is the live nearRT-RIC address." >&2
  exit 1
fi

mkdir -p "${TWIN_LOG_DIR}/db"
CONF="${TWIN_LOG_DIR}/flexric_twin.conf"
cat > "${CONF}" <<CONF_EOF
[NEAR-RIC]
NEAR_RIC_IP = ${TWIN_RIC_IP}

[XAPP]
DB_DIR = ${TWIN_LOG_DIR}/db/
CONF_EOF

listening() {  # listening <ip> <port>
  ss -Hln --sctp 2>/dev/null | awk '{print $4}' | grep -qx "$1:$2"
}

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

if pid_alive "${TWIN_LOG_DIR}/nearRT-RIC.pid" && pid_alive "${TWIN_LOG_DIR}/emu_agent_gnb.pid"; then
  echo "Twin already running (RIC pid $(cat "${TWIN_LOG_DIR}/nearRT-RIC.pid"), emu pid $(cat "${TWIN_LOG_DIR}/emu_agent_gnb.pid")); conf ${CONF}"
  exit 0
fi
# Clean up a half-started twin.
"${SCRIPT_DIR}/stop_twin_emu_stack.sh" >/dev/null 2>&1 || true

if listening "${TWIN_RIC_IP}" 36421 || listening "${TWIN_RIC_IP}" 36422; then
  echo "${TWIN_RIC_IP}:36421/36422 already in use by another process; not starting the twin." >&2
  exit 1
fi

# stdbuf -oL: line-buffered C stdout so the logs are readable while running.
STDBUF=()
command -v stdbuf >/dev/null 2>&1 && STDBUF=(stdbuf -oL -eL)

(cd "${TWIN_LOG_DIR}" && exec setsid "${STDBUF[@]}" "${RIC_BIN}" -c "${CONF}" -p "${LIBS_DIR}") \
  >"${TWIN_LOG_DIR}/nearRT-RIC.log" 2>&1 < /dev/null &
echo $! > "${TWIN_LOG_DIR}/nearRT-RIC.pid"

deadline=$((SECONDS + WAIT_TIMEOUT))
until listening "${TWIN_RIC_IP}" 36421 && listening "${TWIN_RIC_IP}" 36422; do
  if ! pid_alive "${TWIN_LOG_DIR}/nearRT-RIC.pid"; then
    echo "Twin nearRT-RIC exited early; see ${TWIN_LOG_DIR}/nearRT-RIC.log" >&2; exit 1
  fi
  (( SECONDS < deadline )) || { echo "Twin nearRT-RIC did not listen on ${TWIN_RIC_IP}:36421/36422" >&2; exit 1; }
  sleep 0.2
done

(cd "${TWIN_LOG_DIR}" && exec setsid "${STDBUF[@]}" "${EMU_BIN}" -c "${CONF}" -p "${LIBS_DIR}") \
  >"${TWIN_LOG_DIR}/emu_agent_gnb.log" 2>&1 < /dev/null &
echo $! > "${TWIN_LOG_DIR}/emu_agent_gnb.pid"

deadline=$((SECONDS + WAIT_TIMEOUT))
until grep -q "E2 SETUP-RESPONSE rx\|E2 SETUP RESPONSE rx\|SETUP-RESPONSE rx" "${TWIN_LOG_DIR}/emu_agent_gnb.log" 2>/dev/null; do
  if ! pid_alive "${TWIN_LOG_DIR}/emu_agent_gnb.pid"; then
    echo "Twin emu_agent_gnb exited early; see ${TWIN_LOG_DIR}/emu_agent_gnb.log" >&2; exit 1
  fi
  (( SECONDS < deadline )) || { echo "Twin emu_agent_gnb did not complete E2 Setup; see ${TWIN_LOG_DIR}/emu_agent_gnb.log" >&2; exit 1; }
  sleep 0.2
done

cat <<INFO
Twin (tier-1 E2 emulator) running
- nearRT-RIC:     pid $(cat "${TWIN_LOG_DIR}/nearRT-RIC.pid")  E2 ${TWIN_RIC_IP}:36421  E42 ${TWIN_RIC_IP}:36422
- emu_agent_gnb:  pid $(cat "${TWIN_LOG_DIR}/emu_agent_gnb.pid")
- xApp config:    ${CONF}   (export FLEXRIC_XAPP_CONF=${CONF})
- logs:           ${TWIN_LOG_DIR}
INFO
