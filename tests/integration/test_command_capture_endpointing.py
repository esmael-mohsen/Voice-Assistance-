"""Integration coverage for capture-profile and endpoint-aware command intake."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.command_models import CommandExecutionResult
from core.wake_word import WakeAction, WakeResult


def test_runtime_bounded_listen_passes_capture_profile_context_to_listener(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "command_capture_profile_id": "command.default",
            "speech_qualification_profile": "default",
            "enable_dictionary_bias": True,
        },
        persist=False,
    )
    listener = listener_factory(
        command_result_responses=[
            {
                "session_id": "capture-session",
                "recognition_path": "local_first",
                "provider_id": "legacy",
                "primary_transcript": "start obstacle detection",
                "confidence_available": True,
                "confidence_score": 0.9,
                "alternative_transcripts": ("start obstacle detection",),
                "detected_language": "en-US",
                "latency_ms": 20,
                "error_code": None,
            }
        ]
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text, **_kwargs: None,
    )
    runtime._initialize_runtime()

    result = runtime._listen_command_result_bounded(recognition_path="local_first")
    assert result is not None
    assert listener.listen_command_result_calls
    last_call = listener.listen_command_result_calls[-1]
    assert last_call["usage_mode"] == "command"
    assert last_call["capture_profile_id"] == "command.default"
    assert last_call["qualification_profile_id"] == "default"


def test_runtime_dispatch_receives_endpoint_quality_metadata(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    events = []
    listener = listener_factory(
        any_responses=["hi egb"],
        command_result_responses=[
            {
                "session_id": "session-endpoint",
                "recognition_path": "local_first",
                "provider_id": "legacy",
                "primary_transcript": "start obstacle detection",
                "confidence_available": True,
                "confidence_score": 0.91,
                "alternative_transcripts": ("start obstacle detection",),
                "detected_language": "en-US",
                "latency_ms": 18,
                "profile_id": "command.default",
                "capture_attempt_id": "cap-77",
                "endpoint_quality_hints": ("low_trailing_silence",),
                "error_code": None,
            },
            None,
        ],
    )
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch_calls: list[dict[str, object]] = []

    def _dispatch(text: str, **kwargs):
        dispatch_calls.append({"text": text, "kwargs": dict(kwargs)})
        return CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake,
        dispatcher=_dispatch,
    )

    runtime.run_forever(max_cycles=3)

    assert dispatch_calls
    metadata = dispatch_calls[0]["kwargs"]["recognition_metadata"]
    assert metadata["capture_attempt_id"] == "cap-77"
    assert "low_trailing_silence" in metadata["endpoint_quality_hints"]
