#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
WORKSPACE_DIR="${WORKSPACE_DIR:-${PWD}}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-flexric-py310}"
CONDA_SH="${CONDA_SH:-${HOME}/anaconda3/etc/profile.d/conda.sh}"
DEFAULT_ENV_PY="${HOME}/anaconda3/envs/${CONDA_ENV_NAME}/bin/python"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_ENV_PY}}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"

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
elif [[ -d "${WORKSPACE_DIR}/build/examples/xApp/python3" ]]; then
  BUILD_DIR="${WORKSPACE_DIR}/build"
else
  BUILD_DIR="${ROOT_DIR}/build"
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

require_cmd cmake

cmake -S "${ROOT_DIR}" -B "${BUILD_DIR}" \
  -DXAPP_TARGET_LANGUAGE=PYTHON_LANG \
  -DPython3_EXECUTABLE="${PYTHON_BIN}"

cmake --build "${BUILD_DIR}" -j"${JOBS}"

exec "${SCRIPT_DIR}/run_agent_portal_stack.sh" "$@"
