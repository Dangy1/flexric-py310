#!/usr/bin/env bash
# Stop the AppWeaver tier-1 twin started by start_twin_emu_stack.sh. Only the
# pids recorded under ${TWIN_LOG_DIR} are signalled; the live stack is untouched.
set -uo pipefail
TWIN_LOG_DIR="${TWIN_LOG_DIR:-/tmp/flexric_twin_emu}"

stop_pidfile() {
  local name="$1" pf="${TWIN_LOG_DIR}/$1.pid"
  [[ -f "${pf}" ]] || return 0
  local pid; pid="$(cat "${pf}")"
  if kill -0 "${pid}" 2>/dev/null; then
    kill -INT "${pid}" 2>/dev/null || true
    for _ in $(seq 1 30); do kill -0 "${pid}" 2>/dev/null || break; sleep 0.1; done
    kill -0 "${pid}" 2>/dev/null && kill -KILL "${pid}" 2>/dev/null || true
    echo "stopped twin ${name} (pid ${pid})"
  fi
  rm -f "${pf}"
}

# Agent first, then the RIC.
stop_pidfile emu_agent_gnb
stop_pidfile nearRT-RIC
