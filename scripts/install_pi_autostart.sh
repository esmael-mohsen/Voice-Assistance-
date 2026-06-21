#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${EGB_VOICE_ASSISTANT_DIR:-$(cd -- "${SCRIPT_DIR}/.." && pwd)}"
AUTOSTART_DIR="${HOME}/.config/autostart"
BIN_DIR="${HOME}/.local/bin"
WRAPPER_PATH="${BIN_DIR}/egb-voice-assistant-autostart"
DESKTOP_FILE="${AUTOSTART_DIR}/egb-voice-assistant.desktop"
BOOT_LOG_DIR="${EGB_BOOT_LOG_DIR:-${HOME}/egb_logs/voice_assistant}"
ENABLE_AUTOLOGIN=1

usage() {
  cat <<'USAGE'
Install Raspberry Pi desktop autostart for the EGB voice assistant.

Usage:
  bash scripts/install_pi_autostart.sh [--no-autologin]

This configures desktop auto-login with raspi-config when available.
It does not delete or blank the Raspberry Pi user's password.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-autologin)
      ENABLE_AUTOLOGIN=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[EGB_AUTOSTART] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "${AUTOSTART_DIR}" "${BIN_DIR}" "${BOOT_LOG_DIR}"

cat > "${WRAPPER_PATH}" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR}"
BOOT_LOG_DIR="${BOOT_LOG_DIR}"
LAUNCHER="\${PROJECT_DIR}/scripts/launch_voice_assistant_pi.sh"

export EGB_VOICE_ASSISTANT_DIR="\${PROJECT_DIR}"
export EGB_BOOT_LOG_DIR="\${BOOT_LOG_DIR}"

cd "\${PROJECT_DIR}"

if command -v lxterminal >/dev/null 2>&1; then
  TERMINAL_COMMAND="bash -lc '\"\${LAUNCHER}\"; echo; echo \"Press Enter to close this terminal...\"; read -r _'"
  exec lxterminal --working-directory="\${PROJECT_DIR}" --command="\${TERMINAL_COMMAND}"
fi

if command -v x-terminal-emulator >/dev/null 2>&1; then
  TERMINAL_COMMAND="bash -lc '\"\${LAUNCHER}\"; echo; echo \"Press Enter to close this terminal...\"; read -r _'"
  exec x-terminal-emulator -e bash -lc "\${TERMINAL_COMMAND}"
fi

exec bash "\${LAUNCHER}"
EOF
chmod +x "${WRAPPER_PATH}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=EGB Voice Assistant
Comment=Start EGB voice assistant when the Raspberry Pi desktop opens
Exec=${WRAPPER_PATH}
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod 0644 "${DESKTOP_FILE}"

if [[ "${ENABLE_AUTOLOGIN}" == "1" ]]; then
  if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4
  else
    echo "[EGB_AUTOSTART] raspi-config was not found; desktop autostart was installed, but auto-login was not changed."
    echo "[EGB_AUTOSTART] Enable desktop auto-login manually from Raspberry Pi Configuration."
  fi
fi

if ! command -v lxterminal >/dev/null 2>&1; then
  echo "[EGB_AUTOSTART] lxterminal is not installed. Install it with:"
  echo "  sudo apt update && sudo apt install -y lxterminal"
fi

echo "[EGB_AUTOSTART] Installed desktop entry: ${DESKTOP_FILE}"
echo "[EGB_AUTOSTART] Installed launcher wrapper: ${WRAPPER_PATH}"
echo "[EGB_AUTOSTART] Boot logs directory: ${BOOT_LOG_DIR}"
echo "[EGB_AUTOSTART] Reboot with: sudo reboot"
