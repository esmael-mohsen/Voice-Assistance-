"""Shared runtime helpers for launching external EGB function projects."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any, TextIO

EXTERNAL_DISPLAY_ENV = "EGB_EXTERNAL_DISPLAY"
EXTERNAL_XAUTHORITY_ENV = "EGB_EXTERNAL_XAUTHORITY"
EXTERNAL_WAYLAND_ENV = "EGB_EXTERNAL_WAYLAND_DISPLAY"
EXTERNAL_TERMINAL_ENABLED_ENV = "EGB_EXTERNAL_TERMINAL_ENABLED"
EXTERNAL_TERMINAL_APP_ENV = "EGB_EXTERNAL_TERMINAL_APP"
EXTERNAL_TERMINAL_HOLD_ENV = "EGB_EXTERNAL_TERMINAL_HOLD_ON_EXIT"

_AUTO_TERMINAL_CANDIDATES = (
    "lxterminal",
    "x-terminal-emulator",
    "gnome-terminal",
    "xfce4-terminal",
    "xterm",
)

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
    "EGB_VISION_COMMAND",
    "EGB_OCR_COMMAND",
    "EGB_MONEY_COMMAND",
    "EGB_WALK_COMMAND",
    "EGB_EXTERNAL_TERMINAL_ENABLED",
    "EGB_EXTERNAL_TERMINAL_APP",
    "EGB_EXTERNAL_TERMINAL_HOLD_ON_EXIT",
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


def configured_command_argv(command: str | None) -> list[str] | None:
    cleaned = str(command or "").strip()
    if not cleaned:
        return None
    return shlex.split(cleaned)


def _env_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _configured_terminal_app_argv(env: dict[str, str]) -> list[str] | None:
    configured = str(env.get(EXTERNAL_TERMINAL_APP_ENV) or "auto").strip()
    if not configured or configured.lower() == "auto":
        for candidate in _AUTO_TERMINAL_CANDIDATES:
            resolved = shutil.which(candidate)
            if resolved:
                return [resolved]
        return None
    return shlex.split(configured)


def _terminal_shell_script(
    argv: list[str],
    *,
    log_path: str | Path,
    hold_on_exit: bool,
) -> str:
    command = shlex.join(argv)
    quoted_log_path = shlex.quote(str(log_path))
    script = (
        "set -o pipefail; "
        'echo "[EGB_TERMINAL] cwd=$(pwd)" | tee -a '
        f"{quoted_log_path}; "
        f"( {command} ) 2>&1 | tee -a {quoted_log_path}; "
        "status=${PIPESTATUS[0]}; "
        'echo "[EGB_TERMINAL] exit_status=$status" | tee -a '
        f"{quoted_log_path}; "
    )
    if hold_on_exit:
        script += "echo; echo 'Press Enter to close this terminal...'; read -r _; "
    return script + "exit $status"


def wrap_argv_for_visible_terminal(
    argv: list[str],
    *,
    cwd: str | Path,
    log_path: str | Path,
    env: dict[str, str],
) -> list[str]:
    """Wrap a launch command in a visible terminal when Pi diagnostics ask for it."""

    if not _env_truthy(env.get(EXTERNAL_TERMINAL_ENABLED_ENV)):
        return argv

    terminal_argv = _configured_terminal_app_argv(env)
    if not terminal_argv:
        return argv

    terminal_name = Path(terminal_argv[0]).name.lower()
    script = _terminal_shell_script(
        argv,
        log_path=log_path,
        hold_on_exit=_env_truthy(env.get(EXTERNAL_TERMINAL_HOLD_ENV)),
    )
    cwd_text = str(cwd)

    if terminal_name in {"gnome-terminal", "kgx"}:
        return [*terminal_argv, "--working-directory", cwd_text, "--", "bash", "-lc", script]
    if terminal_name == "xfce4-terminal":
        return [*terminal_argv, f"--working-directory={cwd_text}", "--command", f"bash -lc {shlex.quote(script)}"]
    if terminal_name == "lxterminal":
        return [*terminal_argv, f"--working-directory={cwd_text}", "--command", f"bash -lc {shlex.quote(script)}"]
    return [*terminal_argv, "-e", "bash", "-lc", script]


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


def write_python_import_probe(
    handle: TextIO,
    *,
    label: str,
    python_path: str | Path,
    modules: tuple[str, ...],
    timeout_s: float = 6.0,
) -> None:
    module_list = tuple(str(module).strip() for module in modules if str(module).strip())
    if not module_list:
        return
    probe = (
        "import importlib.util, sys\n"
        f"modules = {module_list!r}\n"
        "for name in modules:\n"
        "    spec = importlib.util.find_spec(name)\n"
        "    print(f'module={name} status={\"ok\" if spec else \"missing\"}')\n"
    )
    handle.write(f"[EGB_PREFLIGHT] label={label} python_path={python_path}\n")
    try:
        completed = subprocess.run(
            [str(python_path), "-c", probe],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        handle.write(f"[EGB_PREFLIGHT] probe_failed error={exc}\n")
        handle.flush()
        return

    output = (completed.stdout or "").strip().splitlines()
    for line in output:
        handle.write(f"[EGB_PREFLIGHT] {line}\n")
    stderr = (completed.stderr or "").strip()
    if stderr:
        handle.write(f"[EGB_PREFLIGHT] stderr={stderr[:800]}\n")
    handle.write(f"[EGB_PREFLIGHT] returncode={completed.returncode}\n")
    if not output and completed.returncode != 0:
        handle.write(f"[EGB_PREFLIGHT] executable={sys.executable}\n")
    handle.flush()
