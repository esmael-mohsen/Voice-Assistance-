"""Capability registry and intent bindings for incremental controller migration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable

from controllers import mock_controllers as mc
from controllers.capability_contracts import (
    CapabilityDescriptor,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatusSnapshot,
    CapabilityTimeoutPolicy,
    build_request,
    build_result,
)
from controllers.obstacle_controller import (
    ObstacleCapabilityController,
    ObstacleSensorAdapter,
)
from controllers.ocr_controller import AssistiveOcrProcessController
from controllers.money_controller import AssistiveMoneyProcessController
from controllers.vision_controller import (
    AssistiveVisionAdapter,
    AssistiveVisionProcessController,
    VisionAdapter,
    VisionCapabilityController,
)
from controllers.walk_controller import WalkAssistantProcessController
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CapabilityActionBinding:
    intent_id: str
    capability_id: str
    action: str


class LegacyFunctionCapabilityHandler:
    """Adapter that wraps legacy fallback functions behind capability contract."""

    def __init__(
        self,
        *,
        capability_id: str,
        start_fn: Callable[..., Any] | None = None,
        stop_fn: Callable[..., Any] | None = None,
        execute_fn: Callable[..., Any] | None = None,
        status_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.capability_id = capability_id
        self._start_fn = start_fn
        self._stop_fn = stop_fn
        self._execute_fn = execute_fn
        self._status_fn = status_fn
        self._last_status = "success"
        self._last_error_code: str | None = None

    def _result_from_raw(self, *, request: CapabilityRequest, raw: Any, status: str = "success") -> CapabilityResult:
        payload: dict[str, Any] = {}
        spoken_text = ""
        normalized_status = status
        normalized_error_code: str | None = None
        if isinstance(raw, dict):
            payload = dict(raw)
            if isinstance(payload.get("spoken_text"), str):
                spoken_text = str(payload.pop("spoken_text"))
            if isinstance(payload.get("payload"), dict):
                nested_payload = dict(payload.pop("payload"))
                payload.update(nested_payload)
            if isinstance(payload.get("status"), str):
                normalized_status = str(payload.pop("status"))
            if isinstance(payload.get("error_code"), str):
                normalized_error_code = str(payload.pop("error_code"))
        elif isinstance(raw, str):
            spoken_text = raw
        else:
            spoken_text = str(raw)

        if not spoken_text:
            spoken_text = settings_manager.speak_localized(
                "تم تنفيذ الطلب.",
                "Request completed.",
            )

        self._last_status = normalized_status
        self._last_error_code = None if normalized_status == "success" else (normalized_error_code or "capability_failure")
        payload.setdefault("using_fallback", True)

        return build_result(
            request=request,
            status=normalized_status,
            spoken_text=spoken_text,
            payload=payload,
            error_code=None if normalized_status == "success" else self._last_error_code,
            used_fallback=True,
            backend_name="mock_fallback",
        )

    def start(self, request: CapabilityRequest) -> CapabilityResult:
        if self._start_fn is None:
            return build_result(
                request=request,
                status="rejected",
                spoken_text=settings_manager.speak_localized(
                    "هذا الاجراء غير مدعوم حاليا.",
                    "This action is not supported for this capability.",
                ),
                payload={"using_fallback": True},
                error_code="invalid_action",
                used_fallback=True,
                backend_name="mock_fallback",
            )
        return self._result_from_raw(request=request, raw=self._start_fn(**request.params))

    def stop(self, request: CapabilityRequest) -> CapabilityResult:
        if self._stop_fn is None:
            return build_result(
                request=request,
                status="rejected",
                spoken_text=settings_manager.speak_localized(
                    "هذا الاجراء غير مدعوم حاليا.",
                    "This action is not supported for this capability.",
                ),
                payload={"using_fallback": True},
                error_code="invalid_action",
                used_fallback=True,
                backend_name="mock_fallback",
            )
        return self._result_from_raw(request=request, raw=self._stop_fn(**request.params))

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        if self._execute_fn is None:
            return build_result(
                request=request,
                status="rejected",
                spoken_text=settings_manager.speak_localized(
                    "هذا الاجراء غير مدعوم حاليا.",
                    "This action is not supported for this capability.",
                ),
                payload={"using_fallback": True},
                error_code="invalid_action",
                used_fallback=True,
                backend_name="mock_fallback",
            )
        return self._result_from_raw(request=request, raw=self._execute_fn(**request.params))

    def get_status(self, request: CapabilityRequest) -> CapabilityStatusSnapshot:
        details: dict[str, Any]
        spoken_summary = settings_manager.speak_localized(
            "الحالة متاحة عبر مسار احتياطي.",
            "Status is served by fallback path.",
        )
        if self._status_fn is None:
            details = {"using_fallback": True}
        else:
            raw = self._status_fn(**request.params)
            details = dict(raw) if isinstance(raw, dict) else {"raw_status": raw}
            if isinstance(details.get("spoken_text"), str):
                spoken_summary = str(details["spoken_text"])
        details.setdefault("using_fallback", True)
        return CapabilityStatusSnapshot(
            capability_id=self.capability_id,
            lifecycle_state="active",
            availability="ready",
            using_fallback=True,
            backend_name="mock_fallback",
            last_result_status=self._last_status,
            last_error_code=self._last_error_code,
            spoken_summary=spoken_summary,
            details=details,
        )


class CapabilityRegistry:
    """Registry for capability descriptors, handlers, and intent bindings."""

    def __init__(self) -> None:
        self._descriptors: dict[str, CapabilityDescriptor] = {}
        self._handlers: dict[str, Any] = {}
        self._timeouts: dict[str, CapabilityTimeoutPolicy] = {}
        self._bindings: dict[str, CapabilityActionBinding] = {}

    def register(
        self,
        *,
        descriptor: CapabilityDescriptor,
        handler: Any,
        timeout_policy: CapabilityTimeoutPolicy,
    ) -> None:
        self._descriptors[descriptor.capability_id] = descriptor
        self._handlers[descriptor.capability_id] = handler
        self._timeouts[descriptor.capability_id] = timeout_policy

    def bind_intent(self, *, intent_id: str, capability_id: str, action: str) -> None:
        self._bindings[intent_id] = CapabilityActionBinding(
            intent_id=intent_id,
            capability_id=capability_id,
            action=action,
        )

    def has_binding(self, intent_id: str) -> bool:
        return intent_id in self._bindings

    def descriptor_for_intent(self, intent_id: str) -> CapabilityDescriptor | None:
        binding = self._bindings.get(intent_id)
        if binding is None:
            return None
        return self._descriptors.get(binding.capability_id)

    def _status_snapshot_to_result(
        self,
        *,
        request: CapabilityRequest,
        snapshot: CapabilityStatusSnapshot,
    ) -> CapabilityResult:
        spoken = snapshot.spoken_summary or settings_manager.speak_localized(
            "تم تحديث الحالة.",
            "Status updated.",
        )
        return build_result(
            request=request,
            status="success",
            spoken_text=spoken,
            payload=snapshot.to_dict(),
            used_fallback=snapshot.using_fallback,
            backend_name=snapshot.backend_name,
            metadata={"status_snapshot": True},
        )

    def _unsupported_intent_result(self, *, intent_id: str, params: dict[str, Any]) -> CapabilityResult:
        request = build_request(
            capability_id="unknown",
            action="execute",
            timeout_seconds=1.0,
            params=params,
            source_mode="runtime",
            correlation_id=intent_id,
        )
        return build_result(
            request=request,
            status="rejected",
            spoken_text=settings_manager.speak_localized(
                "هذا الامر غير مدعوم حاليا.",
                "This capability command is not supported yet.",
            ),
            payload={"intent_id": intent_id},
            error_code="unsupported_capability_intent",
            backend_name="none",
        )

    def execute_intent(
        self,
        intent_id: str,
        *,
        params: dict[str, Any] | None = None,
        source_mode: str = "runtime",
        correlation_id: str | None = None,
        allow_test_fallback: bool = False,
    ) -> CapabilityResult:
        safe_params = dict(params or {})
        binding = self._bindings.get(intent_id)
        if binding is None:
            return self._unsupported_intent_result(intent_id=intent_id, params=safe_params)

        descriptor = self._descriptors[binding.capability_id]
        timeout_policy = self._timeouts[binding.capability_id]
        handler = self._handlers[binding.capability_id]

        if not descriptor.supports(binding.action):
            request = build_request(
                capability_id=descriptor.capability_id,
                action=binding.action,
                timeout_seconds=timeout_policy.timeout_for(binding.action),
                params=safe_params,
                source_mode=source_mode,
                correlation_id=correlation_id,
            )
            return build_result(
                request=request,
                status="rejected",
                spoken_text=settings_manager.speak_localized(
                    "هذا الاجراء غير مدعوم حاليا.",
                    "This action is not supported for this capability.",
                ),
                payload={"capability_id": descriptor.capability_id},
                error_code="invalid_action",
                backend_name=descriptor.dependency_name,
            )

        request = build_request(
            capability_id=descriptor.capability_id,
            action=binding.action,
            timeout_seconds=timeout_policy.timeout_for(binding.action),
            params=safe_params,
            source_mode=source_mode,
            correlation_id=correlation_id,
        )

        if binding.action == "start":
            result = handler.start(request)
        elif binding.action == "stop":
            result = handler.stop(request)
        elif binding.action == "execute":
            result = handler.execute(request)
        else:
            snapshot = handler.get_status(request)
            result = self._status_snapshot_to_result(request=request, snapshot=snapshot)

        result_dict = result.to_dict()
        metadata = dict(result_dict.get("metadata") or {})
        metadata["migrated"] = descriptor.migrated
        metadata["backend_mode"] = descriptor.backend_mode
        metadata["fallback_policy"] = descriptor.fallback_policy
        result_dict["metadata"] = metadata

        if descriptor.migrated and descriptor.backend_mode == "real" and result_dict.get("used_fallback"):
            result_dict["status"] = "failed"
            result_dict["error_code"] = "fallback_not_allowed"
            result_dict["spoken_text"] = settings_manager.speak_localized(
                "فشل المسار الحقيقي بشكل امن بدون الرجوع لمسار تجريبي.",
                "The migrated capability failed safely without fallback.",
            )
            result_dict["payload"] = {
                "capability_id": descriptor.capability_id,
                "using_fallback": False,
            }
            result_dict["used_fallback"] = False

        if descriptor.fallback_policy == "disabled" and result_dict.get("used_fallback") and not allow_test_fallback:
            result_dict["status"] = "failed"
            result_dict["error_code"] = "fallback_not_allowed"
            result_dict["spoken_text"] = settings_manager.speak_localized(
                "لا يمكن استخدام المسار الاحتياطي لهذه الميزة بعد الترحيل.",
                "Fallback is not allowed for this migrated capability.",
            )
            result_dict["payload"] = {
                "capability_id": descriptor.capability_id,
                "using_fallback": False,
            }
            result_dict["used_fallback"] = False

        return CapabilityResult(**result_dict)

    def get_status_snapshot(self, capability_id: str) -> CapabilityStatusSnapshot:
        descriptor = self._descriptors[capability_id]
        handler = self._handlers[capability_id]
        timeout_policy = self._timeouts[capability_id]
        request = build_request(
            capability_id=capability_id,
            action="status",
            timeout_seconds=timeout_policy.timeout_for("status"),
            source_mode="runtime",
        )
        snapshot = handler.get_status(request)
        if snapshot.using_fallback and descriptor.migrated and descriptor.fallback_policy == "disabled":
            return CapabilityStatusSnapshot(
                capability_id=capability_id,
                lifecycle_state=snapshot.lifecycle_state,
                availability="degraded",
                using_fallback=False,
                backend_name=snapshot.backend_name,
                last_result_status="failed",
                last_error_code="fallback_not_allowed",
                spoken_summary=settings_manager.speak_localized(
                    "المسار الاحتياطي غير مسموح لهذه الميزة بعد الترحيل.",
                    "Fallback is not allowed for this migrated capability.",
                ),
                details={"capability_id": capability_id},
            )
        return snapshot

    def set_obstacle_adapter(self, adapter: ObstacleSensorAdapter) -> None:
        handler = self._handlers.get("obstacle_detection")
        if isinstance(handler, ObstacleCapabilityController):
            handler.set_adapter(adapter)

    def set_vision_adapter(self, adapter: VisionAdapter) -> None:
        for capability_id in ("face_recognition", "emotion_recognition"):
            handler = self._handlers.get(capability_id)
            if isinstance(handler, VisionCapabilityController):
                handler.set_adapter(adapter)


def _build_default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    obstacle_timeout = CapabilityTimeoutPolicy(
        capability_id="obstacle_detection",
        start_timeout_s=3.0,
        stop_timeout_s=3.0,
        status_timeout_s=3.0,
        execute_timeout_s=3.0,
        hard_max_s=10.0,
    )
    fallback_timeout = CapabilityTimeoutPolicy(
        capability_id="fallback_default",
        start_timeout_s=2.0,
        stop_timeout_s=2.0,
        status_timeout_s=2.0,
        execute_timeout_s=3.0,
        hard_max_s=10.0,
    )
    face_timeout = CapabilityTimeoutPolicy(
        capability_id="face_recognition",
        start_timeout_s=2.0,
        stop_timeout_s=2.0,
        status_timeout_s=1.5,
        execute_timeout_s=6.0,
        hard_max_s=10.0,
    )
    emotion_timeout = CapabilityTimeoutPolicy(
        capability_id="emotion_recognition",
        start_timeout_s=2.0,
        stop_timeout_s=2.0,
        status_timeout_s=1.5,
        execute_timeout_s=6.0,
        hard_max_s=10.0,
    )
    vision_system_timeout = CapabilityTimeoutPolicy(
        capability_id="vision_system",
        start_timeout_s=4.0,
        stop_timeout_s=6.0,
        status_timeout_s=1.0,
        execute_timeout_s=4.0,
        hard_max_s=10.0,
    )
    money_timeout = CapabilityTimeoutPolicy(
        capability_id="money_detection",
        start_timeout_s=4.0,
        stop_timeout_s=6.0,
        status_timeout_s=1.0,
        execute_timeout_s=4.0,
        hard_max_s=10.0,
    )
    ocr_timeout = CapabilityTimeoutPolicy(
        capability_id="ocr",
        start_timeout_s=4.0,
        stop_timeout_s=6.0,
        status_timeout_s=1.0,
        execute_timeout_s=4.0,
        hard_max_s=10.0,
    )

    obstacle_handler = WalkAssistantProcessController(timeout_policy=obstacle_timeout)
    ocr_handler = AssistiveOcrProcessController(timeout_policy=ocr_timeout)
    vision_adapter = AssistiveVisionAdapter()
    vision_system_handler = AssistiveVisionProcessController(timeout_policy=vision_system_timeout)
    money_handler = AssistiveMoneyProcessController(timeout_policy=money_timeout)
    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="obstacle_detection",
            display_name="Obstacle Detection",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"start", "stop", "execute", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="walk_assistant",
            timeout_policy_id="obstacle_detection",
        ),
        handler=obstacle_handler,
        timeout_policy=obstacle_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="ocr",
            display_name="OCR",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"start", "stop", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="ocr",
            timeout_policy_id="ocr",
        ),
        handler=ocr_handler,
        timeout_policy=ocr_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="money_detection",
            display_name="Money Detection",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"start", "stop", "execute", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="money_detection",
            timeout_policy_id="money_detection",
        ),
        handler=money_handler,
        timeout_policy=money_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="vision_system",
            display_name="Vision System",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"start", "stop", "execute", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="vision",
            timeout_policy_id="vision_system",
        ),
        handler=vision_system_handler,
        timeout_policy=vision_system_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="face_recognition",
            display_name="Face Recognition",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"execute", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="vision",
            timeout_policy_id="face_recognition",
        ),
        handler=VisionCapabilityController(
            capability_id="face_recognition",
            adapter=vision_adapter,
            timeout_policy=face_timeout,
        ),
        timeout_policy=face_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="emotion_recognition",
            display_name="Emotion Recognition",
            migrated=True,
            backend_mode="real",
            supported_actions=frozenset({"execute", "status"}),
            fallback_policy="disabled",
            requires_network=False,
            dependency_name="vision",
            timeout_policy_id="emotion_recognition",
        ),
        handler=VisionCapabilityController(
            capability_id="emotion_recognition",
            adapter=vision_adapter,
            timeout_policy=emotion_timeout,
        ),
        timeout_policy=emotion_timeout,
    )

    registry.register(
        descriptor=CapabilityDescriptor(
            capability_id="system_status",
            display_name="System Status",
            migrated=False,
            backend_mode="fallback",
            supported_actions=frozenset({"status"}),
            fallback_policy="unmigrated_only",
            requires_network=False,
            dependency_name="mock_fallback",
            timeout_policy_id="fallback_default",
        ),
        handler=LegacyFunctionCapabilityHandler(
            capability_id="system_status",
            status_fn=mc.fallback_system_status,
        ),
        timeout_policy=fallback_timeout,
    )

    registry.bind_intent(intent_id="enable_obstacle_detection", capability_id="obstacle_detection", action="start")
    registry.bind_intent(intent_id="disable_obstacle_detection", capability_id="obstacle_detection", action="stop")
    registry.bind_intent(intent_id="enable_vision", capability_id="vision_system", action="start")
    registry.bind_intent(intent_id="disable_vision", capability_id="vision_system", action="stop")
    registry.bind_intent(intent_id="enable_OCR", capability_id="ocr", action="start")
    registry.bind_intent(intent_id="disable_OCR", capability_id="ocr", action="stop")
    registry.bind_intent(intent_id="enable_money_detection", capability_id="money_detection", action="start")
    registry.bind_intent(intent_id="disable_money_detection", capability_id="money_detection", action="stop")
    registry.bind_intent(intent_id="recognize_face", capability_id="face_recognition", action="execute")
    registry.bind_intent(intent_id="recognize_emotion", capability_id="emotion_recognition", action="execute")
    registry.bind_intent(intent_id="get_system_status", capability_id="system_status", action="status")

    return registry


_DEFAULT_REGISTRY: CapabilityRegistry | None = None


def get_default_registry() -> CapabilityRegistry:
    global _DEFAULT_REGISTRY  # noqa: PLW0603
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = _build_default_registry()
    return _DEFAULT_REGISTRY


def reset_default_registry() -> CapabilityRegistry:
    global _DEFAULT_REGISTRY  # noqa: PLW0603
    _DEFAULT_REGISTRY = _build_default_registry()
    return _DEFAULT_REGISTRY


def set_obstacle_adapter(adapter: ObstacleSensorAdapter) -> None:
    get_default_registry().set_obstacle_adapter(adapter)


def set_vision_adapter(adapter: VisionAdapter) -> None:
    get_default_registry().set_vision_adapter(adapter)


def execute_intent(intent_id: str, *, params: dict[str, Any] | None = None) -> CapabilityResult:
    return get_default_registry().execute_intent(intent_id, params=params)


def intent_legacy_response(intent_id: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    result = execute_intent(intent_id, params=params)
    response = result.to_dict()

    payload = dict(response.get("payload") or {})
    observation = payload.get("observation") if isinstance(payload, dict) else None
    if isinstance(observation, dict):
        for key in ("distance_meters", "angle_degrees", "severity"):
            if key in observation:
                response[key] = observation[key]
    for key in ("face_id", "emotion"):
        if key in payload:
            response[key] = payload[key]

    return response


def enable_obstacle_detection() -> dict[str, Any]:
    return intent_legacy_response("enable_obstacle_detection")


def disable_obstacle_detection() -> dict[str, Any]:
    return intent_legacy_response("disable_obstacle_detection")


def enable_vision() -> dict[str, Any]:
    return intent_legacy_response("enable_vision")


def disable_vision() -> dict[str, Any]:
    return intent_legacy_response("disable_vision")


def enable_OCR() -> dict[str, Any]:
    return intent_legacy_response("enable_OCR")


def disable_OCR() -> dict[str, Any]:
    return intent_legacy_response("disable_OCR")


def enable_money_detection() -> dict[str, Any]:
    return intent_legacy_response("enable_money_detection")


def disable_money_detection() -> dict[str, Any]:
    return intent_legacy_response("disable_money_detection")


def recognize_face(store_new_face: bool = False) -> dict[str, Any]:
    return intent_legacy_response("recognize_face", params={"store_new_face": store_new_face})


def recognize_emotion(face_id: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if face_id is not None:
        params["face_id"] = face_id
    return intent_legacy_response("recognize_emotion", params=params)


def get_system_status() -> dict[str, Any]:
    return intent_legacy_response("get_system_status")
