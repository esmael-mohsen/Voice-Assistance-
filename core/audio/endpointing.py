"""Endpoint-quality and capture-attempt helpers."""

from __future__ import annotations

from uuid import uuid4

from core.command_models import AudioCaptureAttempt, AudioCaptureProfile


def derive_endpoint_quality_hints(
    *,
    vad_profile: dict[str, float | int | bool] | None,
    profile: AudioCaptureProfile,
    clipping_start_suspected: bool,
    clipping_end_suspected: bool,
) -> tuple[str, ...]:
    hints: list[str] = []
    if clipping_start_suspected:
        hints.append("possible_clipped_start")
    if clipping_end_suspected:
        hints.append("possible_clipped_end")
    if vad_profile:
        leading = int(vad_profile.get("leading_silence_ms", 0) or 0)
        trailing = int(vad_profile.get("trailing_silence_ms", 0) or 0)
        if leading <= min(profile.pre_roll_ms, 120):
            hints.append("low_leading_padding")
        if trailing <= min(profile.post_roll_ms, 120):
            hints.append("low_trailing_silence")
        if float(vad_profile.get("speech_ratio", 0.0) or 0.0) < 0.08:
            hints.append("weak_speech_ratio")
    return tuple(dict.fromkeys(hints))


def should_trigger_bounded_relisten(
    *,
    attempt_index: int,
    max_relisten_attempts: int,
    clipping_start_suspected: bool,
    clipping_end_suspected: bool,
    endpoint_quality_hints: tuple[str, ...],
    relisten_enabled: bool,
) -> bool:
    if not relisten_enabled:
        return False
    if attempt_index >= max_relisten_attempts:
        return False
    if clipping_start_suspected or clipping_end_suspected:
        return True
    if endpoint_quality_hints:
        return True
    return False


def build_capture_attempt(
    *,
    session_id: str,
    profile: AudioCaptureProfile,
    attempt_index: int,
    started_at_ms: int,
    ended_at_ms: int,
    raw_duration_ms: int,
    processed_duration_ms: int,
    utterance_duration_ms: int,
    clipping_start_suspected: bool,
    clipping_end_suspected: bool,
    endpoint_quality_hints: tuple[str, ...],
    relisten_triggered: bool,
    recovery_prompt_surface: str | None = None,
    speech_started_at_ms: int | None = None,
    speech_ended_at_ms: int | None = None,
    capture_attempt_id: str | None = None,
) -> AudioCaptureAttempt:
    return AudioCaptureAttempt(
        capture_attempt_id=capture_attempt_id or f"cap-{uuid4().hex[:10]}",
        session_id=session_id,
        profile_id=profile.profile_id,
        attempt_index=attempt_index,
        started_at_ms=started_at_ms,
        ended_at_ms=ended_at_ms,
        raw_duration_ms=raw_duration_ms,
        processed_duration_ms=processed_duration_ms,
        speech_started_at_ms=speech_started_at_ms,
        speech_ended_at_ms=speech_ended_at_ms,
        utterance_duration_ms=utterance_duration_ms,
        clipping_start_suspected=clipping_start_suspected,
        clipping_end_suspected=clipping_end_suspected,
        endpoint_quality_hints=endpoint_quality_hints,
        relisten_triggered=relisten_triggered,
        recovery_prompt_surface=recovery_prompt_surface,
    )

