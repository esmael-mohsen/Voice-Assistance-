"""Integration coverage for local-first and rescue recognition orchestration."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.command_models import CommandExecutionResult
from core.wake_word import WakeAction, WakeResult


def test_runtime_escalates_to_rescue_path_on_uncertain_local_result(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "command_rescue_enabled": True},
        persist=False,
    )
    listener = listener_factory(
        any_responses=["hi egb"],
        command_result_responses=[
            {
                "session_id": "hybrid-1",
                "recognition_path": "local_first",
                "provider_id": "legacy",
                "primary_transcript": "start obsticle maybe",
                "confidence_available": True,
                "confidence_score": 0.60,
                "alternative_transcripts": ("start obsticle maybe", "start obstacle detection"),
                "detected_language": "en-US",
                "latency_ms": 35,
                "error_code": None,
            },
            {
                "session_id": "hybrid-1",
                "recognition_path": "rescue",
                "provider_id": "legacy",
                "primary_transcript": "start obstacle detection",
                "confidence_available": True,
                "confidence_score": 0.92,
                "alternative_transcripts": ("start obstacle detection",),
                "detected_language": "en-US",
                "latency_ms": 90,
                "error_code": None,
            },
            None,
        ],
    )
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(
        responses=[CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")]
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    assert dispatch.calls
    paths = [call.get("recognition_path") for call in listener.listen_command_result_calls]
    assert paths[:2] == ["local_first", "rescue"]


def test_runtime_respects_rescue_disabled_policy_with_truthful_refusal(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "command_fallback_enabled": False,
            "command_rescue_enabled": False,
            "command_max_retry_cycles": 0,
        },
        persist=False,
    )
    events = []
    listener = listener_factory(
        any_responses=["hi egb"],
        command_result_responses=[
            {
                "session_id": "hybrid-2",
                "recognition_path": "local_first",
                "provider_id": "legacy",
                "primary_transcript": "unknown maybe",
                "confidence_available": True,
                "confidence_score": 0.58,
                "alternative_transcripts": ("unknown maybe", "known command"),
                "detected_language": "en-US",
                "latency_ms": 30,
                "error_code": None,
            },
            None,
        ],
    )
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    assert dispatch.calls == []
    assert listener.listen_command_result_calls
    assert all(call.get("recognition_path") != "rescue" for call in listener.listen_command_result_calls)
    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("cannot execute" in text.lower() for text in assistant_texts)
