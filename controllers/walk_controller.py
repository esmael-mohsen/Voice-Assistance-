"""Walk / obstacle detection controller backed by the external ROS2 project."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import threading
import time
from typing import Any

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
    wrap_argv_for_visible_terminal,
    write_launch_diagnostics,
)
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

DEFAULT_WALK_PROJECT_PATH = Path(__file__).resolve().parents[2] / "walk_assistant"
WALK_PROJECT_ENV = "EGB_WALK_PROJECT_PATH"
WALK_PYTHON_ENV = "EGB_WALK_PYTHON"
WALK_LOG_DIR_ENV = "EGB_WALK_LOG_DIR"
WALK_ENTRYPOINT_ENV = "EGB_WALK_ENTRYPOINT"
WALK_COMMAND_ENV = "EGB_WALK_COMMAND"
WALK_PROCESS_BACKEND_NAME = "walk_assistant_process"


class WalkAssistantProcessController:
    """Lifecycle controller that launches the full Walk_Assistant ROS app."""

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
        timeout_policy: CapabilityTimeoutPolicy | None = None,
        popen_factory: Any | None = None,
    ) -> None:
        self._project_path = Path(os.environ.get(WALK_PROJECT_ENV) or project_path or DEFAULT_WALK_PROJECT_PATH).resolve()
        self._timeout_policy = timeout_policy or CapabilityTimeoutPolicy(
            capability_id="obstacle_detection",
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
        self._last_status = "success"
        self._last_error_code: str | None = None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _python_candidates(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        env_python = os.environ.get(WALK_PYTHON_ENV)
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

    def _resolved_entrypoint(self) -> Path | None:
        configured = os.environ.get(WALK_ENTRYPOINT_ENV)
        if configured:
            return Path(configured).resolve()
        candidates = (
            self._project_path / "ros2_ws" / "src" / "blind_assist" / "launch" / "blind_assist.launch.py",
            self._project_path / "blind_assist.launch.py",
            self._project_path / "main.py",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return None

    def _launch_argv(self) -> list[str]:
        configured_command = os.environ.get(WALK_COMMAND_ENV)
        if configured_command:
            return configured_command_argv(configured_command) or []
        entrypoint = self._resolved_entrypoint()
        python_path = self._resolved_python()
        if entrypoint is None:
            raise RuntimeError("walk_entrypoint_missing")
        if python_path is None:
            raise RuntimeError("walk_python_missing")
        if entrypoint.name.endswith(".launch.py"):
            return [str(python_path), "-m", "launch", str(entrypoint)]
        return [str(python_path), "-u", str(entrypoint)]

    def _project_ready(self) -> tuple[bool, str | None]:
        if not self._project_path.exists():
            return False, "walk_project_missing"
        if self._resolved_entrypoint() is None and not os.environ.get(WALK_COMMAND_ENV):
            return False, "walk_entrypoint_missing"
        if self._resolved_python() is None and not os.environ.get(WALK_COMMAND_ENV):
            return False, "walk_python_missing"
        return True, None

    def _walk_log_dir(self) -> Path:
        configured = os.environ.get(WALK_LOG_DIR_ENV)
        if configured:
            return Path(configured).resolve()
        return Path(__file__).resolve().parents[1] / "artifacts" / "walk_runtime"

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

    def _is_running(self) -> bool:
        self._cleanup_finished_process()
        return self._process is not None and self._process.poll() is None

    def _status_details(self) -> dict[str, Any]:
        self._cleanup_finished_process()
        entrypoint = self._resolved_entrypoint()
        python_path = self._resolved_python()
        return {
            "project_path": str(self._project_path),
            "entrypoint_path": None if entrypoint is None else str(entrypoint),
            "python_path": None if python_path is None else str(python_path),
            "project_path_exists": self._project_path.exists(),
            "entrypoint_exists": entrypoint is not None and entrypoint.exists(),
            "running": self._is_running(),
            "pid": None if self._process is None else getattr(self._process, "pid", None),
            "log_path": None if self._log_path is None else str(self._log_path),
            "suspend_assistant_listening": self._is_running(),
        }

    def _availability_failure(self, *, request: CapabilityRequest, error_code: str) -> CapabilityResult:
        self._last_status = "unavailable"
        self._last_error_code = error_code
        return build_result(
            request=request,
            status="unavailable",
            spoken_text=self._localized(
                "مشروع اكتشاف العوائق غير متاح حاليا.",
                "The walk assistant project is currently unavailable.",
            ),
            payload=self._status_details(),
            error_code=error_code,
            backend_name=WALK_PROCESS_BACKEND_NAME,
        )

    def _spawn_process(self) -> None:
        log_dir = self._walk_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"walk_assistant_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
        original_argv = self._launch_argv()
        env = build_external_process_env()
        argv = wrap_argv_for_visible_terminal(
            original_argv,
            cwd=self._project_path,
            log_path=log_path,
            env=env,
        )

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        log_handle = log_path.open("a", encoding="utf-8", errors="replace")
        write_launch_diagnostics(
            log_handle,
            label="walk_assistant",
            cwd=self._project_path,
            argv=argv,
            env=env,
            paths={
                "project_path": self._project_path,
                "entrypoint_path": self._resolved_entrypoint(),
                "python_path": self._resolved_python(),
            },
            extra={"original_argv": original_argv},
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

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        ready, error_code = self._project_ready()
        if not ready:
            return self._availability_failure(request=request, error_code=error_code or "walk_project_missing")

        with self._lock:
            if self._is_running():
                self._last_status = "success"
                self._last_error_code = None
                return build_result(
                    request=request,
                    status="success",
                    spoken_text=self._localized(
                        "اكتشاف العوائق شغال بالفعل.",
                        "The walk assistant project is already running.",
                    ),
                    payload=self._status_details(),
                    backend_name=WALK_PROCESS_BACKEND_NAME,
                )

            self._spawn_process()
            startup_deadline = time.time() + 5.0
            while time.time() < startup_deadline:
                if not self._is_running():
                    break
                time.sleep(0.2)
            if not self._is_running():
                self._last_status = "failed"
                self._last_error_code = "walk_process_exited_early"
                return build_result(
                    request=request,
                    status="failed",
                    spoken_text=self._localized(
                        "تعذر تشغيل مشروع اكتشاف العوائق بشكل صحيح.",
                        "The walk assistant project exited before it was ready.",
                    ),
                    payload=self._status_details(),
                    error_code="walk_process_exited_early",
                    backend_name=WALK_PROCESS_BACKEND_NAME,
                )

            self._last_status = "success"
            self._last_error_code = None
            details = self._status_details()
            details["suspend_assistant_listening"] = True
            return build_result(
                request=request,
                status="success",
                spoken_text=self._localized(
                    "تم تشغيل اكتشاف العوائق.",
                    "The walk assistant project is now running.",
                ),
                payload=details,
                backend_name=WALK_PROCESS_BACKEND_NAME,
            )

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
                        "اكتشاف العوائق متوقف بالفعل.",
                        "The walk assistant project is already stopped.",
                    ),
                    payload=self._status_details(),
                    backend_name=WALK_PROCESS_BACKEND_NAME,
                )

            self._force_stop()
            self._wait_for_exit(2.0)

            stopped = not self._is_running()
            self._last_status = "success" if stopped else "failed"
            self._last_error_code = None if stopped else "walk_process_stop_failed"
            return build_result(
                request=request,
                status="success" if stopped else "failed",
                spoken_text=self._localized(
                    "تم إيقاف اكتشاف العوائق.",
                    "The walk assistant project has been stopped.",
                )
                if stopped
                else self._localized(
                    "تعذر إيقاف مشروع اكتشاف العوائق بشكل صحيح.",
                    "The walk assistant project could not be stopped cleanly.",
                ),
                payload=self._status_details(),
                error_code=None if stopped else "walk_process_stop_failed",
                backend_name=WALK_PROCESS_BACKEND_NAME,
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
            backend_name=WALK_PROCESS_BACKEND_NAME,
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=self._localized(
                "اكتشاف العوائق شغال حاليا." if running else "اكتشاف العوائق متوقف حاليا.",
                "The walk assistant project is running." if running else "The walk assistant project is stopped.",
            )
            if ready
            else self._localized(
                "مشروع اكتشاف العوائق غير متاح حاليا.",
                "The walk assistant project is currently unavailable.",
            ),
            details=details,
        )
