#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat >&2 <<'EOF'
run_rl_demo_base.sh is kept only as a compatibility wrapper.
Use run_agent_portal_stack.sh to start services directly from an existing build.
Use build_agent_portal_stack.sh if you want configure/build + start in one command.
EOF

exec "${SCRIPT_DIR}/run_agent_portal_stack.sh" "$@"
