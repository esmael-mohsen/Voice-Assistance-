"""Integration coverage for closed-vocabulary STT and constrained retry behavior."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.command_models import CommandRecognitionResult


def _runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
):
    events = []
    listener = listener_factory()
    dispatch = dispatch_spy_factory()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=dispatch,
    )
    runtime._initialize_runtime()
    runtime._active = True
    return runtime, events, dispatch


def test_closed_vocabulary_out_of_set_triggers_single_constrained_retry(
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
            "closed_vocabulary_retry_limit": 1,
        },
        persist=False,
    )
    runtime, events, dispatch = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
    )
    recognition = CommandRecognitionResult(
        session_id=runtime.session.session_id,
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="maybe later",
        confidence_available=True,
        confidence_score=0.9,
        alternative_transcripts=("maybe later",),
        detected_language="en-US",
        profile_id="confirmation.default",
        dictionary_bias_applied=True,
        dictionary_bias_mode="closed_choice",
        closed_vocabulary_id="confirmation.yes_no",
        latency_ms=20,
        error_code=None,
    )
    runtime._handle_active_input("maybe later", recognition_result=recognition)

    assert dispatch.calls == []
    assert runtime._confidence_retry_cycles == 1
    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("available options" in text.lower() for text in assistant_texts)
    guided_payloads = [
        event.payload["guided_dialog_outcome"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "guided_dialog_outcome" in event.payload
    ]
    assert guided_payloads
    assert guided_payloads[-1]["status"] == "retry_required"
    assert guided_payloads[-1]["error_code"] == "out_of_domain_answer"


def test_closed_vocabulary_retry_budget_exhaustion_returns_safe_refusal(
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
            "closed_vocabulary_retry_limit": 1,
        },
        persist=False,
    )
    runtime, events, dispatch = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
    )
    runtime._confidence_retry_cycles = 1
    recognition = CommandRecognitionResult(
        session_id=runtime.session.session_id,
        recognition_path="rescue",
        provider_id="legacy",
        primary_transcript="maybe later",
        confidence_available=True,
        confidence_score=0.9,
        alternative_transcripts=("maybe later",),
        detected_language="en-US",
        profile_id="confirmation.default",
        dictionary_bias_applied=True,
        dictionary_bias_mode="closed_choice",
        closed_vocabulary_id="confirmation.yes_no",
        latency_ms=25,
        error_code=None,
    )
    runtime._handle_active_input("maybe later", recognition_result=recognition)

    assert dispatch.calls == []
    assert runtime._confidence_retry_cycles == 0
    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("safe option" in text.lower() for text in assistant_texts)
    guided_payloads = [
        event.payload["guided_dialog_outcome"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "guided_dialog_outcome" in event.payload
    ]
    assert guided_payloads
    assert guided_payloads[-1]["status"] == "graceful_exit"
    assert guided_payloads[-1]["error_code"] == "retry_exhausted"


def test_closed_vocabulary_allows_global_safety_preemption_for_interrupt_commands(
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
            "closed_vocabulary_retry_limit": 1,
        },
        persist=False,
    )
    runtime, events, dispatch = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
    )
    recognition = CommandRecognitionResult(
        session_id=runtime.session.session_id,
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="stop now",
        confidence_available=True,
        confidence_score=0.95,
        alternative_transcripts=("stop now",),
        detected_language="en-US",
        profile_id="confirmation.default",
        dictionary_bias_applied=True,
        dictionary_bias_mode="closed_choice",
        closed_vocabulary_id="confirmation.yes_no",
        latency_ms=15,
        error_code=None,
    )
    runtime._handle_active_input("stop now", recognition_result=recognition)

    assert dispatch.calls == []
    recovery_payloads = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("recovery_trigger") == "interrupt"
    ]
    assert recovery_payloads
