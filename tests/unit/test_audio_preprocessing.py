"""Unit coverage for audio preprocessing and endpointing helpers."""

from __future__ import annotations

from core.audio.endpointing import derive_endpoint_quality_hints, should_trigger_bounded_relisten
from core.audio.preprocessing import preprocess_audio_for_capture
from core.audio.profiles import select_capture_profile


class _DummyAudio:
    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def get_raw_data(self, **_kwargs):  # noqa: ANN003
        return self._raw


def test_preprocessing_reports_duration_and_loudness() -> None:
    profile = select_capture_profile(usage_mode="command")
    # 16-bit mono PCM at 16 kHz ~ 100 ms.
    samples = (b"\x10\x00" * 1600)
    outcome = preprocess_audio_for_capture(_DummyAudio(samples), profile=profile)
    assert outcome.raw_duration_ms >= 95
    assert outcome.processed_duration_ms == outcome.raw_duration_ms
    assert outcome.measured_loudness_dbfs is not None


def test_endpoint_hints_include_clipping_signals() -> None:
    profile = select_capture_profile(usage_mode="command")
    hints = derive_endpoint_quality_hints(
        vad_profile={"leading_silence_ms": 30, "trailing_silence_ms": 40, "speech_ratio": 0.2},
        profile=profile,
        clipping_start_suspected=True,
        clipping_end_suspected=True,
    )
    assert "possible_clipped_start" in hints
    assert "possible_clipped_end" in hints
    assert "low_trailing_silence" in hints


def test_bounded_relisten_triggers_once_for_clipping_hints() -> None:
    should_retry = should_trigger_bounded_relisten(
        attempt_index=0,
        max_relisten_attempts=1,
        clipping_start_suspected=False,
        clipping_end_suspected=True,
        endpoint_quality_hints=("low_trailing_silence",),
        relisten_enabled=True,
    )
    assert should_retry is True

    should_retry_again = should_trigger_bounded_relisten(
        attempt_index=1,
        max_relisten_attempts=1,
        clipping_start_suspected=True,
        clipping_end_suspected=False,
        endpoint_quality_hints=(),
        relisten_enabled=True,
    )
    assert should_retry_again is False

