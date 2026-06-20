"""Integration tests for capability refactor runtime behavior."""

from __future__ import annotations

from controllers import capability_registry as cap_registry
from controllers.capability_contracts import CapabilityStatusSnapshot, build_result
from core import resolver
from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.dispatcher import dispatch
from core.wake_word import WakeAction, WakeResult


def setup_function() -> None:
    resolver.reset_session_context()
    cap_registry.reset_default_registry()


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


def test_dispatch_obstacle_result_includes_capability_metadata() -> None:
    result = dispatch("start obstacle detection")
    assert result.status == "success"
    assert result.intent_id == "enable_obstacle_detection"
    assert result.payload is not None
    assert result.payload.get("capability_id") == "obstacle_detection"
    assert result.payload.get("used_fallback") is False


def test_dispatch_ocr_uses_real_path_without_fallback() -> None:
    cap_registry.get_default_registry()._handlers["ocr"] = _FakeOcrHandler()  # noqa: SLF001

    result = dispatch("start ocr")
    assert result.status == "success"
    assert result.payload is not None
    assert result.payload.get("capability_id") == "ocr"
    assert result.payload.get("used_fallback") is False


def _run_mode_once(
    mode: RuntimeMode,
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
):
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "voice_gender": "female", "speech_speed": 1.0},
        persist=False,
    )
    events = []
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start obstacle detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])

    runtime = AssistantRuntime(
        mode=mode,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)
    return events


def test_gui_and_console_parity_for_obstacle_flow(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    gui_events = _run_mode_once(
        RuntimeMode.GUI,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    cap_registry.reset_default_registry()
    resolver.reset_session_context()
    console_events = _run_mode_once(
        RuntimeMode.CONSOLE,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )

    gui_assistant = [event.payload["text"] for event in gui_events if event.type == RuntimeEventType.ASSISTANT]
    console_assistant = [event.payload["text"] for event in console_events if event.type == RuntimeEventType.ASSISTANT]
    assert gui_assistant == console_assistant


def test_dispatch_reports_safe_failure_when_obstacle_backend_fails(obstacle_adapter_factory) -> None:
    cap_registry.set_obstacle_adapter(obstacle_adapter_factory(available=True, fail_on_start=True))
    result = dispatch("start obstacle detection")
    assert result.status == "failed"
    assert result.error_code in {"capability_failure", "resolver_execution_error"}
