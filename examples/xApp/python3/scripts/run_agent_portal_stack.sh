#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
WORKSPACE_DIR="${WORKSPACE_DIR:-${PWD}}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-flexric-py310}"
CONDA_SH="${CONDA_SH:-${HOME}/anaconda3/etc/profile.d/conda.sh}"
DEFAULT_ENV_PY="${HOME}/anaconda3/envs/${CONDA_ENV_NAME}/bin/python"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_ENV_PY}}"
LOG_DIR="${LOG_DIR:-/tmp/flexric_portal_stack}"

PORTAL_HOST="${FLEXRIC_AGENT_PORTAL_HOST:-0.0.0.0}"
PORTAL_PORT="${FLEXRIC_AGENT_PORTAL_PORT:-8088}"
RPC_HOST="${XAPP_RPC_HOST:-0.0.0.0}"
RPC_PORT="${XAPP_RPC_PORT:-8090}"
MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8000}"
MCP_PATH="${MCP_PATH:-/mcp}"
KPM_BUS_HOST="${KPM_BUS_HOST:-0.0.0.0}"
KPM_BUS_PORT="${KPM_BUS_PORT:-8091}"
START_KPM_BUS="${START_KPM_BUS:-1}"
START_RPC_SERVER="${START_RPC_SERVER:-1}"
START_MCP_SERVER="${START_MCP_SERVER:-1}"
START_PORTAL="${START_PORTAL:-1}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-60}"
MCP_OPTIONAL="${MCP_OPTIONAL:-1}"

mkdir -p "${LOG_DIR}"

normalize_check_host() {
  local host="$1"
  case "${host}" in
    ""|"0.0.0.0"|"::")
      printf '127.0.0.1\n'
      ;;
    *)
      printf '%s\n' "${host}"
      ;;
  esac
}

detect_lan_host() {
  local candidate
  for candidate in $(hostname -I 2>/dev/null); do
    case "${candidate}" in
      127.*|"")
        ;;
      *)
        printf '%s\n' "${candidate}"
        return 0
        ;;
    esac
  done
  printf '127.0.0.1\n'
}

normalize_public_host() {
  local bind_host="$1"
  local explicit_public="$2"
  if [[ -n "${explicit_public}" ]]; then
    printf '%s\n' "${explicit_public}"
    return 0
  fi
  case "${bind_host}" in
    ""|"0.0.0.0"|"::")
      detect_lan_host
      ;;
    *)
      printf '%s\n' "${bind_host}"
      ;;
  esac
}

PORTAL_CHECK_HOST="$(normalize_check_host "${PORTAL_HOST}")"
RPC_CHECK_HOST="$(normalize_check_host "${RPC_HOST}")"
MCP_CHECK_HOST="$(normalize_check_host "${MCP_HOST}")"
KPM_BUS_CHECK_HOST="$(normalize_check_host "${KPM_BUS_HOST}")"

PORTAL_PUBLIC_HOST="$(normalize_public_host "${PORTAL_HOST}" "${FLEXRIC_AGENT_PORTAL_PUBLIC_HOST:-}")"
RPC_PUBLIC_HOST="$(normalize_public_host "${RPC_HOST}" "${XAPP_RPC_PUBLIC_HOST:-${FLEXRIC_AGENT_PORTAL_PUBLIC_HOST:-}}")"
MCP_PUBLIC_HOST="$(normalize_public_host "${MCP_HOST}" "${MCP_PUBLIC_HOST:-${FLEXRIC_AGENT_PORTAL_PUBLIC_HOST:-}}")"
KPM_BUS_PUBLIC_HOST="$(normalize_public_host "${KPM_BUS_HOST}" "${KPM_BUS_PUBLIC_HOST:-${FLEXRIC_AGENT_PORTAL_PUBLIC_HOST:-}}")"
AUTO_STOP_BEFORE_START="${AUTO_STOP_BEFORE_START:-1}"

if [[ "${AUTO_STOP_BEFORE_START}" == "1" ]]; then
  STOP_SCRIPT="${SCRIPT_DIR}/stop_agent_portal_stack.sh"
  if [[ -x "${STOP_SCRIPT}" ]]; then
    echo "Ensuring the previous FlexRIC portal stack is stopped before startup..."
    "${STOP_SCRIPT}" || true
    sleep 1
  fi
fi

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
if [[ -n "${ROOT_DIR:-}" ]]; then
  :
elif ROOT_DIR="$(find_repo_root "${WORKSPACE_DIR}")"; then
  :
elif ROOT_DIR="$(find_repo_root "${SCRIPT_DIR}")"; then
  :
elif [[ "${SCRIPT_DIR}" == */build/examples/xApp/python3 ]]; then
  ROOT_DIR="$(find_repo_root "$(dirname "$(dirname "$(dirname "${SCRIPT_DIR}")")")")" || true
fi

if [[ -z "${ROOT_DIR}" ]]; then
  echo "Could not locate the FlexRIC workspace root from ${WORKSPACE_DIR} or ${SCRIPT_DIR}." >&2
  echo "Set WORKSPACE_DIR=/path/to/flexric or BUILD_DIR=/path/to/flexric/build and try again." >&2
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

require_cmd curl
require_cmd ss

if [[ ! -f /usr/local/lib/flexric/libkpm_sm.so ]]; then
  echo "Missing installed FlexRIC service-model libraries under /usr/local/lib/flexric." >&2
  echo "Run: sudo cmake --build \"${BUILD_DIR}\" --target install" >&2
  exit 1
fi

if [[ ! -d "${BUILD_XAPP_DIR}" ]]; then
  echo "Build xApp directory not found: ${BUILD_XAPP_DIR}" >&2
  exit 1
fi

require_file() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "Missing build artifact: ${path}" >&2
    echo "Run ./build_agent_portal_stack.sh first, or build manually with cmake." >&2
    exit 1
  fi
}

require_file "${BUILD_DIR}/examples/ric/nearRT-RIC"
require_file "${BUILD_DIR}/examples/emulator/agent/emu_agent_gnb"
require_file "${BUILD_XAPP_DIR}/_xapp_sdk.so"
require_file "${BUILD_XAPP_DIR}/xapp_sdk.py"
require_file "${BUILD_XAPP_DIR}/flexric_agent_portal.py"
require_file "${BUILD_XAPP_DIR}/xapp_rpc_server.py"
require_file "${BUILD_XAPP_DIR}/mcp_flexric_metrics_http.py"
require_file "${BUILD_XAPP_DIR}/kpm_bus_service.py"
require_file "${BUILD_XAPP_DIR}/xapp_kpm_bus_reader.py"

export LD_LIBRARY_PATH="${HOME}/anaconda3/lib:${BUILD_DIR}/src/xApp:${BUILD_XAPP_DIR}:/usr/local/lib:/usr/local/lib/flexric:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${BUILD_XAPP_DIR}:${PYTHONPATH:-}"
export FLEXRIC_AGENT_PORTAL_HOST="${PORTAL_HOST}"
export FLEXRIC_AGENT_PORTAL_PORT="${PORTAL_PORT}"
export FLEXRIC_AGENT_PORTAL_PUBLIC_HOST="${PORTAL_PUBLIC_HOST}"
export XAPP_RPC_HOST="${RPC_HOST}"
export XAPP_RPC_PORT="${RPC_PORT}"
export XAPP_RPC_PUBLIC_HOST="${RPC_PUBLIC_HOST}"
export MCP_HOST="${MCP_HOST}"
export MCP_PORT="${MCP_PORT}"
export MCP_PUBLIC_HOST="${MCP_PUBLIC_HOST}"
export MCP_PATH
export KPM_BUS_HOST="${KPM_BUS_HOST}"
export KPM_BUS_PORT="${KPM_BUS_PORT}"
export KPM_BUS_PUBLIC_HOST="${KPM_BUS_PUBLIC_HOST}"
export KPM_BUS_URL="http://${KPM_BUS_CHECK_HOST}:${KPM_BUS_PORT}"

declare -a PIDS=()

cleanup() {
  set +e
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid}" ]]; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

start_bg() {
  local name="$1"
  local logfile="$2"
  shift 2
  (
    cd "${BUILD_XAPP_DIR}"
    exec "$@"
  ) >"${logfile}" 2>&1 &
  local pid=$!
  PIDS+=("${pid}")
  echo "${pid}"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local pid="$3"
  local deadline=$((SECONDS + WAIT_TIMEOUT))

  while (( SECONDS < deadline )); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      echo "${name} exited early. Check logs under ${LOG_DIR}." >&2
      return 1
    fi
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for ${name} at ${url}" >&2
  return 1
}

wait_for_port() {
  local name="$1"
  local host="$2"
  local port="$3"
  local pid="$4"
  local deadline=$((SECONDS + WAIT_TIMEOUT))

  while (( SECONDS < deadline )); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      echo "${name} exited early. Check logs under ${LOG_DIR}." >&2
      return 1
    fi
    if "${PYTHON_BIN}" - <<PY >/dev/null 2>&1
import socket
s = socket.socket()
s.settimeout(1.0)
try:
    s.connect(("${host}", ${port}))
finally:
    s.close()
PY
    then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for ${name} on ${host}:${port}" >&2
  return 1
}

port_is_busy() {
  local host="$1"
  local port="$2"
  "${PYTHON_BIN}" - <<PY >/dev/null 2>&1
import socket
s = socket.socket()
s.settimeout(0.5)
try:
    rc = s.connect_ex(("${host}", ${port}))
finally:
    s.close()
raise SystemExit(0 if rc == 0 else 1)
PY
}

check_port_free() {
  local host="$1"
  local port="$2"
  local name="$3"
  if port_is_busy "${host}" "${port}"; then
    echo "Port ${host}:${port} for ${name} is already in use." >&2
    ss -ltnp | grep -E "[[:space:]]${host}:${port}[[:space:]]" >&2 || true
    echo "Stop the old process first, or change the port env vars before starting the stack." >&2
    return 1
  fi
  return 0
}

NEARRIC_LOG="${LOG_DIR}/nearRT-RIC.log"
EMU_LOG="${LOG_DIR}/emu_agent_gnb.log"
PORTAL_LOG="${LOG_DIR}/agent_portal.log"
RPC_LOG="${LOG_DIR}/xapp_rpc_server.log"
MCP_LOG="${LOG_DIR}/mcp_flexric_metrics_http.log"
KPM_BUS_LOG="${LOG_DIR}/kpm_bus_service.log"

check_port_free "127.0.0.1" "36421" "nearRT-RIC E2 endpoint"
check_port_free "127.0.0.1" "36422" "nearRT-RIC E42 endpoint"
if [[ "${START_PORTAL}" == "1" ]]; then
  check_port_free "${PORTAL_CHECK_HOST}" "${PORTAL_PORT}" "agent portal"
fi
if [[ "${START_RPC_SERVER}" == "1" ]]; then
  check_port_free "${RPC_CHECK_HOST}" "${RPC_PORT}" "xApp RPC server"
fi
if [[ "${START_MCP_SERVER}" == "1" ]]; then
  check_port_free "${MCP_CHECK_HOST}" "${MCP_PORT}" "MCP metrics server"
fi
if [[ "${START_KPM_BUS}" == "1" ]]; then
  check_port_free "${KPM_BUS_CHECK_HOST}" "${KPM_BUS_PORT}" "KPM bus server"
fi

RIC_PID="$(start_bg nearRT-RIC "${NEARRIC_LOG}" "${BUILD_DIR}/examples/ric/nearRT-RIC")"
sleep 2
if ! kill -0 "${RIC_PID}" 2>/dev/null; then
  echo "nearRT-RIC failed to start. Check ${NEARRIC_LOG}" >&2
  exit 1
fi

AGENT_PID="$(start_bg emu_agent_gnb "${EMU_LOG}" "${BUILD_DIR}/examples/emulator/agent/emu_agent_gnb")"
sleep 2
if ! kill -0 "${AGENT_PID}" 2>/dev/null; then
  echo "emu_agent_gnb failed to start. Check ${EMU_LOG}" >&2
  exit 1
fi

PORTAL_PID=""
RPC_PID=""
MCP_PID=""
KPM_BUS_PID=""

if [[ "${START_PORTAL}" == "1" ]]; then
  PORTAL_PID="$(start_bg flexric_agent_portal "${PORTAL_LOG}" "${PYTHON_BIN}" "${BUILD_XAPP_DIR}/flexric_agent_portal.py")"
  wait_for_http "FlexRIC Agent Portal" "http://${PORTAL_CHECK_HOST}:${PORTAL_PORT}/" "${PORTAL_PID}" || exit 1
fi

if [[ "${START_RPC_SERVER}" == "1" ]]; then
  RPC_PID="$(start_bg xapp_rpc_server "${RPC_LOG}" "${PYTHON_BIN}" -m uvicorn xapp_rpc_server:app --host "${RPC_HOST}" --port "${RPC_PORT}" --app-dir "${BUILD_XAPP_DIR}")"
  wait_for_http "xApp RPC server" "http://${RPC_CHECK_HOST}:${RPC_PORT}/health" "${RPC_PID}" || exit 1
fi

if [[ "${START_MCP_SERVER}" == "1" ]]; then
  MCP_PID="$(start_bg mcp_flexric_metrics_http "${MCP_LOG}" "${PYTHON_BIN}" "${BUILD_XAPP_DIR}/mcp_flexric_metrics_http.py")"
  wait_for_http "MCP metrics server" "http://${MCP_CHECK_HOST}:${MCP_PORT}/healthz" "${MCP_PID}" || exit 1
fi

if [[ "${START_KPM_BUS}" == "1" ]]; then
  KPM_BUS_PID="$(start_bg kpm_bus_service "${KPM_BUS_LOG}" "${PYTHON_BIN}" "${BUILD_XAPP_DIR}/kpm_bus_service.py")"
  wait_for_http "KPM bus server" "http://${KPM_BUS_CHECK_HOST}:${KPM_BUS_PORT}/healthz" "${KPM_BUS_PID}" || exit 1
fi

cat <<EOF
FlexRIC stack is up.

Build dir: ${BUILD_DIR}
Python: ${PYTHON_BIN}
Logs: ${LOG_DIR}

Services:
- nearRT-RIC:     running (pid ${RIC_PID})
- emu_agent_gnb:  running (pid ${AGENT_PID})
EOF

if [[ -n "${PORTAL_PID}" ]]; then
  cat <<EOF
- agent portal:   http://127.0.0.1:${PORTAL_PORT}/
EOF
  if [[ "${PORTAL_PUBLIC_HOST}" != "127.0.0.1" ]]; then
    cat <<EOF
- agent portal LAN: http://${PORTAL_PUBLIC_HOST}:${PORTAL_PORT}/
EOF
  fi
fi

if [[ -n "${RPC_PID}" ]]; then
  cat <<EOF
- xApp RPC:       http://127.0.0.1:${RPC_PORT}/health
EOF
  if [[ "${RPC_PUBLIC_HOST}" != "127.0.0.1" ]]; then
    cat <<EOF
- xApp RPC LAN:   http://${RPC_PUBLIC_HOST}:${RPC_PORT}/health
EOF
  fi
fi

if [[ -n "${MCP_PID}" ]]; then
  cat <<EOF
- MCP metrics:    http://127.0.0.1:${MCP_PORT}/healthz
EOF
  if [[ "${MCP_PUBLIC_HOST}" != "127.0.0.1" ]]; then
    cat <<EOF
- MCP metrics LAN: http://${MCP_PUBLIC_HOST}:${MCP_PORT}/healthz
EOF
  fi
fi

if [[ -n "${KPM_BUS_PID}" ]]; then
  cat <<EOF
- KPM bus:        http://127.0.0.1:${KPM_BUS_PORT}/healthz
EOF
  if [[ "${KPM_BUS_PUBLIC_HOST}" != "127.0.0.1" ]]; then
    cat <<EOF
- KPM bus LAN:    http://${KPM_BUS_PUBLIC_HOST}:${KPM_BUS_PORT}/healthz
EOF
  fi
fi

cat <<'EOF'

Press Ctrl+C to stop the stack.
EOF

while true; do
  sleep 5

  if ! kill -0 "${RIC_PID}" 2>/dev/null; then
    echo "nearRT-RIC stopped unexpectedly. Check logs." >&2
    exit 1
  fi
  if ! kill -0 "${AGENT_PID}" 2>/dev/null; then
    echo "emu_agent_gnb stopped unexpectedly. Check logs." >&2
    exit 1
  fi
  if [[ -n "${PORTAL_PID}" ]] && ! kill -0 "${PORTAL_PID}" 2>/dev/null; then
    echo "agent portal stopped unexpectedly. Check ${PORTAL_LOG}" >&2
    exit 1
  fi
  if [[ -n "${RPC_PID}" ]] && ! kill -0 "${RPC_PID}" 2>/dev/null; then
    echo "xApp RPC server stopped unexpectedly. Check ${RPC_LOG}" >&2
    exit 1
  fi
  if [[ -n "${MCP_PID}" ]] && ! kill -0 "${MCP_PID}" 2>/dev/null; then
    if [[ "${MCP_OPTIONAL}" == "1" ]]; then
      echo "MCP metrics server is no longer running; continuing because MCP is optional for the AI page." >&2
      MCP_PID=""
    else
      echo "MCP metrics server stopped unexpectedly. Check ${MCP_LOG}" >&2
      exit 1
    fi
  fi
done
