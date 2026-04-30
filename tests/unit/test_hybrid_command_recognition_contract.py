"""Unit coverage for hybrid local-first/rescue recognition contracts."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeMode
from core.command_models import (
    CommandRecognitionResult,
    HybridRecognitionResult,
)
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


def test_command_recognition_result_accepts_rescue_path_with_metadata() -> None:
    result = CommandRecognitionResult(
        session_id="session-1",
        recognition_path="rescue",
        provider_id="legacy",
        primary_transcript="read text",
        confidence_score=0.81,
        confidence_available=True,
        alternative_transcripts=("read text", "read the text"),
        detected_language="en-US",
        language_candidates=("en-US", "ar-EG"),
        profile_id="command.default",
        dictionary_bias_applied=True,
        dictionary_bias_mode="command_inventory",
        closed_vocabulary_id=None,
        endpoint_quality_hints=("low_trailing_silence",),
        latency_ms=120,
        error_code=None,
    )
    assert result.recognition_path == "rescue"
    assert result.dictionary_bias_applied is True
    assert result.endpoint_quality_hints == ("low_trailing_silence",)


def test_hybrid_result_contract_requires_primary_transcript_when_successful() -> None:
    with pytest.raises(ValueError):
        HybridRecognitionResult(
            session_id="session-2",
            capture_attempt_id="cap-1",
            recognition_path="local_first",
            provider_id="legacy_vosk",
            profile_id="command.default",
            primary_transcript="",
            confidence_available=False,
            confidence_score=None,
            latency_ms=90,
            error_code=None,
        )


def test_runtime_recognition_metadata_includes_phase14_fields(
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
        session_id="session-3",
        recognition_path="rescue",
        provider_id="legacy",
        primary_transcript="read text",
        confidence_score=0.8,
        confidence_available=True,
        alternative_transcripts=("read text",),
        detected_language="en-US",
        language_candidates=("en-US", "ar-EG"),
        capture_attempt_id="cap-3",
        profile_id="command.default",
        dictionary_bias_applied=True,
        dictionary_bias_mode="command_inventory",
        endpoint_quality_hints=("possible_clipped_end",),
        qualification_profile_id="default",
        latency_ms=100,
        error_code=None,
    )
    post = process_command_transcript(recognition.primary_transcript)
    metadata = runtime._build_recognition_metadata(recognition_result=recognition, post_processing=post)
    assert metadata["recognition_path"] == "rescue"
    assert metadata["capture_attempt_id"] == "cap-3"
    assert metadata["profile_id"] == "command.default"
    assert metadata["dictionary_bias_applied"] is True

