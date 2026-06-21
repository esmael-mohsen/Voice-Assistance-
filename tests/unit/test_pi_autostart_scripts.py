from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pi_voice_launcher_runs_console_runtime_from_project_root() -> None:
    launcher = ROOT / "scripts" / "launch_voice_assistant_pi.sh"

    content = launcher.read_text(encoding="utf-8")

    assert "PROJECT_DIR=" in content
    assert "source .venv/bin/activate" in content
    assert "python main.py --console" in content
    assert "EGB_RUNTIME_TARGET=raspberry_pi" in content
    assert "tee -a" in content


def test_pi_autostart_installer_creates_desktop_entry_without_removing_password() -> None:
    installer = ROOT / "scripts" / "install_pi_autostart.sh"

    content = installer.read_text(encoding="utf-8")

    assert "egb-voice-assistant.desktop" in content
    assert "X-GNOME-Autostart-enabled=true" in content
    assert "lxterminal" in content
    assert "raspi-config nonint do_boot_behaviour B4" in content
    assert "passwd -d" not in content
    assert "delete password" not in content.lower()
