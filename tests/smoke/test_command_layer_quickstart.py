"""Smoke validation for command layer hardening quickstart paths."""

from __future__ import annotations

import time

from controllers import capability_registry as cap_registry
from controllers.capability_contracts import CapabilityStatusSnapshot, build_result
from core import resolver
from core.dispatcher import dispatch


def setup_function() -> None:
    resolver.reset_session_context()


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


def test_curated_regression_success_rate_and_safe_failures() -> None:
    registry = cap_registry.get_default_registry()
    registry._handlers["ocr"] = _FakeOcrHandler()  # noqa: SLF001
    registry._handlers["money_detection"] = _FakeMoneyHandler()  # noqa: SLF001
    registry._handlers["face_recognition"] = _FakeVisionHandler(capability_id="face_recognition")  # noqa: SLF001
    registry._handlers["emotion_recognition"] = _FakeVisionHandler(capability_id="emotion_recognition")  # noqa: SLF001
    curated = [
        ("start obstacle detection", "success"),
        ("stop obstacle detection", "success"),
        ("start ocr", "success"),
        ("recognize face", "success"),
        ("recognize emotion", "success"),
        ("start money detection", "success"),
        ("switch to english", "success"),
        ("male voice", "success"),
        ("stop system", "confirmation_required"),
        ("set language", "clarification_required"),
        ("random unrelated phrase", "rejected"),
    ]

    passed = 0
    for text, expected in curated:
        result = dispatch(text)
        if result.status == expected:
            passed += 1

    success_rate = passed / len(curated)
    assert success_rate >= 0.9


def test_protected_near_match_has_zero_unintended_activation() -> None:
    risky_near_matches = [
        "stop assistant now",
        "reset my mood",
        "stob systm",
    ]
    for text in risky_near_matches:
        result = dispatch(text)
        assert not (result.intent_id in {"stop_system", "reset_settings"} and result.status == "success")


def test_dispatch_baseline_capture_regression_smoke() -> None:
    start = time.perf_counter()
    result = dispatch("start obstacle detection")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.status == "success"
    assert elapsed_ms > 0
    # Generous smoke threshold to catch catastrophic regressions only.
    assert elapsed_ms < 1000


def test_phase9_protected_confirmation_phrase_families_smoke() -> None:
    confirmation = dispatch("stop system")
    assert confirmation.status == "confirmation_required"

    affirmative = dispatch("yes please")
    assert affirmative.status == "success"
    assert affirmative.intent_id == "stop_system"

    second_confirmation = dispatch("reset settings")
    assert second_confirmation.status == "confirmation_required"
    cancelled = dispatch("yes cancel")
    assert cancelled.status == "rejected"
    assert cancelled.error_code == "confirmation_declined"


def test_phase9_clarification_bounded_retry_smoke() -> None:
    first = dispatch("set language")
    second = dispatch("unknown option")
    third = dispatch("still unknown")

    assert first.status == "clarification_required"
    assert second.status == "clarification_required"
    assert third.status == "failed"
    assert third.error_code == "clarification_failed"


def test_phase13_dispatch_accepts_canonicalized_command_text_smoke() -> None:
    result = dispatch(
        "reed txt",
        canonical_command_text="read text",
        recognition_metadata={"recognition_path": "local_first"},
    )
    assert result.metadata["canonical_command_text"] == "read text"
