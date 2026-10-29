#!/usr/bin/env bash
# Exit 0 if a new xApp can register with the nearRT-RIC (E42 setup completes and at least one E2 node
# is visible) within PROBE_TIMEOUT_S, non-zero otherwise.
# Used by run_harness.py --health-cmd after every record. The limit is 2.5 s (2026-10-29, during Batch B k=8):
# a healthy RIC registers an xApp in ~1 s; a degrading one answers E42 SETUP only after 1-3 'Resending Setup
# Request' retries (2-4 s), late enough that TC/RC control ACKs miss the harness's 12 s window. Before: 8 s.
# One retry after 1 s, because a single slow answer right after a busy record is not degradation.
# the portal nearRT-RIC wedges after a few
# hundred xApp connect/disconnect cycles (E42 setup requests are no longer answered), which would
# otherwise show up as unacknowledged tool calls.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "${SCRIPT_DIR}/.." || exit 3
probe() {
  timeout "${PROBE_TIMEOUT_S:-2.5}" python -c "
import os, xapp_sdk as ric
ric.init()
os._exit(0 if len(ric.conn_e2_nodes()) else 2)
" > /dev/null 2>&1
}
# Two tries: right after a busy record the RIC can be briefly slow; a degrading RIC is slow on both.
probe || { sleep 1; probe; } || exit 1

# A degrading RIC still registers one probe xApp quickly but answers the record's own xApps (several at once)
# only after repeated E42 setup resends, so their control ACKs arrive too late. Healthy periods show no
# resend at all (Batch B, 22:00-00:30: 0 of 1,065 xApp logs); fail when any xApp log not judged before
# (from the last 30 min) shows >= 2 resends. Each log is judged once.
RUN_LOGS="${FLEXRIC_RUN_LOG_DIR:-/tmp/flexric_agent_portal}"
SEEN="${RUN_LOGS}/.probe_seen"   # logs already judged; long-running xApps keep writing after the check
touch "$SEEN"
bad=0
while IFS= read -r f; do
  grep -qxF "$f" "$SEEN" && continue
  echo "$f" >> "$SEEN"
  n=$(grep -c "Resending Setup Request" "$f" 2>/dev/null || true)
  [ "${n:-0}" -ge 2 ] && bad=1
done < <(find "$RUN_LOGS" -maxdepth 1 -name '*.log' -mmin -30 2>/dev/null)
exit $bad
