"""Shared runtime helpers for launching external EGB function projects."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, TextIO

EXTERNAL_DISPLAY_ENV = "EGB_EXTERNAL_DISPLAY"
EXTERNAL_XAUTHORITY_ENV = "EGB_EXTERNAL_XAUTHORITY"
EXTERNAL_WAYLAND_ENV = "EGB_EXTERNAL_WAYLAND_DISPLAY"

_DIAGNOSTIC_ENV_KEYS = (
    "EGB_RUNTIME_TARGET",
    "DISPLAY",
    "XAUTHORITY",
    "WAYLAND_DISPLAY",
    "QT_QPA_PLATFORM",
    "PYTHONUNBUFFERED",
    "PYTHONIOENCODING",
    "ASSISTANT_MICROPHONE_INDEX",
    "ASSISTANT_SHOW_WINDOW",
    "ASSISTANT_VOICE_ENABLED",
)


def build_external_process_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    display = env.get(EXTERNAL_DISPLAY_ENV)
    xauthority = env.get(EXTERNAL_XAUTHORITY_ENV)
    wayland_display = env.get(EXTERNAL_WAYLAND_ENV)
    if display and not env.get("DISPLAY"):
        env["DISPLAY"] = display
    if xauthority and not env.get("XAUTHORITY"):
        env["XAUTHORITY"] = xauthority
    if wayland_display and not env.get("WAYLAND_DISPLAY"):
        env["WAYLAND_DISPLAY"] = wayland_display

    if env.get("DISPLAY"):
        env.setdefault("QT_QPA_PLATFORM", "xcb")

    if extra:
        for key, value in extra.items():
            env[str(key)] = str(value)
    return env


def _path_exists_label(value: str) -> str:
    if not value:
        return "exists=False"
    return f"exists={Path(value).exists()}"


def write_launch_diagnostics(
    handle: TextIO,
    *,
    label: str,
    cwd: str | Path,
    argv: list[str],
    env: dict[str, str],
    paths: dict[str, str | Path | None] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    handle.write(f"[EGB_LAUNCH] label={label}\n")
    handle.write(f"[EGB_LAUNCH] started_at={datetime.now(timezone.utc).isoformat()}\n")
    handle.write(f"[EGB_LAUNCH] cwd={cwd}\n")
    handle.write(f"[EGB_LAUNCH] argv={argv}\n")
    for key, value in (paths or {}).items():
        text = "" if value is None else str(value)
        handle.write(f"[EGB_LAUNCH] {key}={text} {_path_exists_label(text)}\n")
    for key in _DIAGNOSTIC_ENV_KEYS:
        value = env.get(key, "")
        if key == "XAUTHORITY":
            handle.write(f"[EGB_LAUNCH] {key}={value} {_path_exists_label(value)}\n")
        else:
            handle.write(f"[EGB_LAUNCH] {key}={value}\n")
    for key, value in (extra or {}).items():
        handle.write(f"[EGB_LAUNCH] {key}={value}\n")
    handle.write("[EGB_LAUNCH] process_output_begin\n")
    handle.flush()
