"""Obstacle capability controller with adapter boundary and timeout safety."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Protocol

from controllers.capability_contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatusSnapshot,
    CapabilityTimeoutPolicy,
    build_result,
    invoke_with_timeout,
)
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class ObstacleSensorAdapter(Protocol):
    def is_available(self) -> bool: ...
    def start_monitoring(self) -> None: ...
    def stop_monitoring(self) -> None: ...
    def read_observation(self, timeout_s: float) -> dict[str, Any] | None: ...
    def describe_health(self) -> dict[str, Any]: ...


class LocalObstacleSensorAdapter:
    """Local adapter placeholder for the first migrated real capability path."""

    def __init__(self, *, available: bool = True, sensor_source: str = "local_obstacle_adapter") -> None:
        self.available = available
        self.active = False
        self.sensor_source = sensor_source

    def is_available(self) -> bool:
        return self.available

    def start_monitoring(self) -> None:
        self.active = True

    def stop_monitoring(self) -> None:
        self.active = False

    def read_observation(self, timeout_s: float) -> dict[str, Any] | None:
        if not self.available:
            return None
        # Local deterministic placeholder until hardware sensor wiring is integrated.
        return {
            "detected": False,
            "distance_meters": 1.5,
            "angle_degrees": 0.0,
            "severity": "clear",
            "confidence": 0.9,
            "sensor_source": self.sensor_source,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def describe_health(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "active": self.active,
            "sensor_source": self.sensor_source,
            "requires_network": False,
        }


class ObstacleCapabilityController:
    """Controller for obstacle detection capability lifecycle and execution."""

    def __init__(
        self,
        *,
        adapter: ObstacleSensorAdapter | None = None,
        timeout_policy: CapabilityTimeoutPolicy | None = None,
    ) -> None:
        self._adapter = adapter or LocalObstacleSensorAdapter()
        self._timeout_policy = timeout_policy or CapabilityTimeoutPolicy(
            capability_id="obstacle_detection",
            start_timeout_s=3.0,
            stop_timeout_s=3.0,
            status_timeout_s=3.0,
            execute_timeout_s=3.0,
            hard_max_s=10.0,
        )
        self._active = False
        self._last_status = "success"
        self._last_error_code: str | None = None
        self._last_observation: dict[str, Any] | None = None

    @property
    def timeout_policy(self) -> CapabilityTimeoutPolicy:
        return self._timeout_policy

    def set_adapter(self, adapter: ObstacleSensorAdapter) -> None:
        self._adapter = adapter
        self._active = False
        self._last_observation = None
        self._last_status = "success"
        self._last_error_code = None

    def _localized(self, ar_text: str, en_text: str) -> str:
        return settings_manager.speak_localized(ar_text, en_text)

    def _availability_failure(
        self,
        *,
        request: CapabilityRequest,
        duration_ms: int = 0,
    ) -> CapabilityResult:
        self._last_status = "unavailable"
        self._last_error_code = "capability_unavailable"
        spoken = self._localized(
            "ميزة اكتشاف العوائق غير متاحة الان.",
            "Obstacle capability is currently unavailable.",
        )
        return build_result(
            request=request,
            status="unavailable",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "inactive",
                "using_fallback": False,
                "availability": "unavailable",
            },
            error_code="capability_unavailable",
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"health": self._adapter.describe_health()},
        )

    def _timeout_failure(self, *, request: CapabilityRequest, duration_ms: int) -> CapabilityResult:
        self._last_status = "timeout"
        self._last_error_code = "capability_timeout"
        spoken = self._localized(
            "انتهت مهلة اكتشاف العوائق. حاول مرة اخرى.",
            "Obstacle detection timed out. Please try again.",
        )
        return build_result(
            request=request,
            status="timeout",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "active" if self._active else "inactive",
                "using_fallback": False,
            },
            error_code="capability_timeout",
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"timeout_seconds": request.timeout_seconds},
        )

    def _exception_failure(
        self,
        *,
        request: CapabilityRequest,
        error: Exception,
        duration_ms: int,
    ) -> CapabilityResult:
        self._last_status = "failed"
        self._last_error_code = "capability_failure"
        logger.error("[OBSTACLE] capability action failed action=%s error=%s", request.action, error)
        spoken = self._localized(
            "حدث خطا اثناء تشغيل اكتشاف العوائق.",
            "Obstacle capability failed while processing your request.",
        )
        return build_result(
            request=request,
            status="failed",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "active" if self._active else "failed",
                "using_fallback": False,
            },
            error_code="capability_failure",
            duration_ms=duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"exception": str(error)},
        )

    def _idempotent_success(
        self,
        *,
        request: CapabilityRequest,
        lifecycle_state: str,
        spoken_text: str,
    ) -> CapabilityResult:
        self._last_status = "success"
        self._last_error_code = None
        return build_result(
            request=request,
            status="success",
            spoken_text=spoken_text,
            payload={
                "lifecycle_state": lifecycle_state,
                "using_fallback": False,
                "idempotent": True,
            },
            duration_ms=0,
            used_fallback=False,
            backend_name="obstacle_sensor",
        )

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        if not self._adapter.is_available():
            return self._availability_failure(request=request)

        if self._active:
            spoken = self._localized(
                "اكتشاف العوائق يعمل بالفعل.",
                "Obstacle detection is already active.",
            )
            return self._idempotent_success(request=request, lifecycle_state="active", spoken_text=spoken)

        invocation = invoke_with_timeout(self._adapter.start_monitoring, timeout_seconds=request.timeout_seconds)
        if invocation.timed_out:
            return self._timeout_failure(request=request, duration_ms=invocation.duration_ms)
        if invocation.exception is not None:
            return self._exception_failure(
                request=request,
                error=invocation.exception,
                duration_ms=invocation.duration_ms,
            )

        self._active = True
        self._last_status = "success"
        self._last_error_code = None
        spoken = self._localized(
            "تم تشغيل اكتشاف العوائق.",
            "Obstacle detection enabled.",
        )
        return build_result(
            request=request,
            status="success",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "active",
                "using_fallback": False,
            },
            duration_ms=invocation.duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"health": self._adapter.describe_health()},
        )

    def stop(self, request: CapabilityRequest) -> CapabilityResult:
        if not self._adapter.is_available():
            return self._availability_failure(request=request)

        if not self._active:
            spoken = self._localized(
                "اكتشاف العوائق متوقف بالفعل.",
                "Obstacle detection is already stopped.",
            )
            return self._idempotent_success(request=request, lifecycle_state="inactive", spoken_text=spoken)

        invocation = invoke_with_timeout(self._adapter.stop_monitoring, timeout_seconds=request.timeout_seconds)
        if invocation.timed_out:
            return self._timeout_failure(request=request, duration_ms=invocation.duration_ms)
        if invocation.exception is not None:
            return self._exception_failure(
                request=request,
                error=invocation.exception,
                duration_ms=invocation.duration_ms,
            )

        self._active = False
        self._last_status = "success"
        self._last_error_code = None
        spoken = self._localized(
            "تم ايقاف اكتشاف العوائق.",
            "Obstacle detection disabled.",
        )
        return build_result(
            request=request,
            status="success",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "inactive",
                "using_fallback": False,
            },
            duration_ms=invocation.duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"health": self._adapter.describe_health()},
        )

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        if not self._adapter.is_available():
            return self._availability_failure(request=request)

        invocation = invoke_with_timeout(
            lambda: self._adapter.read_observation(request.timeout_seconds),
            timeout_seconds=request.timeout_seconds,
        )
        if invocation.timed_out:
            return self._timeout_failure(request=request, duration_ms=invocation.duration_ms)
        if invocation.exception is not None:
            return self._exception_failure(
                request=request,
                error=invocation.exception,
                duration_ms=invocation.duration_ms,
            )
        if invocation.result is None:
            return self._availability_failure(request=request, duration_ms=invocation.duration_ms)

        observation = dict(invocation.result)
        self._last_observation = observation
        self._last_status = "success"
        self._last_error_code = None

        detected = bool(observation.get("detected"))
        severity = str(observation.get("severity", "clear")).lower()
        if detected and severity in {"warning", "critical"}:
            spoken = self._localized(
                "تحذير، يوجد عائق امامك.",
                "Warning, there is an obstacle ahead.",
            )
        else:
            spoken = self._localized(
                "المسار يبدو خاليا من العوائق.",
                "Path looks clear.",
            )

        return build_result(
            request=request,
            status="success",
            spoken_text=spoken,
            payload={
                "lifecycle_state": "active" if self._active else "inactive",
                "using_fallback": False,
                "observation": observation,
            },
            duration_ms=invocation.duration_ms,
            used_fallback=False,
            backend_name="obstacle_sensor",
            metadata={"health": self._adapter.describe_health()},
        )

    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot:
        availability = "ready" if self._adapter.is_available() else "unavailable"
        lifecycle_state = "active" if self._active else "inactive"
        details: dict[str, Any] = {
            "health": self._adapter.describe_health(),
        }
        if self._last_observation is not None:
            details["last_observation"] = dict(self._last_observation)

        spoken_summary = self._localized(
            "اكتشاف العوائق يعمل." if self._active else "اكتشاف العوائق متوقف.",
            "Obstacle detection is active." if self._active else "Obstacle detection is inactive.",
        )
        return CapabilityStatusSnapshot(
            capability_id="obstacle_detection",
            lifecycle_state=lifecycle_state,
            availability=availability,
            using_fallback=False,
            backend_name="obstacle_sensor",
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=spoken_summary,
            details=details,
        )
