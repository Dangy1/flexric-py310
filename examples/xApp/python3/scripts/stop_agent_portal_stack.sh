#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
WORKSPACE_DIR="${WORKSPACE_DIR:-${PWD}}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-flexric-py310}"
CONDA_SH="${CONDA_SH:-${HOME}/anaconda3/etc/profile.d/conda.sh}"
DEFAULT_ENV_PY="${HOME}/anaconda3/envs/${CONDA_ENV_NAME}/bin/python"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_ENV_PY}}"

PORTAL_HOST="${FLEXRIC_AGENT_PORTAL_HOST:-127.0.0.1}"
PORTAL_PORT="${FLEXRIC_AGENT_PORTAL_PORT:-8088}"
RPC_HOST="${XAPP_RPC_HOST:-127.0.0.1}"
RPC_PORT="${XAPP_RPC_PORT:-8090}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8000}"
KPM_BUS_HOST="${KPM_BUS_HOST:-127.0.0.1}"
KPM_BUS_PORT="${KPM_BUS_PORT:-8091}"

find_repo_root() {
  local start_dir="$1"
  local dir="${start_dir}"
  while [[ "${dir}" != "/" ]]; do
    if [[ -f "${dir}/CMakeLists.txt" && -d "${dir}/examples/xApp/python3" ]]; then
      printf '%s\n' "${dir}"
      return 0
    fi
    dir="$(dirname "${dir}")"
  done
  return 1
}

ROOT_DIR=""
if ROOT_DIR="$(find_repo_root "${WORKSPACE_DIR}")"; then
  :
elif ROOT_DIR="$(find_repo_root "${SCRIPT_DIR}")"; then
  :
else
  echo "Could not locate the FlexRIC workspace root from ${WORKSPACE_DIR} or ${SCRIPT_DIR}." >&2
  exit 1
fi

if [[ -n "${BUILD_DIR:-}" ]]; then
  BUILD_DIR="$(readlink -f "${BUILD_DIR}")"
elif [[ "${SCRIPT_DIR}" == */build/examples/xApp/python3 ]]; then
  BUILD_DIR="$(dirname "$(dirname "$(dirname "${SCRIPT_DIR}")")")"
elif [[ -d "${WORKSPACE_DIR}/build/examples/xApp/python3" ]]; then
  BUILD_DIR="${WORKSPACE_DIR}/build"
else
  BUILD_DIR="${ROOT_DIR}/build"
fi

if [[ "${SCRIPT_DIR}" == "${BUILD_DIR}/examples/xApp/python3" ]]; then
  BUILD_XAPP_DIR="${SCRIPT_DIR}"
else
  BUILD_XAPP_DIR="${BUILD_DIR}/examples/xApp/python3"
fi

if [[ -f "${CONDA_SH}" ]]; then
  # shellcheck disable=SC1090
  source "${CONDA_SH}"
  if conda env list | awk '{print $1}' | grep -qx "${CONDA_ENV_NAME}"; then
    conda activate "${CONDA_ENV_NAME}"
    PYTHON_BIN="${PYTHON_BIN:-${CONDA_PREFIX}/bin/python}"
  fi
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "Python interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
  fi
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

require_cmd ss
require_cmd ps

PIDS=()

append_pid() {
  local pid="$1"
  [[ -n "${pid}" ]] || return 0
  case " ${PIDS[*]} " in
    *" ${pid} "*) ;;
    *) PIDS+=("${pid}") ;;
  esac
}

collect_pids_by_pattern() {
  local pattern="$1"
  while IFS= read -r pid; do
    append_pid "${pid}"
  done < <(ps -eo pid=,args= | awk -v pat="${pattern}" 'index($0, pat) > 0 {print $1}')
}

collect_pids_on_port() {
  local host="$1"
  local port="$2"
  while IFS= read -r pid; do
    append_pid "${pid}"
  done < <(ss -ltnpH "( sport = :${port} )" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
}

collect_pids_by_pattern "${BUILD_DIR}/examples/ric/nearRT-RIC"
collect_pids_by_pattern "${BUILD_DIR}/examples/emulator/agent/emu_agent_gnb"
collect_pids_by_pattern "${BUILD_XAPP_DIR}/flexric_agent_portal.py"
collect_pids_by_pattern "${BUILD_XAPP_DIR}/mcp_flexric_metrics_http.py"
collect_pids_by_pattern "${BUILD_XAPP_DIR}/kpm_bus_service.py"
collect_pids_by_pattern "uvicorn xapp_rpc_server:app --host ${RPC_HOST} --port ${RPC_PORT} --app-dir ${BUILD_XAPP_DIR}"

collect_pids_on_port "${PORTAL_HOST}" "${PORTAL_PORT}"
collect_pids_on_port "${RPC_HOST}" "${RPC_PORT}"
collect_pids_on_port "${MCP_HOST}" "${MCP_PORT}"
collect_pids_on_port "${KPM_BUS_HOST}" "${KPM_BUS_PORT}"
collect_pids_on_port "127.0.0.1" "36421"
collect_pids_on_port "127.0.0.1" "36422"

if [[ "${#PIDS[@]}" -eq 0 ]]; then
  echo "No matching FlexRIC agent portal stack processes found."
  exit 0
fi

printf 'Stopping FlexRIC agent portal stack PIDs: %s\n' "${PIDS[*]}"
kill "${PIDS[@]}" 2>/dev/null || true

deadline=$((SECONDS + 10))
while (( SECONDS < deadline )); do
  still_running=0
  for pid in "${PIDS[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      still_running=1
      break
    fi
  done
  if [[ "${still_running}" -eq 0 ]]; then
    echo "FlexRIC agent portal stack stopped."
    exit 0
  fi
  sleep 1
done

echo "Some processes are still running after 10s; sending SIGKILL." >&2
kill -9 "${PIDS[@]}" 2>/dev/null || true
echo "FlexRIC agent portal stack stop requested."
