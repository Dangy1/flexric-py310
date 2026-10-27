#!/usr/bin/env bash
# Restart the portal stack detached and wait until it is serving.
# Used between evaluation records (run_harness.py --maintenance-cmd): the nearRT-RIC leaks memory
# with every xApp connect/disconnect (18 GB RSS after ~4k xApp runs) and then stops completing
# E42 setup for new xApps, which would show up as unacknowledged tool calls.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LOG="${STACK_RESTART_LOG:-/tmp/flexric_portal_stack_restart.log}"
e42_up() { ss -lnS 2>/dev/null | grep -q "127.0.0.1:36422 "; }
for attempt in 1 2 3; do
  "${SCRIPT_DIR}/stop_agent_portal_stack.sh" >> "${LOG}" 2>&1 || true
  sleep 3
  nohup "${SCRIPT_DIR}/run_agent_portal_stack.sh" >> "${LOG}" 2>&1 < /dev/null &
  for _ in $(seq 120); do
    # The RIC's E42 server (xApp registration, port 36422) can fail to bind after a wedged RIC;
    # the stack then looks healthy but no new xApp can register, so check it explicitly.
    if e42_up \
       && curl -sf -m 2 "http://127.0.0.1:${KPM_BUS_PORT:-8091}/healthz" > /dev/null \
       && curl -sf -m 2 "http://127.0.0.1:${XAPP_RPC_PORT:-8090}/health" > /dev/null \
       && curl -sf -m 2 "http://127.0.0.1:${FLEXRIC_AGENT_PORTAL_PORT:-8088}/api/overview" > /dev/null; then
      echo "$(date -Is) stack restarted (attempt ${attempt})" >> "${LOG}"
      exit 0
    fi
    sleep 1
  done
  echo "$(date -Is) attempt ${attempt}: stack not serving (E42 up: $(e42_up && echo yes || echo no)), retrying" >> "${LOG}"
done
echo "$(date -Is) stack restart failed" >> "${LOG}"
exit 1
