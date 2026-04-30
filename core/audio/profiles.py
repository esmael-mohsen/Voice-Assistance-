"""Capture profile helpers for command and onboarding STT flows."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from core.command_models import AudioCaptureProfile

_USAGE_MODE_ALIASES: dict[str, str] = {
    "wake": "standby_wake",
    "standby": "standby_wake",
    "wake_word": "standby_wake",
    "setup": "onboarding",
    "listen": "command",
    "confirm": "confirmation",
}


def normalize_usage_mode(value: str | None) -> str:
    mode = str(value or "command").strip().lower()
    return _USAGE_MODE_ALIASES.get(mode, mode)


def default_capture_profiles() -> dict[str, AudioCaptureProfile]:
    """Return baseline capture profiles tuned for each runtime usage mode."""
    return {
        "standby_wake.default": AudioCaptureProfile(
            profile_id="standby_wake.default",
            usage_mode="standby_wake",
            sample_rate_hz=16_000,
            pre_roll_ms=90,
            post_roll_ms=130,
            trailing_silence_ms=300,
            max_utterance_ms=2_500,
            dictionary_bias_mode="none",
        ),
        "onboarding.default": AudioCaptureProfile(
            profile_id="onboarding.default",
            usage_mode="onboarding",
            sample_rate_hz=16_000,
            pre_roll_ms=160,
            post_roll_ms=230,
            trailing_silence_ms=700,
            max_utterance_ms=9_000,
            dictionary_bias_mode="closed_choice",
            closed_vocabulary_id="onboarding.default",
        ),
        "command.default": AudioCaptureProfile(
            profile_id="command.default",
            usage_mode="command",
            sample_rate_hz=16_000,
            pre_roll_ms=180,
            post_roll_ms=220,
            trailing_silence_ms=650,
            max_utterance_ms=8_000,
            dictionary_bias_mode="command_inventory",
        ),
        "confirmation.default": AudioCaptureProfile(
            profile_id="confirmation.default",
            usage_mode="confirmation",
            sample_rate_hz=16_000,
            pre_roll_ms=150,
            post_roll_ms=180,
            trailing_silence_ms=520,
            max_utterance_ms=4_500,
            dictionary_bias_mode="closed_choice",
            closed_vocabulary_id="confirmation.yes_no",
        ),
    }


def _profile_id_for_mode(usage_mode: str) -> str:
    mode = normalize_usage_mode(usage_mode)
    return f"{mode}.default"


def _with_bias_mode(
    profile: AudioCaptureProfile,
    *,
    dictionary_bias_mode: str | None,
    closed_vocabulary_id: str | None,
) -> AudioCaptureProfile:
    if dictionary_bias_mode is None and closed_vocabulary_id is None:
        return profile
    bias_mode = str(dictionary_bias_mode or profile.dictionary_bias_mode).strip().lower()
    vocab_id = closed_vocabulary_id if closed_vocabulary_id is not None else profile.closed_vocabulary_id
    if bias_mode == "closed_choice" and not vocab_id:
        vocab_id = "closed_choice.default"
    if bias_mode != "closed_choice":
        vocab_id = None
    return replace(
        profile,
        dictionary_bias_mode=bias_mode,
        closed_vocabulary_id=vocab_id,
    )


def select_capture_profile(
    *,
    usage_mode: str | None,
    profile_overrides: Mapping[str, str] | None = None,
    dictionary_bias_mode: str | None = None,
    closed_vocabulary_id: str | None = None,
    qualification_profile: str = "default",
    allow_noise_suppression: bool | None = None,
) -> AudioCaptureProfile:
    mode = normalize_usage_mode(usage_mode)
    if mode not in {"standby_wake", "onboarding", "command", "confirmation"}:
        mode = "command"
    profiles = default_capture_profiles()
    selected_profile_id = _profile_id_for_mode(mode)
    if profile_overrides:
        override = str(profile_overrides.get(mode, "") or "").strip()
        if override in profiles:
            selected_profile_id = override
    profile = profiles.get(selected_profile_id, profiles["command.default"])
    profile = _with_bias_mode(
        profile,
        dictionary_bias_mode=dictionary_bias_mode,
        closed_vocabulary_id=closed_vocabulary_id,
    )
    qualification = str(qualification_profile or "default").strip().lower()
    if qualification == "simplified":
        profile = replace(
            profile,
            allow_noise_suppression=False,
            max_utterance_ms=min(profile.max_utterance_ms, 7_000),
        )
    elif allow_noise_suppression is not None:
        profile = replace(profile, allow_noise_suppression=bool(allow_noise_suppression))
    return profile

