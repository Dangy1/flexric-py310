#!/usr/bin/env bash
# Stop what start_sim_stack.sh started (xApp, ns-3, nearRT-RIC), in that order.
# Only PIDs recorded in $LOG_DIR are signalled; ~/flexric's own RIC is never touched.
LOG_DIR="${LOG_DIR:-/tmp/ns_oran_stack}"

stop_pid() {
  local f="$LOG_DIR/$1.pid"
  [[ -f "$f" ]] || return 0
  local pid; pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then
    kill -INT "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 0.2; done
    kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null
    echo "stopped $1 ($pid)"
  fi
  rm -f "$f"
}

stop_pid xapp
stop_pid ns3
stop_pid ric
