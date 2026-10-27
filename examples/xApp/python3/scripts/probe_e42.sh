#!/usr/bin/env bash
# Exit 0 if a new xApp can register with the nearRT-RIC (E42 setup completes and at least one E2 node
# is visible) within PROBE_TIMEOUT_S, non-zero otherwise.
# Used by run_harness.py --health-cmd after every record: the portal nearRT-RIC wedges after a few
# hundred xApp connect/disconnect cycles (E42 setup requests are no longer answered), which would
# otherwise show up as unacknowledged tool calls.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "${SCRIPT_DIR}/.." || exit 3
timeout "${PROBE_TIMEOUT_S:-8}" python -c "
import os, xapp_sdk as ric
ric.init()
os._exit(0 if len(ric.conn_e2_nodes()) else 2)
" > /dev/null 2>&1
