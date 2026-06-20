"""Smoke checks aligned with capability-refactor quickstart scenarios."""

from __future__ import annotations

from controllers import capability_registry as cap_registry
from controllers.capability_contracts import CapabilityStatusSnapshot, CapabilityTimeoutPolicy, build_result
from core import resolver
from core.dispatcher import dispatch


def setup_function() -> None:
    resolver.reset_session_context()
    cap_registry.reset_default_registry()


class _FakeMoneyHandler:
    def start(self, request):
        return build_result(
            request=request,
            status="success",
            spoken_text="The money detection project is now running.",
            payload={"running": True, "capability_id": "money_detection"},
            used_fallback=False,
            backend_name="egy_money_detection_process",
        )

    def stop(self, request):
        return build_result(
            request=request,
            status="success",
            spoken_text="The money detection project has been stopped.",
            payload={"running": False, "capability_id": "money_detection"},
            used_fallback=False,
            backend_name="egy_money_detection_process",
        )

    def execute(self, request):
        return self.start(request)

    def get_status(self, request):
        return CapabilityStatusSnapshot(
            capability_id=request.capability_id,
            lifecycle_state="active",
            availability="ready",
            using_fallback=False,
            backend_name="egy_money_detection_process",
            last_result_status="success",
            spoken_summary="Money detection is running.",
            details={"running": True},
        )


class _FakeOcrHandler:
    def start(self, request):
        return build_result(
            request=request,
            status="success",
            spoken_text="OCR text reading project is now running.",
            payload={"running": True, "capability_id": "ocr"},
            used_fallback=False,
            backend_name="blind_ocr_assistant_process",
        )

    def stop(self, request):
        return build_result(
            request=request,
            status="success",
            spoken_text="OCR text reading project has been stopped.",
            payload={"running": False, "capability_id": "ocr"},
            used_fallback=False,
            backend_name="blind_ocr_assistant_process",
        )

    def execute(self, request):
        return self.start(request)

    def get_status(self, request):
        return CapabilityStatusSnapshot(
            capability_id=request.capability_id,
            lifecycle_state="active",
            availability="ready",
            using_fallback=False,
            backend_name="blind_ocr_assistant_process",
            last_result_status="success",
            spoken_summary="OCR text reading is running.",
            details={"running": True},
        )


class _FakeVisionHandler:
    def __init__(self, *, capability_id: str) -> None:
        self._capability_id = capability_id

    def start(self, request):
        return build_result(
            request=request,
            status="rejected",
            spoken_text="Unsupported action.",
            payload={"capability_id": self._capability_id},
            error_code="invalid_action",
            used_fallback=False,
            backend_name="assistive_vision_system",
        )

    def stop(self, request):
        return self.start(request)

    def execute(self, request):
        payload = {"capability_id": self._capability_id}
        if self._capability_id == "face_recognition":
            payload.update({"face_id": "Face_Test", "allow_emotion_follow_up": True})
            spoken = "Face Face_Test recognized."
        else:
            payload.update({"face_id": "Face_Test", "emotion": "Happy"})
            spoken = "Detected a happy emotion for Face_Test."
        return build_result(
            request=request,
            status="success",
            spoken_text=spoken,
            payload=payload,
            used_fallback=False,
            backend_name="assistive_vision_system",
        )

    def get_status(self, request):
        return CapabilityStatusSnapshot(
            capability_id=request.capability_id,
            lifecycle_state="active",
            availability="ready",
            using_fallback=False,
            backend_name="assistive_vision_system",
            last_result_status="success",
            spoken_summary="Vision capability ready.",
            details={"ready": True},
        )


def test_quickstart_validation_matrix_basics() -> None:
    registry = cap_registry.get_default_registry()
    registry._handlers["ocr"] = _FakeOcrHandler()  # noqa: SLF001
    registry._handlers["money_detection"] = _FakeMoneyHandler()  # noqa: SLF001
    registry._handlers["face_recognition"] = _FakeVisionHandler(capability_id="face_recognition")  # noqa: SLF001
    registry._handlers["emotion_recognition"] = _FakeVisionHandler(capability_id="emotion_recognition")  # noqa: SLF001
    scenarios = [
        ("start obstacle detection", "success"),
        ("stop obstacle detection", "success"),
        ("start ocr", "success"),
        ("start money detection", "success"),
        ("recognize face", "success"),
        ("recognize emotion", "success"),
        ("get status", "success"),
    ]
    for text, expected in scenarios:
        result = dispatch(text)
        assert result.status == expected


def test_migrated_obstacle_timeout_is_safe_and_bounded(obstacle_adapter_factory) -> None:
    registry = cap_registry.get_default_registry()
    registry._timeouts["obstacle_detection"] = CapabilityTimeoutPolicy(  # noqa: SLF001
        capability_id="obstacle_detection",
        start_timeout_s=0.05,
        stop_timeout_s=0.05,
        status_timeout_s=0.05,
        execute_timeout_s=0.05,
        hard_max_s=10.0,
    )
    cap_registry.set_obstacle_adapter(obstacle_adapter_factory(available=True, start_delay_s=0.2))

    result = dispatch("start obstacle detection")
    assert result.status == "failed"
    assert result.error_code == "capability_timeout"
    assert result.payload is not None
    assert result.payload.get("used_fallback") is False


def test_migrated_process_capabilities_use_real_paths_without_fallback() -> None:
    cap_registry.get_default_registry()._handlers["ocr"] = _FakeOcrHandler()  # noqa: SLF001
    cap_registry.get_default_registry()._handlers["money_detection"] = _FakeMoneyHandler()  # noqa: SLF001
    ocr = dispatch("start ocr")
    money = dispatch("start money detection")

    assert ocr.payload is not None and ocr.payload.get("used_fallback") is False
    assert money.payload is not None and money.payload.get("used_fallback") is False


def test_runtime_recovers_after_capability_failure(obstacle_adapter_factory) -> None:
    cap_registry.set_obstacle_adapter(obstacle_adapter_factory(available=True, fail_on_start=True))
    failed = dispatch("start obstacle detection")
    next_result = dispatch("switch to english")

    assert failed.status == "failed"
    assert next_result.status == "success"
