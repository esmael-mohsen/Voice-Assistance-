from __future__ import annotations

import os
from pathlib import Path
import sys

from controllers.external_process_runtime import (
    build_external_process_env,
    wrap_argv_for_visible_terminal,
    write_python_import_probe,
    write_launch_diagnostics,
)


def test_external_process_env_maps_pi_display_overrides(monkeypatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("XAUTHORITY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("EGB_RUNTIME_TARGET", "raspberry_pi")
    monkeypatch.setenv("EGB_EXTERNAL_DISPLAY", ":0")
    monkeypatch.setenv("EGB_EXTERNAL_XAUTHORITY", "/run/user/1000/.mutter-Xwaylandauth.TEST")
    monkeypatch.setenv("EGB_EXTERNAL_WAYLAND_DISPLAY", "wayland-0")

    env = build_external_process_env(extra={"CUSTOM_FLAG": "1"})

    assert env["PYTHONUNBUFFERED"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert env["DISPLAY"] == ":0"
    assert env["XAUTHORITY"] == "/run/user/1000/.mutter-Xwaylandauth.TEST"
    assert env["WAYLAND_DISPLAY"] == "wayland-0"
    assert env["CUSTOM_FLAG"] == "1"


def test_external_process_env_maps_shared_numeric_camera_index(monkeypatch) -> None:
    monkeypatch.setenv("EGB_CAMERA_INDEX", "2")
    monkeypatch.delenv("EGB_CAMERA_SOURCE", raising=False)
    monkeypatch.delenv("ASSISTANT_CAMERA_SOURCE", raising=False)
    monkeypatch.delenv("ASSISTANT_CAMERA_INDEX", raising=False)
    monkeypatch.delenv("EGY_MONEY_CAMERA_SOURCE", raising=False)
    monkeypatch.delenv("EGB_VISION_CAMERA_INDEX", raising=False)

    env = build_external_process_env()

    assert env["EGB_CAMERA_INDEX"] == "2"
    assert env["EGB_VISION_CAMERA_INDEX"] == "2"
    assert env["CAMERA_INDEX"] == "2"
    assert env["ASSISTANT_CAMERA_INDEX"] == "2"
    assert env["EGY_MONEY_CAMERA_SOURCE"] == "2"
    assert "ASSISTANT_CAMERA_SOURCE" not in env


def test_external_process_env_maps_shared_url_camera_source(monkeypatch) -> None:
    monkeypatch.delenv("EGB_CAMERA_INDEX", raising=False)
    monkeypatch.setenv("EGB_CAMERA_SOURCE", "http://127.0.0.1:8080/video")
    monkeypatch.delenv("ASSISTANT_CAMERA_SOURCE", raising=False)
    monkeypatch.delenv("EGY_MONEY_CAMERA_SOURCE", raising=False)

    env = build_external_process_env()

    assert env["EGB_CAMERA_SOURCE"] == "http://127.0.0.1:8080/video"
    assert env["ASSISTANT_CAMERA_SOURCE"] == "http://127.0.0.1:8080/video"
    assert env["EGY_MONEY_CAMERA_SOURCE"] == "http://127.0.0.1:8080/video"


def test_launch_diagnostics_write_actionable_env_and_path_summary(tmp_path: Path) -> None:
    log_path = tmp_path / "external.log"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    python_path = project_dir / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    with log_path.open("a", encoding="utf-8") as handle:
        write_launch_diagnostics(
            handle,
            label="vision",
            cwd=project_dir,
            argv=[str(python_path), "-u", str(project_dir / "main.py")],
            env={
                "DISPLAY": ":0",
                "XAUTHORITY": str(tmp_path / "missing-auth"),
                "WAYLAND_DISPLAY": "wayland-0",
                "ASSISTANT_MICROPHONE_INDEX": "3",
            },
            paths={"python_path": python_path, "project_path": project_dir},
        )

    content = log_path.read_text(encoding="utf-8")

    assert "[EGB_LAUNCH] label=vision" in content
    assert "DISPLAY=:0" in content
    assert "XAUTHORITY=" in content
    assert "exists=False" in content
    assert "ASSISTANT_MICROPHONE_INDEX=3" in content
    assert f"python_path={python_path}" in content


def test_python_import_probe_records_missing_and_available_modules(tmp_path: Path) -> None:
    log_path = tmp_path / "probe.log"

    with log_path.open("a", encoding="utf-8") as handle:
        write_python_import_probe(
            handle,
            label="money_voice",
            python_path=Path(sys.executable),
            modules=("sys", "definitely_missing_egb_module"),
            timeout_s=5.0,
        )

    content = log_path.read_text(encoding="utf-8")

    assert "[EGB_PREFLIGHT] label=money_voice" in content
    assert "module=sys status=ok" in content
    assert "module=definitely_missing_egb_module status=missing" in content


def test_visible_terminal_wrapper_uses_configured_lxterminal(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "money-project"
    log_path = tmp_path / "money.log"
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_ENABLED", "1")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_APP", "lxterminal")
    monkeypatch.setenv("EGB_EXTERNAL_TERMINAL_HOLD_ON_EXIT", "1")

    wrapped = wrap_argv_for_visible_terminal(
        ["bash", "-lc", "source .venv/bin/activate && exec python -u main.py"],
        cwd=project_dir,
        log_path=log_path,
        env=dict(os.environ),
    )

    assert wrapped[:2] == ["lxterminal", f"--working-directory={project_dir}"]
    assert wrapped[2] == "--command"
    assert wrapped[3].startswith("bash -lc ")
    assert "source .venv/bin/activate && exec python -u main.py" in wrapped[3]
    assert "tee -a" in wrapped[3]
    assert str(log_path) in wrapped[3]
    assert "Press Enter to close this terminal" in wrapped[3]
