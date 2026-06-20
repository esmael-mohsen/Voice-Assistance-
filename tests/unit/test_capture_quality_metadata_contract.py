"""Unit coverage for capture-quality metadata contract."""

from __future__ import annotations

from core.stt import VoiceListener


class _DummyAudio:
    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def get_raw_data(self, **_kwargs):  # noqa: ANN003
        return self._raw


def test_listen_command_result_emits_capture_metadata_contract_fields() -> None:
    listener = VoiceListener(default_language="en-US", retries=0)
    listener.listen_audio = lambda **_kwargs: _DummyAudio(b"\x08\x00" * 3200)  # type: ignore[method-assign]
    listener._recognize_candidates = (  # type: ignore[method-assign]
        lambda _audio, **_kwargs: (
            "read text",
            "en-US",
            ("read text", "read the text"),
            0.86,
        )
    )
    listener._analyze_vad_profile = lambda _audio: {  # type: ignore[method-assign]
        "speech_ratio": 0.22,
        "leading_silence_ms": 80,
        "trailing_silence_ms": 75,
        "boundary_clipped": True,
    }

    result = listener.listen_command_result(timeout_s=2, phrase_time_limit_s=2, usage_mode="command")
    assert result is not None
    assert result.error_code is None
    assert result.capture_attempt_id
    assert result.profile_id == "command.default"
    assert result.dictionary_bias_applied is True
    assert result.endpoint_quality_hints
    assert result.capture_attempt is not None
    assert result.capture_attempt.attempt_index == 0


def test_listen_command_result_marks_bounded_relisten_when_clipping_detected() -> None:
    listener = VoiceListener(default_language="en-US", retries=1)
    listener.listen_audio = lambda **_kwargs: _DummyAudio(b"\x08\x00" * 3200)  # type: ignore[method-assign]
    listener._recognize_candidates = (  # type: ignore[method-assign]
        lambda _audio, **_kwargs: (
            "start obstacle",
            "en-US",
            ("start obstacle",),
            0.72,
        )
    )
    listener._analyze_vad_profile = lambda _audio: {  # type: ignore[method-assign]
        "speech_ratio": 0.18,
        "leading_silence_ms": 25,
        "trailing_silence_ms": 25,
        "boundary_clipped": True,
    }

    result = listener.listen_command_result(
        timeout_s=2,
        phrase_time_limit_s=2,
        usage_mode="command",
        recovery_prompt_surface="runtime.capture.retry_short",
    )
    assert result is not None
    assert result.capture_attempt is not None
    assert result.capture_attempt.relisten_triggered is True
    assert result.capture_attempt.recovery_prompt_surface == "runtime.capture.retry_short"
