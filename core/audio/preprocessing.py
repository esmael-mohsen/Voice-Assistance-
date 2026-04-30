"""Lightweight preprocessing helpers for runtime-safe command capture."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.command_models import AudioCaptureProfile


@dataclass(frozen=True)
class PreprocessingOutcome:
    raw_duration_ms: int
    processed_duration_ms: int
    measured_loudness_dbfs: float | None
    gain_applied_db: float
    sample_rate_hz: int
    mono_required: bool
    high_pass_hz: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_duration_ms": self.raw_duration_ms,
            "processed_duration_ms": self.processed_duration_ms,
            "measured_loudness_dbfs": self.measured_loudness_dbfs,
            "gain_applied_db": self.gain_applied_db,
            "sample_rate_hz": self.sample_rate_hz,
            "mono_required": self.mono_required,
            "high_pass_hz": self.high_pass_hz,
        }


def _duration_ms_from_pcm(
    pcm: bytes,
    *,
    sample_rate_hz: int,
    sample_width_bytes: int = 2,
    channels: int = 1,
) -> int:
    if not pcm:
        return 0
    frame_size = max(1, sample_width_bytes * max(1, channels))
    total_frames = len(pcm) / frame_size
    return max(0, int(round((total_frames / max(1, sample_rate_hz)) * 1000)))


def _estimate_loudness_dbfs(pcm: bytes) -> float | None:
    if not pcm:
        return None
    if len(pcm) < 2:
        return None
    sample_count = len(pcm) // 2
    if sample_count <= 0:
        return None
    accumulator = 0.0
    for index in range(sample_count):
        start = index * 2
        sample = int.from_bytes(pcm[start : start + 2], byteorder="little", signed=True)
        accumulator += float(sample * sample)
    rms = math.sqrt(accumulator / sample_count)
    if rms <= 0:
        return None
    return round(20.0 * math.log10(rms / 32767.0), 2)


def preprocess_audio_for_capture(
    audio: Any,
    *,
    profile: AudioCaptureProfile,
) -> PreprocessingOutcome:
    """Derive preprocessing metadata without storing user audio."""
    get_raw_data = getattr(audio, "get_raw_data", None)
    pcm = b""
    if callable(get_raw_data):
        try:
            pcm = get_raw_data(
                convert_rate=profile.sample_rate_hz,
                convert_width=2,
            )
        except Exception:  # noqa: BLE001
            pcm = b""
    raw_duration_ms = _duration_ms_from_pcm(
        pcm,
        sample_rate_hz=profile.sample_rate_hz,
        sample_width_bytes=2,
        channels=1 if profile.mono_required else 2,
    )
    measured_dbfs = _estimate_loudness_dbfs(pcm)
    gain_applied_db = 0.0
    if measured_dbfs is not None:
        gain_applied_db = round(profile.target_loudness_dbfs - measured_dbfs, 2)
    # Runtime keeps capture metadata only; processed audio remains ephemeral.
    processed_duration_ms = raw_duration_ms
    return PreprocessingOutcome(
        raw_duration_ms=raw_duration_ms,
        processed_duration_ms=processed_duration_ms,
        measured_loudness_dbfs=measured_dbfs,
        gain_applied_db=gain_applied_db,
        sample_rate_hz=profile.sample_rate_hz,
        mono_required=profile.mono_required,
        high_pass_hz=profile.high_pass_hz,
    )

