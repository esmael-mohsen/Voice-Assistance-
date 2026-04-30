"""Unit coverage for structured command-recognition contracts."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.command_models import CommandPostProcessingOutcome, CommandRecognitionResult


def _build_runtime(
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


def test_command_recognition_result_enforces_missing_confidence_contract() -> None:
    with pytest.raises(ValueError):
        CommandRecognitionResult(
            session_id="session-1",
            recognition_path="local_first",
            provider_id="legacy",
            primary_transcript="read text",
            confidence_score=0.8,
            confidence_available=False,
            alternative_transcripts=("read text",),
            detected_language="en-US",
            latency_ms=10,
            error_code=None,
        )


def test_command_recognition_result_supports_metadata_first_shape() -> None:
    result = CommandRecognitionResult(
        session_id="session-1",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="read text",
        confidence_score=0.9,
        confidence_available=True,
        alternative_transcripts=("read text", "read the text"),
        detected_language="en-US",
        latency_ms=30,
        error_code=None,
    )
    payload = result.to_dict()
    assert payload["recognition_path"] == "local_first"
    assert payload["confidence_available"] is True
    assert payload["confidence_score"] == pytest.approx(0.9)
    assert payload["alternative_transcripts"] == ("read text", "read the text")


def test_runtime_bounded_listen_prefers_structured_listener_results(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    scripted = CommandRecognitionResult(
        session_id="session-42",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="switch to english",
        confidence_score=0.87,
        confidence_available=True,
        alternative_transcripts=("switch to english",),
        detected_language="en-US",
        latency_ms=18,
        error_code=None,
    )
    listener = listener_factory(command_result_responses=[scripted])
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

    result = runtime._listen_command_result_bounded(recognition_path="local_first")
    assert result == scripted


def test_runtime_builds_metadata_without_raw_utterance(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = _build_runtime(
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )
    recognition = CommandRecognitionResult(
        session_id="session-99",
        recognition_path="fallback",
        provider_id="legacy",
        primary_transcript="reed txt",
        confidence_score=None,
        confidence_available=False,
        alternative_transcripts=("reed txt", "read text"),
        detected_language="en-US",
        latency_ms=55,
        error_code=None,
    )
    post_processing = CommandPostProcessingOutcome(
        source_transcript="reed txt",
        normalized_transcript="read text",
        canonical_command_text="read text",
        substitution_ids=("en.read_text.reed_to_read", "en.read_text.txt_to_text"),
        language_hints=("en",),
        ambiguity_flags=(),
        post_processing_status="normalized",
    )

    metadata = runtime._build_recognition_metadata(
        recognition_result=recognition,
        post_processing=post_processing,
    )
    assert metadata["recognition_path"] == "fallback"
    assert metadata["post_processing_status"] == "normalized"
    assert "source_transcript" not in metadata


def test_command_recognition_result_accepts_phase18_source_labels() -> None:
    for source_label in ("rescue_strict_vosk", "cloud_unavailable"):
        result = CommandRecognitionResult(
            session_id=f"session-{source_label}",
            recognition_path="fallback",
            provider_id="legacy",
            primary_transcript="",
            confidence_score=None,
            confidence_available=False,
            alternative_transcripts=(),
            detected_language="en-US",
            selected_language="en-US",
            latency_ms=12,
            error_code="strict_grammar_no_match",
            recognition_source=source_label,
            failure_reason_code="strict_grammar_no_match",
        )
        payload = result.to_dict()
        assert payload["recognition_source"] == source_label
        assert payload["failure_reason_code"] == "strict_grammar_no_match"


def test_no_usable_transcript_shape_remains_field_safe() -> None:
    result = CommandRecognitionResult(
        session_id="session-no-usable",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="",
        confidence_score=None,
        confidence_available=False,
        alternative_transcripts=(),
        detected_language=None,
        selected_language="ar-EG",
        latency_ms=44,
        error_code="cloud_network_timeout",
        recognition_source="cloud_unavailable",
        failure_reason_code="cloud_network_timeout",
        field_safe=True,
        raw_user_content_present=False,
    )
    payload = result.to_dict()
    assert payload["primary_transcript"] == ""
    assert payload["error_code"] == "cloud_network_timeout"
    assert payload["field_safe"] is True
    assert payload["raw_user_content_present"] is False
