#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${EGB_VOICE_ASSISTANT_DIR:-$(cd -- "${SCRIPT_DIR}/.." && pwd)}"
LOG_DIR="${EGB_BOOT_LOG_DIR:-/home/egb/egb_logs/voice_assistant}"
RUN_STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/voice_assistant_boot_${RUN_STAMP}.log"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_DIR}"

export EGB_RUNTIME_TARGET=raspberry_pi
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "[EGB_BOOT] Missing virtual environment: ${PROJECT_DIR}/.venv" | tee -a "${LOG_FILE}"
  echo "[EGB_BOOT] Create it first, then rerun scripts/install_pi_autostart.sh" | tee -a "${LOG_FILE}"
  exit 1
fi

echo "[EGB_BOOT] started_at=$(date -Is)" | tee -a "${LOG_FILE}"
echo "[EGB_BOOT] project_dir=${PROJECT_DIR}" | tee -a "${LOG_FILE}"
echo "[EGB_BOOT] log_file=${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "[EGB_BOOT] display=${DISPLAY:-}" | tee -a "${LOG_FILE}"
echo "[EGB_BOOT] xauthority=${XAUTHORITY:-}" | tee -a "${LOG_FILE}"
echo "[EGB_BOOT] wayland_display=${WAYLAND_DISPLAY:-}" | tee -a "${LOG_FILE}"

# shellcheck disable=SC1091
source .venv/bin/activate

python main.py --console 2>&1 | tee -a "${LOG_FILE}"
