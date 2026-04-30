"""Contract tests for command safety evaluation policy behavior."""

from __future__ import annotations

from core import parser
from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.command_models import CommandRecognitionResult, ConfidenceDecisionPolicy
from core.command_post_processing import process_command_transcript


def _runtime(
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> AssistantRuntime:
    listener = listener_factory()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,  # noqa: ARG005
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text, **_kwargs: None,
    )
    runtime._listener = listener
    runtime._provider_state.session_provider = "legacy"
    return runtime


def test_protected_high_confidence_command_requires_confirmation(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s-safe-1",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="stop system",
        confidence_score=0.97,
        confidence_available=True,
        alternative_transcripts=("stop system",),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=15,
        error_code=None,
        recognition_source="cloud_primary",
    )
    parsed = parser.parse_command("stop system")
    post = process_command_transcript("stop system")
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_band == "high"
    assert decision.decision_action == "confirm"
    assert decision.confirmation_required is True


def test_parser_rejected_high_confidence_never_executes(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s-safe-2",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="this is not a command",
        confidence_score=0.93,
        confidence_available=True,
        alternative_transcripts=("this is not a command",),
        detected_language="en-US",
        selected_language="en-US",
        latency_ms=20,
        error_code=None,
        recognition_source="cloud_primary",
    )
    parsed = None
    post = process_command_transcript("this is not a command")
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_action in {"fallback", "retry", "refuse"}
    assert decision.reason_code in {"parser_rejected_recovery", "retry_required", "retry_exhausted"}


def test_language_mismatch_routes_to_recovery_not_execution(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="s-safe-3",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="start obstacle detection",
        confidence_score=0.91,
        confidence_available=True,
        alternative_transcripts=("start obstacle detection",),
        detected_language="ar-EG",
        selected_language="en-US",
        latency_ms=19,
        error_code=None,
        recognition_source="cloud_primary",
    )
    parsed = parser.parse_command("start obstacle detection")
    post = process_command_transcript("start obstacle detection")
    decision = runtime._evaluate_confidence_decision(
        recognition_result=recognition,
        post_processing=post,
        parsed_intent=parsed,
        policy=ConfidenceDecisionPolicy(),
        retry_count=0,
    )
    assert decision.decision_action in {"fallback", "retry", "refuse"}
    assert decision.reason_code in {"language_mismatch_recovery", "retry_required", "retry_exhausted"}
