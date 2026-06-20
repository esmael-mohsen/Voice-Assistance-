"""Integration coverage for runtime command-recognition orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.command_models import CommandExecutionResult, CommandRecognitionResult
from core.speech.interfaces import LEGACY_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult


@dataclass
class _DispatchProbe:
    responses: list[Any] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, text: str, **kwargs: Any) -> Any:
        self.calls.append({"text": text, "kwargs": dict(kwargs)})
        if not self.responses:
            return CommandExecutionResult(status="success", spoken_text="ok", intent_id="get_system_status")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _recognition(
    *,
    session_id: str,
    text: str,
    recognition_path: str = "local_first",
    confidence: float | None = 0.9,
    alternatives: tuple[str, ...] = (),
    detected_language: str = "en-US",
    selected_language: str = "en-US",
    recognition_source: str = "cloud_primary",
    error_code: str | None = None,
    failure_reason_code: str | None = None,
) -> CommandRecognitionResult:
    return CommandRecognitionResult(
        session_id=session_id,
        recognition_path=recognition_path,
        provider_id="legacy",
        primary_transcript=text,
        confidence_score=confidence,
        confidence_available=confidence is not None,
        alternative_transcripts=alternatives or (text,),
        detected_language=detected_language,
        selected_language=selected_language,
        latency_ms=20,
        error_code=error_code,
        recognition_source=recognition_source,
        failure_reason_code=failure_reason_code,
    )


def _runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    listener_responses: list[CommandRecognitionResult | dict[str, Any] | None],
    dispatch_probe: _DispatchProbe,
) -> tuple[AssistantRuntime, list[Any]]:
    events: list[Any] = []
    listener = listener_factory(
        any_responses=["hi egb"],
        command_result_responses=list(listener_responses),
    )
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    tts = tts_engine_factory()
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(
                provider_id=LEGACY_PROVIDER_ID,
                display_name="legacy",
                requires_network=False,
            ),
            wake_service=wake,
            stt_service=listener,
            tts_service=tts,
        )
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=registry,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch_probe,
    )
    return runtime, events


def test_runtime_executes_high_confidence_local_first_without_fallback(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    dispatch_probe = _DispatchProbe(
        responses=[
            CommandExecutionResult(
                status="success",
                spoken_text="Obstacle enabled",
                intent_id="enable_obstacle_detection",
            )
        ]
    )
    recognition = CommandRecognitionResult(
        session_id="session-local",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_score=0.95,
        confidence_available=True,
        alternative_transcripts=("start obstacle detection",),
        detected_language="en-US",
        latency_ms=10,
        error_code=None,
    )
    runtime, events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[recognition, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=2)

    assert len(dispatch_probe.calls) == 1
    assert dispatch_probe.calls[0]["text"] == "start obstacle detection"
    telemetry_payloads = [
        event.payload["command_recognition_telemetry"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "command_recognition_telemetry" in event.payload
    ]
    assert telemetry_payloads
    assert telemetry_payloads[-1]["recognition_path"] == "local_first"
    assert telemetry_payloads[-1]["decision_outcome"] == "execute"


def test_runtime_successful_start_command_returns_to_standby_after_handoff(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    dispatch_probe = _DispatchProbe(
        responses=[
            CommandExecutionResult(
                status="success",
                spoken_text="Obstacle detection enabled",
                intent_id="enable_obstacle_detection",
                metadata={"capability_id": "obstacle_detection"},
            )
        ]
    )
    recognition = _recognition(
        session_id="session-standby-handoff",
        text="start obstacle detection",
        alternatives=("start obstacle detection",),
        recognition_source="cloud_primary",
        selected_language="en-US",
        detected_language="en-US",
    )
    runtime, events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[recognition, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=2)

    guided_payloads = [
        event.payload["guided_dialog_outcome"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "guided_dialog_outcome" in event.payload
    ]
    assert guided_payloads
    assert guided_payloads[-1]["next_runtime_state"] == "standby"

    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("obstacle detection is running now" in text.lower() for text in assistant_texts)
    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    speaking_index = status_states.index("speaking")
    assert "listening" not in status_states[speaking_index + 1 :]


def test_runtime_escalates_to_fallback_when_medium_confidence_local_result(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    dispatch_probe = _DispatchProbe(
        responses=[CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")]
    )
    local_uncertain = CommandRecognitionResult(
        session_id="session-fallback",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obsticle maybe",
        confidence_score=0.6,
        confidence_available=True,
        alternative_transcripts=("start obsticle maybe", "start obstacle detection"),
        detected_language="en-US",
        latency_ms=25,
        error_code=None,
    )
    fallback_high = CommandRecognitionResult(
        session_id="session-fallback",
        recognition_path="fallback",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_score=0.9,
        confidence_available=True,
        alternative_transcripts=("start obstacle detection",),
        detected_language="en-US",
        latency_ms=40,
        error_code=None,
    )
    runtime, events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[local_uncertain, fallback_high, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=3)

    assert len(dispatch_probe.calls) == 1
    assert dispatch_probe.calls[0]["text"] == "start obstacle detection"
    telemetry_payloads = [
        event.payload["command_recognition_telemetry"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "command_recognition_telemetry" in event.payload
    ]
    assert telemetry_payloads
    assert telemetry_payloads[-1]["recognition_path"] == "fallback"


def test_runtime_refuses_when_fallback_unavailable_and_retry_budget_exhausted(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "command_max_retry_cycles": 0,
        },
        persist=False,
    )
    dispatch_probe = _DispatchProbe()
    local_uncertain = CommandRecognitionResult(
        session_id="session-refuse",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="unknown command maybe",
        confidence_score=0.6,
        confidence_available=True,
        alternative_transcripts=("unknown command maybe", "known command"),
        detected_language="en-US",
        latency_ms=20,
        error_code=None,
    )
    fallback_failed = {
        "session_id": "session-refuse",
        "recognition_path": "fallback",
        "provider_id": "legacy",
        "primary_transcript": "",
        "confidence_score": None,
        "confidence_available": False,
        "alternative_transcripts": (),
        "detected_language": "en-US",
        "latency_ms": 30,
        "error_code": "timeout",
    }
    runtime, events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[local_uncertain, fallback_failed, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=3)

    assert dispatch_probe.calls == []
    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("cannot execute" in text.lower() for text in assistant_texts)


def test_runtime_passes_cloud_metadata_to_dispatch_context(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    dispatch_probe = _DispatchProbe(
        responses=[
            CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")
        ]
    )
    recognition = _recognition(
        session_id="session-cloud-meta",
        text="start obstacle detection",
        alternatives=("start obstacle detection",),
        recognition_source="cloud_primary",
        selected_language="en-US",
        detected_language="en-US",
    )
    runtime, _events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[recognition, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=3)

    assert len(dispatch_probe.calls) == 1
    metadata = dispatch_probe.calls[0]["kwargs"]["recognition_metadata"]
    assert metadata["recognition_source"] == "cloud_primary"
    assert metadata["selected_language"] == "en-US"
    assert metadata["failure_reason_code"] is None


def test_runtime_rescues_after_language_mismatch_without_dispatching_first_result(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    dispatch_probe = _DispatchProbe(
        responses=[
            CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")
        ]
    )
    local_mismatch = _recognition(
        session_id="session-language-mismatch",
        text="start obstacle detection",
        recognition_path="local_first",
        confidence=0.92,
        alternatives=("start obstacle detection",),
        selected_language="en-US",
        detected_language="ar-EG",
        recognition_source="cloud_primary",
    )
    fallback_recovered = _recognition(
        session_id="session-language-mismatch",
        text="start obstacle detection",
        recognition_path="fallback",
        confidence=0.9,
        alternatives=("start obstacle detection",),
        selected_language="en-US",
        detected_language="en-US",
        recognition_source="strict_vosk_fallback",
    )
    runtime, _events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[local_mismatch, fallback_recovered, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=3)

    assert len(dispatch_probe.calls) == 1
    metadata = dispatch_probe.calls[0]["kwargs"]["recognition_metadata"]
    assert metadata["recognition_path"] == "fallback"
    assert metadata["recognition_source"] == "strict_vosk_fallback"


def test_runtime_parser_rejection_triggers_fallback_and_blocks_raw_execution(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    dispatch_probe = _DispatchProbe(
        responses=[
            CommandExecutionResult(status="success", spoken_text="Done", intent_id="enable_obstacle_detection")
        ]
    )
    parser_rejected = _recognition(
        session_id="session-parser-reject",
        text="random transcript that is not command shaped",
        recognition_path="local_first",
        confidence=0.95,
        alternatives=("random transcript that is not command shaped",),
        selected_language="en-US",
        detected_language="en-US",
        recognition_source="cloud_primary",
    )
    fallback_recovered = _recognition(
        session_id="session-parser-reject",
        text="start obstacle detection",
        recognition_path="fallback",
        confidence=0.91,
        alternatives=("start obstacle detection",),
        selected_language="en-US",
        detected_language="en-US",
        recognition_source="rescue_strict_vosk",
    )
    runtime, _events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[parser_rejected, fallback_recovered, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=3)

    assert len(dispatch_probe.calls) == 1
    assert dispatch_probe.calls[0]["text"] == "start obstacle detection"
    assert all("random transcript" not in call["text"] for call in dispatch_probe.calls)


def test_runtime_protected_cloud_and_fallback_commands_require_confirmation(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    dispatch_probe = _DispatchProbe()
    cloud_protected = _recognition(
        session_id="session-protected",
        text="reset settings",
        recognition_path="local_first",
        confidence=0.98,
        alternatives=("reset settings", "start system"),
        selected_language="en-US",
        detected_language="en-US",
        recognition_source="cloud_primary",
    )
    fallback_protected = _recognition(
        session_id="session-protected-fallback",
        text="reset settings",
        recognition_path="fallback",
        confidence=0.96,
        alternatives=("reset settings", "start system"),
        selected_language="en-US",
        detected_language="en-US",
        recognition_source="strict_vosk_fallback",
    )
    runtime, events = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        listener_responses=[cloud_protected, fallback_protected, None],
        dispatch_probe=dispatch_probe,
    )
    runtime.run_forever(max_cycles=4)

    assert dispatch_probe.calls
    assert all(
        call["kwargs"]["runtime_context"]["confidence_decision_action"] == "confirm"
        for call in dispatch_probe.calls
    )
    telemetry_payloads = [
        event.payload["command_recognition_telemetry"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "command_recognition_telemetry" in event.payload
    ]
    assert telemetry_payloads
    assert any(payload["decision_outcome"] == "confirm" for payload in telemetry_payloads)
