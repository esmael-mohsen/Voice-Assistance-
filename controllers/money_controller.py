"""Money capability controller backed by the external EGY money det project."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
from uuid import uuid4

from controllers.capability_contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatusSnapshot,
    CapabilityTimeoutPolicy,
    build_result,
)
from controllers.external_process_runtime import (
    build_external_process_env,
    configured_command_argv,
    write_launch_diagnostics,
    write_python_import_probe,
)
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

DEFAULT_MONEY_PROJECT_PATH = Path(__file__).resolve().parents[2] / "EGY money det"
MONEY_PROJECT_ENV = "EGB_MONEY_PROJECT_PATH"
MONEY_PYTHON_ENV = "EGB_MONEY_PYTHON"
MONEY_STOP_FILE_ENV = "EGY_MONEY_STOP_FILE"
MONEY_LOG_DIR_ENV = "EGB_MONEY_LOG_DIR"
MONEY_COMMAND_ENV = "EGB_MONEY_COMMAND"
MONEY_PROCESS_BACKEND_NAME = "egy_money_detection_process"


class AssistiveMoneyProcessController:
    """Lifecycle controller that launches the full EGY money det app."""

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
        timeout_policy: CapabilityTimeoutPolicy | None = None,
        popen_factory: Any | None = None,
    ) -> None:
        self._project_path = Path(
            os.environ.get(MONEY_PROJECT_ENV) or project_path or DEFAULT_MONEY_PROJECT_PATH
        ).resolve()
        self._main_script_path = self._project_path / "main.py"
        self._timeout_policy = timeout_policy or CapabilityTimeoutPolicy(
            capability_id="money_detection",
            start_timeout_s=4.0,
            stop_timeout_s=6.0,
            status_timeout_s=1.0,
            execute_timeout_s=4.0,
            hard_max_s=10.0,
        )
        self._popen_factory = popen_factory or subprocess.Popen
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | Any | None = None
        self._log_handle: Any | None = None
        self._log_path: Path | None = None
        self._stop_file_path: Path | None = None
        self._last_status = "success"
        self._last_error_code: str | None = None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _python_candidates(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        env_python = os.environ.get(MONEY_PYTHON_ENV)
        if env_python:
            candidates.append(Path(env_python).resolve())
        candidates.append((self._project_path / ".venv" / "bin" / "python").resolve())
        candidates.append((self._project_path / ".venv" / "Scripts" / "python.exe").resolve())
        candidates.append(Path(sys.executable).resolve())

        unique: list[Path] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return tuple(unique)

    def _resolved_python(self) -> Path | None:
        for candidate in self._python_candidates():
            if candidate.exists():
                return candidate
        return None

    def _project_ready(self) -> tuple[bool, str | None]:
        if not self._project_path.exists():
            return False, "money_project_missing"
        if not self._main_script_path.exists():
            return False, "money_main_missing"
        if self._resolved_python() is None and configured_command_argv(os.environ.get(MONEY_COMMAND_ENV)) is None:
            return False, "money_python_missing"
        return True, None

    def _money_log_dir(self) -> Path:
        configured = os.environ.get(MONEY_LOG_DIR_ENV)
        if configured:
            return Path(configured).resolve()
        return Path(__file__).resolve().parents[1] / "artifacts" / "money_runtime"

    def _new_stop_file(self) -> Path:
        return Path(tempfile.gettempdir()) / f"egy_money_stop_{uuid4().hex}.flag"

    def _cleanup_finished_process(self) -> None:
        process = self._process
        if process is None or process.poll() is None:
            return
        if self._log_handle is not None:
            try:
                self._log_handle.close()
            except Exception:  # noqa: BLE001
                pass
        self._process = None
        self._log_handle = None
        self._log_path = None
        if self._stop_file_path is not None:
            try:
                self._stop_file_path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        self._stop_file_path = None

    def _is_running(self) -> bool:
        self._cleanup_finished_process()
        return self._process is not None and self._process.poll() is None

    def _status_details(self) -> dict[str, Any]:
        self._cleanup_finished_process()
        python_path = self._resolved_python()
        return {
            "project_path": str(self._project_path),
            "main_script_path": str(self._main_script_path),
            "python_path": None if python_path is None else str(python_path),
            "project_path_exists": self._project_path.exists(),
            "main_script_exists": self._main_script_path.exists(),
            "running": self._is_running(),
            "pid": None if self._process is None else getattr(self._process, "pid", None),
            "log_path": None if self._log_path is None else str(self._log_path),
            "stop_file_path": None if self._stop_file_path is None else str(self._stop_file_path),
        }

    def _availability_failure(self, *, request: CapabilityRequest, error_code: str) -> CapabilityResult:
        self._last_status = "unavailable"
        self._last_error_code = error_code
        return build_result(
            request=request,
            status="unavailable",
            spoken_text=self._localized(
                "مشروع كشف العملات غير متاح حاليا.",
                "The money detection project is currently unavailable.",
            ),
            payload=self._status_details(),
            error_code=error_code,
            backend_name=MONEY_PROCESS_BACKEND_NAME,
        )

    def _spawn_process(self) -> None:
        log_dir = self._money_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"egy_money_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
        stop_file = self._new_stop_file()
        python_path = self._resolved_python()
        configured_argv = configured_command_argv(os.environ.get(MONEY_COMMAND_ENV))
        if python_path is None and configured_argv is None:
            raise RuntimeError("money_python_missing")

        env = build_external_process_env(extra={MONEY_STOP_FILE_ENV: str(stop_file)})

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        log_handle = log_path.open("a", encoding="utf-8", errors="replace")
        argv = configured_argv or [str(python_path), "-u", str(self._main_script_path)]
        write_launch_diagnostics(
            log_handle,
            label="money",
            cwd=self._project_path,
            argv=argv,
            env=env,
            paths={
                "project_path": self._project_path,
                "main_script_path": self._main_script_path,
                "python_path": python_path,
                "stop_file_path": stop_file,
            },
        )
        write_python_import_probe(
            log_handle,
            label="money_voice",
            python_path=python_path or sys.executable,
            modules=("speech_recognition", "pyaudio", "edge_tts", "playsound", "vosk"),
        )
        process = self._popen_factory(
            argv,
            cwd=str(self._project_path),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env,
            creationflags=creationflags,
        )
        self._process = process
        self._log_handle = log_handle
        self._log_path = log_path
        self._stop_file_path = stop_file

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        ready, error_code = self._project_ready()
        if not ready:
            return self._availability_failure(request=request, error_code=error_code or "money_project_missing")

        with self._lock:
            if self._is_running():
                self._last_status = "success"
                self._last_error_code = None
                return build_result(
                    request=request,
                    status="success",
                    spoken_text=self._localized(
                        "مشروع كشف العملات شغال بالفعل.",
                        "The money detection project is already running.",
                    ),
                    payload=self._status_details(),
                    backend_name=MONEY_PROCESS_BACKEND_NAME,
                )

            self._spawn_process()
            startup_deadline = time.time() + 5.0
            while time.time() < startup_deadline:
                if not self._is_running():
                    break
                time.sleep(0.2)
            if not self._is_running():
                self._last_status = "failed"
                self._last_error_code = "money_process_exited_early"
                return build_result(
                    request=request,
                    status="failed",
                    spoken_text=self._localized(
                        "تعذر تشغيل مشروع كشف العملات بشكل صحيح.",
                        "The money detection project exited before it was ready.",
                    ),
                    payload=self._status_details(),
                    error_code="money_process_exited_early",
                    backend_name=MONEY_PROCESS_BACKEND_NAME,
                )

            self._last_status = "success"
            self._last_error_code = None
            return build_result(
                request=request,
                status="success",
                spoken_text=self._localized(
                    "تم تشغيل مشروع كشف العملات.",
                    "The money detection project is now running.",
                ),
                payload={**self._status_details(), "suspend_assistant_listening": True},
                backend_name=MONEY_PROCESS_BACKEND_NAME,
            )

    def _request_graceful_stop(self) -> None:
        if self._stop_file_path is not None:
            self._stop_file_path.write_text("stop\n", encoding="utf-8")

    def _wait_for_exit(self, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if not self._is_running():
                return True
            time.sleep(0.2)
        return not self._is_running()

    def _force_stop(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        if platform.system().lower() == "windows" and hasattr(signal, "CTRL_BREAK_EVENT"):
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
                if self._wait_for_exit(1.5):
                    return
            except Exception:  # noqa: BLE001
                pass
        try:
            process.terminate()
            if self._wait_for_exit(1.5):
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            process.kill()
        except Exception:  # noqa: BLE001
            pass

    def stop(self, request: CapabilityRequest) -> CapabilityResult:
        with self._lock:
            if not self._is_running():
                self._last_status = "success"
                self._last_error_code = None
                return build_result(
                    request=request,
                    status="success",
                    spoken_text=self._localized(
                        "مشروع كشف العملات متوقف بالفعل.",
                        "The money detection project is already stopped.",
                    ),
                    payload=self._status_details(),
                    backend_name=MONEY_PROCESS_BACKEND_NAME,
                )

            self._request_graceful_stop()
            if not self._wait_for_exit(4.0):
                self._force_stop()
                self._wait_for_exit(2.0)

            stopped = not self._is_running()
            self._last_status = "success" if stopped else "failed"
            self._last_error_code = None if stopped else "money_process_stop_failed"
            return build_result(
                request=request,
                status="success" if stopped else "failed",
                spoken_text=self._localized(
                    "تم إيقاف مشروع كشف العملات.",
                    "The money detection project has been stopped.",
                )
                if stopped
                else self._localized(
                    "تعذر إيقاف مشروع كشف العملات بشكل صحيح.",
                    "The money detection project could not be stopped cleanly.",
                ),
                payload=self._status_details(),
                error_code=None if stopped else "money_process_stop_failed",
                backend_name=MONEY_PROCESS_BACKEND_NAME,
            )

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        return self.start(request)

    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot:
        ready, error_code = self._project_ready()
        running = self._is_running()
        details = self._status_details()
        if error_code is not None:
            details["error_code"] = error_code
        return CapabilityStatusSnapshot(
            capability_id=request.capability_id,
            lifecycle_state="active" if running else "inactive",
            availability="ready" if ready else "unavailable",
            using_fallback=False,
            backend_name=MONEY_PROCESS_BACKEND_NAME,
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=self._localized(
                "مشروع كشف العملات شغال حاليا." if running else "مشروع كشف العملات متوقف حاليا.",
                "The money detection project is running." if running else "The money detection project is stopped.",
            )
            if ready
            else self._localized(
                "مشروع كشف العملات غير متاح حاليا.",
                "The money detection project is currently unavailable.",
            ),
            details=details,
        )
