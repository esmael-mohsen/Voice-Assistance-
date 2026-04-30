"""Centralized runtime settings for STT and TTS layers."""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from core.critical_prompts import (
    FAILURE_MISSING,
    FAILURE_MOJIBAKE_PATTERN,
    FAILURE_NOT_NORMALIZED,
    FAILURE_REPLACEMENT_CHARACTER,
    FAILURE_UNEXPECTED_UNICODE,
    INTEGRITY_FALLBACK_USED,
    INTEGRITY_REPAIRED,
    INTEGRITY_VALID,
    approved_catalog_source,
    build_default_critical_prompt_catalog,
    contains_arabic_mojibake,
    contains_replacement_character,
    has_unexpected_unicode,
    emergency_fallback_text,
    language_key_for_locale,
    prompt_definition,
    surface_binding,
    surface_binding_payloads,
)
from core.text_integrity import normalize_nfc
from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
    normalize_provider_id,
)
from core.speech.provider_resolver import (
    DEFAULT_CONNECTIVITY_GRACE_S,
    build_connectivity_state,
    normalize_confirmed_status,
    normalize_detected_status,
    normalize_override_mode,
)
from settings.profile_store import (
    load_profile_snapshot,
    normalize_critical_prompt_catalog_snapshot,
    save_profile_snapshot,
)

logger = logging.getLogger(__name__)

_DEFAULT_CRITICAL_PROMPT_CATALOG: dict[str, dict[str, str]] = build_default_critical_prompt_catalog()
_SPEECH_PRIORITY_RANK: dict[str, int] = {
    "warning": 0,
    "action_confirmation": 1,
    "error": 2,
    "info": 3,
}


class SettingsManager:
    def __init__(self):
        self.username = ""
        self.language = "en-US"
        self.voice_gender = "female"
        self.default_speech_speed = 1.0
        self.speech_speed = self.default_speech_speed
        self.speech_provider = LEGACY_PROVIDER_ID
        self.pending_speech_provider: str | None = None
        self.deferred_provider_switch = False
        self.min_speech_speed = 0.6
        self.max_speech_speed = 1.6
        self.max_listen_seconds = 8.0
        self.max_speak_seconds = 8.0
        self.priority_coalescing_window_s = 2.0
        self.concise_word_limit = 12
        self.offline_allowlisted_capabilities: set[str] = {"system_status"}
        self.network_available = True
        self.network_override_mode = "auto"
        self.connectivity_detected_status = "online"
        self.connectivity_last_confirmed_status = "online"
        self.connectivity_last_confirmed_at: float | None = None
        self.connectivity_grace_window_deadline_at: float | None = None
        self.connectivity_probe_generation = 0
        self.connectivity_startup_reset_applied = False
        self.connectivity_grace_window_s = DEFAULT_CONNECTIVITY_GRACE_S
        self.wake_primary_mode = WAKE_MODE_KEYWORD_LOW_POWER
        self.wake_fallback_mode = WAKE_MODE_HARDWARE_TRIGGER
        self.wake_dev_fallback_mode = WAKE_MODE_STT_BASED
        self.stt_wake_allowed_in_production = False
        self.low_power_standby_enabled = True
        self.non_speech_cues_enabled = True
        self.command_confidence_high_threshold = 0.82
        self.command_confidence_medium_threshold = 0.55
        self.command_protected_threshold = 0.9
        self.command_allow_missing_confidence_for_unprotected = True
        self.command_max_retry_cycles = 1
        self.command_fallback_enabled = True
        self.command_rescue_enabled = True
        self.command_offline_local_allowed = True
        self.standby_capture_profile_id = "standby_wake.default"
        self.onboarding_capture_profile_id = "onboarding.default"
        self.command_capture_profile_id = "command.default"
        self.confirmation_capture_profile_id = "confirmation.default"
        self.closed_vocabulary_retry_limit = 1
        self.speech_qualification_profile = "default"
        self.enable_audio_noise_suppression = False
        self.enable_capture_relisten = True
        self.enable_dictionary_bias = True
        self._critical_prompt_catalog = build_default_critical_prompt_catalog()
        self._repaired_prompt_keys: set[str] = set()
        self.release_threshold_policy, self.release_artifact_retention_days = (
            self._load_release_threshold_policy()
        )
        self._listener = None
        self._tts_engine = None
        self._speech_state = threading.Condition()
        self._speech_active = False
        self._speech_active_rank = max(_SPEECH_PRIORITY_RANK.values()) + 1
        self._voice_profiles = {
            ("ar-EG", "female"): "ar-EG-SalmaNeural",
            ("ar-EG", "male"): "ar-EG-ShakirNeural",
            # More human-sounding defaults
            ("en-US", "female"): "en-US-EmmaMultilingualNeural",
            ("en-US", "male"): "en-US-AndrewMultilingualNeural",
        }
        self._default_voice = "en-US-EmmaNeural"
        self._profile_loaded = False

    def load_user_profile(self) -> bool:
        """Load persisted profile if present. Returns True when loaded."""
        if self._profile_loaded:
            return bool(self.username)

        snapshot = load_profile_snapshot()
        self._profile_loaded = True
        if not snapshot:
            return False

        effective_snapshot: dict[str, Any] = dict(snapshot)
        repaired = False
        if not str(effective_snapshot.get("username", "") or "").strip():
            # First-run profiles can carry stale language from previous experiments.
            # Keep startup predictable and default to English until onboarding completes.
            if str(effective_snapshot.get("language", "en-US") or "").strip() != "en-US":
                effective_snapshot["language"] = "en-US"
                repaired = True

        self.apply_settings_snapshot(effective_snapshot, persist=repaired)

        logger.info("[SETTINGS] Loaded user profile (%s)", self.username or "no-name")
        return True

    def is_configured(self) -> bool:
        # First-run setup considered complete when a username exists.
        return bool(self.username)

    def get_settings_snapshot(self) -> dict[str, Any]:
        """Return a runtime-safe snapshot of active settings."""
        connectivity = self.get_connectivity_state_snapshot()
        return {
            "username": self.username,
            "language": self.language,
            "voice_gender": self.voice_gender,
            "speech_speed": self.speech_speed,
            "speech_provider": self.speech_provider,
            "pending_speech_provider": self.pending_speech_provider,
            "deferred_provider_switch": self.deferred_provider_switch,
            "max_listen_seconds": self.max_listen_seconds,
            "max_speak_seconds": self.max_speak_seconds,
            "priority_coalescing_window_s": self.priority_coalescing_window_s,
            "concise_word_limit": self.concise_word_limit,
            "offline_allowlisted_capabilities": sorted(self.offline_allowlisted_capabilities),
            "network_available": connectivity["effective_network_available"],
            "network_override_mode": connectivity["override_mode"],
            "connectivity_detected_status": connectivity["detected_status"],
            "connectivity_last_confirmed_status": connectivity["last_confirmed_status"],
            "connectivity_last_confirmed_at": connectivity["last_confirmed_at"],
            "connectivity_grace_window_deadline_at": connectivity["grace_window_deadline_at"],
            "connectivity_probe_generation": connectivity["probe_generation"],
            "connectivity_startup_reset_applied": connectivity["startup_reset_applied"],
            "connectivity_grace_window_s": connectivity.get("grace_window_s", self.connectivity_grace_window_s),
            "wake_primary_mode": self.wake_primary_mode,
            "wake_fallback_mode": self.wake_fallback_mode,
            "wake_dev_fallback_mode": self.wake_dev_fallback_mode,
            "stt_wake_allowed_in_production": self.stt_wake_allowed_in_production,
            "low_power_standby_enabled": self.low_power_standby_enabled,
            "non_speech_cues_enabled": self.non_speech_cues_enabled,
            "command_confidence_high_threshold": self.command_confidence_high_threshold,
            "command_confidence_medium_threshold": self.command_confidence_medium_threshold,
            "command_protected_threshold": self.command_protected_threshold,
            "command_allow_missing_confidence_for_unprotected": (
                self.command_allow_missing_confidence_for_unprotected
            ),
            "command_max_retry_cycles": self.command_max_retry_cycles,
            "command_fallback_enabled": self.command_fallback_enabled,
            "command_rescue_enabled": self.command_rescue_enabled,
            "command_offline_local_allowed": self.command_offline_local_allowed,
            "standby_capture_profile_id": self.standby_capture_profile_id,
            "onboarding_capture_profile_id": self.onboarding_capture_profile_id,
            "command_capture_profile_id": self.command_capture_profile_id,
            "confirmation_capture_profile_id": self.confirmation_capture_profile_id,
            "closed_vocabulary_retry_limit": self.closed_vocabulary_retry_limit,
            "speech_qualification_profile": self.speech_qualification_profile,
            "enable_audio_noise_suppression": self.enable_audio_noise_suppression,
            "enable_capture_relisten": self.enable_capture_relisten,
            "enable_dictionary_bias": self.enable_dictionary_bias,
            "critical_prompt_catalog": self._critical_prompt_catalog,
            "release_threshold_policy": self.release_threshold_policy,
            "release_artifact_retention_days": self.release_artifact_retention_days,
        }

    def apply_settings_snapshot(self, snapshot: Mapping[str, Any], *, persist: bool = True) -> dict[str, Any]:
        """Apply a partial settings snapshot and keep attached dependencies aligned."""
        if snapshot is None:
            raise ValueError("snapshot must not be None")

        username = str(snapshot.get("username", self.username) or self.username).strip()
        language = str(snapshot.get("language", self.language) or self.language)
        voice_gender = str(snapshot.get("voice_gender", self.voice_gender) or self.voice_gender)
        speech_speed = self._clamp_speed(self._coerce_speed(snapshot.get("speech_speed", self.speech_speed)))
        speech_provider = self._coerce_provider(snapshot.get("speech_provider", self.speech_provider))
        pending_raw = snapshot.get("pending_speech_provider", self.pending_speech_provider)
        pending_provider = self._coerce_optional_provider(pending_raw)
        deferred_provider_switch = bool(snapshot.get("deferred_provider_switch", self.deferred_provider_switch))
        max_listen_seconds = self._coerce_positive_duration(
            snapshot.get("max_listen_seconds", self.max_listen_seconds),
            fallback=self.max_listen_seconds,
        )
        max_speak_seconds = self._coerce_positive_duration(
            snapshot.get("max_speak_seconds", self.max_speak_seconds),
            fallback=self.max_speak_seconds,
        )
        priority_coalescing_window_s = self._coerce_positive_duration(
            snapshot.get("priority_coalescing_window_s", self.priority_coalescing_window_s),
            fallback=self.priority_coalescing_window_s,
        )
        concise_word_limit = self._coerce_word_limit(snapshot.get("concise_word_limit", self.concise_word_limit))
        offline_allowlisted_capabilities = self._coerce_allowlist(
            snapshot.get("offline_allowlisted_capabilities", self.offline_allowlisted_capabilities)
        )
        legacy_network_available = bool(snapshot.get("network_available", self.network_available))
        override_mode = normalize_override_mode(
            str(snapshot.get("network_override_mode", self.network_override_mode))
        )
        detected_status = normalize_detected_status(
            str(
                snapshot.get(
                    "connectivity_detected_status",
                    self.connectivity_detected_status if self.connectivity_detected_status else (
                        "online" if legacy_network_available else "offline"
                    ),
                )
            )
        )
        last_confirmed_status = normalize_confirmed_status(
            str(
                snapshot.get(
                    "connectivity_last_confirmed_status",
                    self.connectivity_last_confirmed_status if self.connectivity_last_confirmed_status else (
                        "online" if legacy_network_available else "offline"
                    ),
                )
            )
        )
        last_confirmed_at = self._coerce_optional_timestamp(
            snapshot.get("connectivity_last_confirmed_at", self.connectivity_last_confirmed_at)
        )
        grace_window_deadline_at = self._coerce_optional_timestamp(
            snapshot.get("connectivity_grace_window_deadline_at", self.connectivity_grace_window_deadline_at)
        )
        probe_generation = self._coerce_non_negative_int(
            snapshot.get("connectivity_probe_generation", self.connectivity_probe_generation)
        )
        startup_reset_applied = bool(
            snapshot.get("connectivity_startup_reset_applied", self.connectivity_startup_reset_applied)
        )
        connectivity_grace_window_s = self._coerce_positive_duration(
            snapshot.get("connectivity_grace_window_s", self.connectivity_grace_window_s),
            fallback=self.connectivity_grace_window_s,
        )
        connectivity_state = build_connectivity_state(
            override_mode=override_mode,
            detected_status=detected_status,
            last_confirmed_status=last_confirmed_status,
            last_confirmed_at=last_confirmed_at,
            grace_window_deadline_at=grace_window_deadline_at,
            probe_generation=probe_generation,
            startup_reset_applied=startup_reset_applied,
            now_s=time.time(),
        )
        wake_primary_mode = self._coerce_wake_mode(
            snapshot.get("wake_primary_mode", self.wake_primary_mode),
            fallback=self.wake_primary_mode,
        )
        wake_fallback_mode = self._coerce_wake_mode(
            snapshot.get("wake_fallback_mode", self.wake_fallback_mode),
            fallback=self.wake_fallback_mode,
        )
        wake_dev_fallback_mode = self._coerce_wake_mode(
            snapshot.get("wake_dev_fallback_mode", self.wake_dev_fallback_mode),
            fallback=self.wake_dev_fallback_mode,
        )
        stt_wake_allowed_in_production = bool(
            snapshot.get("stt_wake_allowed_in_production", self.stt_wake_allowed_in_production)
        )
        low_power_standby_enabled = bool(
            snapshot.get("low_power_standby_enabled", self.low_power_standby_enabled)
        )
        non_speech_cues_enabled = bool(snapshot.get("non_speech_cues_enabled", self.non_speech_cues_enabled))
        command_confidence_high_threshold = self._coerce_probability(
            snapshot.get("command_confidence_high_threshold", self.command_confidence_high_threshold),
            fallback=self.command_confidence_high_threshold,
        )
        command_confidence_medium_threshold = self._coerce_probability(
            snapshot.get("command_confidence_medium_threshold", self.command_confidence_medium_threshold),
            fallback=self.command_confidence_medium_threshold,
        )
        if command_confidence_high_threshold < command_confidence_medium_threshold:
            command_confidence_high_threshold = command_confidence_medium_threshold
        command_protected_threshold = self._coerce_probability(
            snapshot.get("command_protected_threshold", self.command_protected_threshold),
            fallback=self.command_protected_threshold,
        )
        if command_protected_threshold < command_confidence_high_threshold:
            command_protected_threshold = command_confidence_high_threshold
        command_allow_missing_confidence_for_unprotected = bool(
            snapshot.get(
                "command_allow_missing_confidence_for_unprotected",
                self.command_allow_missing_confidence_for_unprotected,
            )
        )
        command_max_retry_cycles = self._coerce_retry_cycles(
            snapshot.get("command_max_retry_cycles", self.command_max_retry_cycles),
            fallback=self.command_max_retry_cycles,
        )
        command_fallback_enabled = bool(
            snapshot.get(
                "command_fallback_enabled",
                snapshot.get("command_rescue_enabled", self.command_fallback_enabled),
            )
        )
        command_rescue_enabled = bool(
            snapshot.get("command_rescue_enabled", command_fallback_enabled)
        )
        command_offline_local_allowed = bool(
            snapshot.get("command_offline_local_allowed", self.command_offline_local_allowed)
        )
        standby_capture_profile_id = str(
            snapshot.get("standby_capture_profile_id", self.standby_capture_profile_id) or self.standby_capture_profile_id
        ).strip()
        onboarding_capture_profile_id = str(
            snapshot.get("onboarding_capture_profile_id", self.onboarding_capture_profile_id)
            or self.onboarding_capture_profile_id
        ).strip()
        command_capture_profile_id = str(
            snapshot.get("command_capture_profile_id", self.command_capture_profile_id) or self.command_capture_profile_id
        ).strip()
        confirmation_capture_profile_id = str(
            snapshot.get("confirmation_capture_profile_id", self.confirmation_capture_profile_id)
            or self.confirmation_capture_profile_id
        ).strip()
        closed_vocabulary_retry_limit = self._coerce_retry_cycles(
            snapshot.get("closed_vocabulary_retry_limit", self.closed_vocabulary_retry_limit),
            fallback=self.closed_vocabulary_retry_limit,
        )
        speech_qualification_profile = str(
            snapshot.get("speech_qualification_profile", self.speech_qualification_profile)
            or self.speech_qualification_profile
        ).strip().lower()
        if speech_qualification_profile not in {"default", "simplified"}:
            speech_qualification_profile = self.speech_qualification_profile
        enable_audio_noise_suppression = bool(
            snapshot.get("enable_audio_noise_suppression", self.enable_audio_noise_suppression)
        )
        enable_capture_relisten = bool(
            snapshot.get("enable_capture_relisten", self.enable_capture_relisten)
        )
        enable_dictionary_bias = bool(
            snapshot.get("enable_dictionary_bias", self.enable_dictionary_bias)
        )
        critical_prompt_catalog, repaired_prompt_keys = self._coerce_critical_prompt_catalog(
            snapshot.get("critical_prompt_catalog", self._critical_prompt_catalog)
        )
        release_threshold_policy = self._coerce_release_threshold_policy(
            snapshot.get("release_threshold_policy", self.release_threshold_policy)
        )
        release_artifact_retention_days = self._coerce_retention_days(
            snapshot.get("release_artifact_retention_days", self.release_artifact_retention_days)
        )

        self.username = username
        self.language = language
        self.voice_gender = voice_gender
        self.speech_speed = speech_speed
        self.speech_provider = speech_provider
        self.pending_speech_provider = pending_provider
        self.deferred_provider_switch = deferred_provider_switch
        self.max_listen_seconds = max_listen_seconds
        self.max_speak_seconds = max_speak_seconds
        self.priority_coalescing_window_s = priority_coalescing_window_s
        self.concise_word_limit = concise_word_limit
        self.offline_allowlisted_capabilities = offline_allowlisted_capabilities
        self.network_override_mode = connectivity_state.override_mode
        self.connectivity_detected_status = connectivity_state.detected_status
        self.connectivity_last_confirmed_status = connectivity_state.last_confirmed_status
        self.connectivity_last_confirmed_at = connectivity_state.last_confirmed_at
        self.connectivity_grace_window_deadline_at = connectivity_state.grace_window_deadline_at
        self.connectivity_probe_generation = connectivity_state.probe_generation
        self.connectivity_startup_reset_applied = connectivity_state.startup_reset_applied
        self.connectivity_grace_window_s = connectivity_grace_window_s
        self.network_available = connectivity_state.effective_network_available
        self.wake_primary_mode = wake_primary_mode
        self.wake_fallback_mode = wake_fallback_mode
        self.wake_dev_fallback_mode = wake_dev_fallback_mode
        self.stt_wake_allowed_in_production = stt_wake_allowed_in_production
        self.low_power_standby_enabled = low_power_standby_enabled
        self.non_speech_cues_enabled = non_speech_cues_enabled
        self.command_confidence_high_threshold = command_confidence_high_threshold
        self.command_confidence_medium_threshold = command_confidence_medium_threshold
        self.command_protected_threshold = command_protected_threshold
        self.command_allow_missing_confidence_for_unprotected = (
            command_allow_missing_confidence_for_unprotected
        )
        self.command_max_retry_cycles = command_max_retry_cycles
        self.command_fallback_enabled = command_fallback_enabled
        self.command_rescue_enabled = command_rescue_enabled
        self.command_offline_local_allowed = command_offline_local_allowed
        self.standby_capture_profile_id = standby_capture_profile_id or self.standby_capture_profile_id
        self.onboarding_capture_profile_id = onboarding_capture_profile_id or self.onboarding_capture_profile_id
        self.command_capture_profile_id = command_capture_profile_id or self.command_capture_profile_id
        self.confirmation_capture_profile_id = (
            confirmation_capture_profile_id or self.confirmation_capture_profile_id
        )
        self.closed_vocabulary_retry_limit = max(1, closed_vocabulary_retry_limit)
        self.speech_qualification_profile = speech_qualification_profile
        self.enable_audio_noise_suppression = enable_audio_noise_suppression
        self.enable_capture_relisten = enable_capture_relisten
        self.enable_dictionary_bias = enable_dictionary_bias
        self._critical_prompt_catalog = critical_prompt_catalog
        self._repaired_prompt_keys = set(repaired_prompt_keys)
        self.release_threshold_policy = release_threshold_policy
        self.release_artifact_retention_days = release_artifact_retention_days

        if self._listener:
            self._listener.set_language(self.language)
        if self._tts_engine:
            self._tts_engine.set_language(self.language)
            self._tts_engine.set_voice_gender(self.voice_gender)
            self._tts_engine.set_speech_speed(self.speech_speed)
            self._apply_voice_profile()

        if persist or repaired_prompt_keys:
            self._persist_profile()

        logger.info(
            "[SETTINGS] Applied snapshot (language=%s, gender=%s, speed=%.2f, provider=%s, network=%s, configured=%s)",
            self.language,
            self.voice_gender,
            self.speech_speed,
            self.speech_provider,
            self.get_connectivity_state_snapshot()["effective_network_available"],
            bool(self.username),
        )
        return self.get_settings_snapshot()

    def get_onboarding_configuration_snapshot(self) -> dict[str, Any]:
        """Return the onboarding-relevant view of settings values."""
        return {
            "required": not self.is_configured(),
            "selected_language": self.language,
            "selected_voice_gender": self.voice_gender,
            "selected_speech_speed": self.speech_speed,
            "confirmed_username": self.username or None,
        }

    def persist_onboarding_configuration(
        self,
        *,
        language: Optional[str] = None,
        voice_gender: Optional[str] = None,
        speech_speed: Optional[float] = None,
        username: Optional[str] = None,
    ) -> dict[str, Any]:
        """Persist onboarding-selected settings without owning onboarding flow logic."""
        snapshot = self.get_settings_snapshot()
        if language is not None:
            snapshot["language"] = language
        if voice_gender is not None:
            snapshot["voice_gender"] = voice_gender
        if speech_speed is not None:
            snapshot["speech_speed"] = speech_speed
        if username is not None:
            snapshot["username"] = username

        self.apply_settings_snapshot(snapshot, persist=True)
        return self.get_onboarding_configuration_snapshot()

    def _persist_profile(self) -> None:
        try:
            save_profile_snapshot(self.get_settings_snapshot())
        except Exception:  # noqa: BLE001
            logger.exception("[SETTINGS] Failed to persist profile")

    def set_username(self, username: str):
        username = (username or "").strip()
        if not username:
            logger.warning("[SETTINGS] Missing username")
            return self.username
        self.username = username
        self._persist_profile()
        return self.username

    def attach_listener(self, listener):
        self._listener = listener
        self._listener.set_language(self.language)
        logger.info("[SETTINGS] Listener attached with language %s", self.language)

    def attach_tts_engine(self, tts_engine):
        self._tts_engine = tts_engine
        self._tts_engine.configure(
            language=self.language,
            gender=self.voice_gender,
            speed=self.speech_speed,
            voice_id=self._current_voice_id(),
            pitch="+0Hz",
            volume="+0%",
        )
        logger.info("[SETTINGS] TTS engine attached")

    def set_language(self, language_code: str):
        if not language_code:
            logger.warning("[SETTINGS] Missing language code")
            return self.language
        self.language = language_code
        if self._listener:
            self._listener.set_language(language_code)
        if self._tts_engine:
            self._tts_engine.set_language(language_code)
            self._apply_voice_profile()
        logger.info("[SETTINGS] Language switched to %s", language_code)
        self._persist_profile()
        return self.language

    def set_voice_gender(self, gender: Optional[str]):
        if not gender:
            logger.warning("[SETTINGS] Missing gender value")
            return self.voice_gender
        self.voice_gender = gender
        if self._tts_engine:
            self._tts_engine.set_voice_gender(gender)
            self._apply_voice_profile()
        logger.info("[SETTINGS] Voice gender set to %s", gender)
        self._persist_profile()
        return self.voice_gender

    def set_speech_speed(self, speed: float):
        speed = self._clamp_speed(speed)
        self.speech_speed = speed
        if self._tts_engine:
            self._tts_engine.set_speech_speed(speed)
        logger.info("[SETTINGS] Speech speed set to %.2f", speed)
        self._persist_profile()
        return self.speech_speed

    def adjust_speech_speed(self, delta: float):
        return self.set_speech_speed(self.speech_speed + delta)

    def set_speech_provider(self, provider_id: str):
        self.speech_provider = self._coerce_provider(provider_id)
        self.pending_speech_provider = None
        self.deferred_provider_switch = False
        logger.info("[SETTINGS] Speech provider set to %s", self.speech_provider)
        self._persist_profile()
        return self.speech_provider

    def request_speech_provider(self, provider_id: str, *, runtime_active: bool) -> dict[str, Any]:
        provider = self._coerce_provider(provider_id)
        if runtime_active:
            self.pending_speech_provider = provider
            self.deferred_provider_switch = True
            logger.info("[SETTINGS] Deferred provider switch requested: %s", provider)
        else:
            self.speech_provider = provider
            self.pending_speech_provider = None
            self.deferred_provider_switch = False
            logger.info("[SETTINGS] Provider switch applied immediately: %s", provider)
        self._persist_profile()
        return self.get_settings_snapshot()

    def consume_deferred_speech_provider(self) -> str | None:
        if not self.deferred_provider_switch or not self.pending_speech_provider:
            return None
        applied = self._coerce_provider(self.pending_speech_provider)
        self.speech_provider = applied
        self.pending_speech_provider = None
        self.deferred_provider_switch = False
        logger.info("[SETTINGS] Applied deferred provider switch: %s", applied)
        self._persist_profile()
        return applied

    def _clamp_speed(self, speed: float) -> float:
        return max(self.min_speech_speed, min(speed, self.max_speech_speed))

    def _coerce_speed(self, speed: Any) -> float:
        try:
            return float(speed)
        except (TypeError, ValueError):
            logger.warning("[SETTINGS] Invalid speed value %r, keeping %.2f", speed, self.speech_speed)
            return self.speech_speed

    def _coerce_provider(self, provider_id: Any) -> str:
        provider = normalize_provider_id(str(provider_id or self.speech_provider))
        if not provider:
            return LEGACY_PROVIDER_ID
        return provider

    def _coerce_optional_provider(self, provider_id: Any) -> str | None:
        if provider_id in (None, ""):
            return None
        normalized = normalize_provider_id(str(provider_id))
        return normalized or None

    def _coerce_positive_duration(self, value: Any, *, fallback: float) -> float:
        try:
            parsed = float(value)
            if parsed <= 0:
                raise ValueError
            return parsed
        except (TypeError, ValueError):
            logger.warning("[SETTINGS] Invalid duration value %r, keeping %.2f", value, fallback)
            return fallback

    def _coerce_word_limit(self, value: Any) -> int:
        try:
            parsed = int(value)
            if parsed <= 0:
                raise ValueError
            return parsed
        except (TypeError, ValueError):
            logger.warning("[SETTINGS] Invalid concise_word_limit %r, keeping %s", value, self.concise_word_limit)
            return self.concise_word_limit

    def _coerce_optional_timestamp(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            parsed = float(value)
            return parsed if parsed >= 0 else None
        except (TypeError, ValueError):
            return None

    def _coerce_non_negative_int(self, value: Any) -> int:
        try:
            parsed = int(value)
            return max(0, parsed)
        except (TypeError, ValueError):
            return 0

    def _coerce_allowlist(self, value: Any) -> set[str]:
        if value is None:
            return set(self.offline_allowlisted_capabilities)
        if isinstance(value, (list, tuple, set)):
            cleaned = {str(item).strip().lower() for item in value if str(item).strip()}
            return cleaned or {"system_status"}
        if isinstance(value, str):
            cleaned = {item.strip().lower() for item in value.split(",") if item.strip()}
            return cleaned or {"system_status"}
        return set(self.offline_allowlisted_capabilities)

    def _coerce_wake_mode(self, value: Any, *, fallback: str) -> str:
        mode = str(value or fallback).strip().lower()
        if mode not in {WAKE_MODE_KEYWORD_LOW_POWER, WAKE_MODE_HARDWARE_TRIGGER, WAKE_MODE_STT_BASED}:
            logger.warning("[SETTINGS] Invalid wake mode %r, keeping %s", value, fallback)
            return fallback
        return mode

    def _coerce_probability(self, value: Any, *, fallback: float) -> float:
        try:
            parsed = float(value)
            if parsed < 0 or parsed > 1:
                raise ValueError
            return parsed
        except (TypeError, ValueError):
            logger.warning("[SETTINGS] Invalid probability value %r, keeping %.2f", value, fallback)
            return fallback

    def _coerce_retry_cycles(self, value: Any, *, fallback: int) -> int:
        try:
            parsed = int(value)
            return max(0, parsed)
        except (TypeError, ValueError):
            logger.warning("[SETTINGS] Invalid retry cycle value %r, keeping %s", value, fallback)
            return fallback

    def _coerce_critical_prompt_catalog(self, value: Any) -> tuple[dict[str, dict[str, str]], list[str]]:
        catalog, _, repaired_keys = normalize_critical_prompt_catalog_snapshot(value)
        if not catalog:
            return build_default_critical_prompt_catalog(), []
        return catalog, repaired_keys

    def _coerce_release_threshold_policy(self, value: Any) -> dict[str, dict[str, float]]:
        fallback_policy = getattr(
            self,
            "release_threshold_policy",
            {
                "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
                "listen_to_result": {"threshold_ms": 120.0, "threshold_pct": 15.0},
                "result_to_speech_start": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            },
        )
        if not isinstance(value, Mapping):
            return dict(fallback_policy)
        policy: dict[str, dict[str, float]] = {}
        for metric_name, threshold in value.items():
            if not isinstance(threshold, Mapping):
                continue
            try:
                threshold_ms = float(threshold.get("threshold_ms", 0.0))
                threshold_pct = float(threshold.get("threshold_pct", 0.0))
            except (TypeError, ValueError):
                continue
            policy[str(metric_name)] = {
                "threshold_ms": max(0.0, threshold_ms),
                "threshold_pct": max(0.0, threshold_pct),
            }
        return policy or dict(fallback_policy)

    def _coerce_retention_days(self, value: Any) -> int:
        fallback_days = int(getattr(self, "release_artifact_retention_days", 180))
        try:
            parsed = int(value)
            if parsed <= 0:
                raise ValueError
            return parsed
        except (TypeError, ValueError):
            logger.warning(
                "[SETTINGS] Invalid release_artifact_retention_days %r, keeping %s",
                value,
                fallback_days,
            )
            return fallback_days

    def _load_release_threshold_policy(self) -> tuple[dict[str, dict[str, float]], int]:
        policy_path = Path(__file__).resolve().parent / "release_thresholds.json"
        default_policy = {
            "wake_to_listen": {"threshold_ms": 100.0, "threshold_pct": 15.0},
            "listen_to_result": {"threshold_ms": 120.0, "threshold_pct": 15.0},
            "result_to_speech_start": {"threshold_ms": 100.0, "threshold_pct": 15.0},
        }
        default_retention_days = 180
        if not policy_path.exists():
            return default_policy, default_retention_days

        try:
            payload = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            logger.exception("[SETTINGS] Failed to load release threshold policy, using defaults")
            return default_policy, default_retention_days

        raw_metrics = payload.get("metrics", {})
        raw_days = payload.get("retention_days", default_retention_days)
        policy = self._coerce_release_threshold_policy(raw_metrics)
        retention_days = self._coerce_retention_days(raw_days)
        return policy, retention_days

    def get_release_threshold_policy(self) -> dict[str, dict[str, float]]:
        return dict(self.release_threshold_policy)

    def get_release_metric_threshold(self, metric_name: str) -> dict[str, float]:
        metric = str(metric_name or "").strip()
        return dict(self.release_threshold_policy.get(metric, {"threshold_ms": 0.0, "threshold_pct": 0.0}))

    def get_runtime_limits(self) -> dict[str, float]:
        return {
            "max_listen_seconds": self.max_listen_seconds,
            "max_speak_seconds": self.max_speak_seconds,
            "coalescing_window_s": self.priority_coalescing_window_s,
        }

    def set_network_available(self, available: bool, *, persist: bool = False) -> bool:
        status = "online" if bool(available) else "offline"
        now_value = time.time()
        self.connectivity_detected_status = status
        self.connectivity_last_confirmed_status = status
        self.connectivity_last_confirmed_at = now_value
        self.connectivity_grace_window_deadline_at = None
        self.connectivity_probe_generation = max(0, self.connectivity_probe_generation)
        self.network_available = self.get_connectivity_state_snapshot(now_s=now_value)["effective_network_available"]
        if persist:
            self._persist_profile()
        return self.network_available

    def set_network_override_mode(self, mode: str, *, persist: bool = False) -> str:
        self.network_override_mode = normalize_override_mode(mode)
        self.network_available = self.get_connectivity_state_snapshot()["effective_network_available"]
        if persist:
            self._persist_profile()
        return self.network_override_mode

    def reset_network_override_for_startup(self) -> dict[str, Any]:
        self.network_override_mode = "auto"
        self.connectivity_startup_reset_applied = True
        self.network_available = self.get_connectivity_state_snapshot()["effective_network_available"]
        return self.get_connectivity_state_snapshot()

    def apply_network_probe_result(
        self,
        result: Mapping[str, Any],
        *,
        grace_window_s: float | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        status = normalize_detected_status(str(result.get("status", "uncertain")))
        checked_at = self._coerce_optional_timestamp(result.get("checked_at", time.time())) or time.time()
        configured_grace_s = grace_window_s if grace_window_s is not None else self.connectivity_grace_window_s
        bounded_grace_s = max(0.0, min(float(configured_grace_s), 5.0))

        if status in {"online", "offline"}:
            self.connectivity_detected_status = status
            self.connectivity_last_confirmed_status = status
            self.connectivity_last_confirmed_at = checked_at
            self.connectivity_grace_window_deadline_at = None
        else:
            self.connectivity_detected_status = "uncertain"
            if self.connectivity_last_confirmed_status in {"online", "offline"}:
                self.connectivity_grace_window_deadline_at = checked_at + bounded_grace_s
            else:
                self.connectivity_grace_window_deadline_at = checked_at

        self.connectivity_probe_generation = max(0, self.connectivity_probe_generation) + 1
        self.network_available = self.get_connectivity_state_snapshot(now_s=checked_at)[
            "effective_network_available"
        ]
        if persist:
            self._persist_profile()
        return self.get_connectivity_state_snapshot(now_s=checked_at)

    def get_connectivity_state_snapshot(self, *, now_s: float | None = None) -> dict[str, Any]:
        state = build_connectivity_state(
            override_mode=self.network_override_mode,
            detected_status=self.connectivity_detected_status,
            last_confirmed_status=self.connectivity_last_confirmed_status,
            last_confirmed_at=self.connectivity_last_confirmed_at,
            grace_window_deadline_at=self.connectivity_grace_window_deadline_at,
            probe_generation=self.connectivity_probe_generation,
            startup_reset_applied=self.connectivity_startup_reset_applied,
            now_s=now_s if now_s is not None else time.time(),
        )
        payload = state.to_dict()
        payload["grace_window_s"] = self.connectivity_grace_window_s
        return payload

    def get_critical_prompt_catalog(self) -> dict[str, dict[str, str]]:
        return {
            prompt_key: {
                "ar": str(entry.get("ar", "") or ""),
                "en": str(entry.get("en", "") or ""),
            }
            for prompt_key, entry in self._critical_prompt_catalog.items()
        }

    def get_critical_surface_bindings(self) -> list[dict[str, Any]]:
        return surface_binding_payloads()

    def _critical_text_failure_reason(self, *, language: str, text: str) -> str | None:
        raw_value = str(text or "").strip()
        normalized = normalize_nfc(raw_value)
        if not normalized:
            return FAILURE_MISSING
        if raw_value != normalized:
            return FAILURE_NOT_NORMALIZED
        if contains_replacement_character(normalized):
            return FAILURE_REPLACEMENT_CHARACTER
        if has_unexpected_unicode(normalized):
            return FAILURE_UNEXPECTED_UNICODE
        if language == "ar" and contains_arabic_mojibake(normalized):
            return FAILURE_MOJIBAKE_PATTERN
        return None

    def _format_critical_text(self, text: str, format_kwargs: Mapping[str, Any] | None) -> str:
        template = str(text or "")
        if not format_kwargs:
            return template
        try:
            return template.format(**dict(format_kwargs))
        except (KeyError, ValueError):
            logger.warning("[SETTINGS] Failed to format critical prompt template %r", template)
            return template

    def resolve_critical_surface(
        self,
        surface_id: str,
        *,
        format_kwargs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        binding = surface_binding(surface_id)
        if binding is None:
            return {
                "surface_id": surface_id,
                "prompt_key": None,
                "language": self.language,
                "language_key": language_key_for_locale(self.language),
                "integrity_status": INTEGRITY_FALLBACK_USED,
                "fallback_used": True,
                "failure_reason": "unapproved_surface",
                "text": "",
                "catalog_source": approved_catalog_source(),
                "signal_emitted": False,
            }

        prompt_key = binding.prompt_key
        language_key = language_key_for_locale(self.language)
        entry = self._critical_prompt_catalog.get(prompt_key, {})
        selected_text = str(entry.get(language_key, "") or "").strip()
        failure_reason = self._critical_text_failure_reason(language=language_key, text=selected_text)
        fallback_used = failure_reason is not None
        if fallback_used:
            selected_text = emergency_fallback_text(prompt_key, self.language)

        selected_text = self._format_critical_text(selected_text, format_kwargs)
        if fallback_used:
            integrity_status = INTEGRITY_FALLBACK_USED
        elif prompt_key in self._repaired_prompt_keys:
            integrity_status = INTEGRITY_REPAIRED
        else:
            integrity_status = INTEGRITY_VALID

        prompt_meta = prompt_definition(prompt_key)
        approved_entry = prompt_meta.to_catalog_entry() if prompt_meta else {"ar": "", "en": ""}
        return {
            "surface_id": binding.surface_id,
            "prompt_key": prompt_key,
            "module_path": binding.module_path,
            "flow": binding.flow,
            "language": self.language,
            "language_key": language_key,
            "integrity_status": integrity_status,
            "fallback_used": fallback_used,
            "failure_reason": failure_reason,
            "text": selected_text,
            "catalog_source": approved_catalog_source(),
            "signal_emitted": False,
            "approved_text": approved_entry,
            "surface_binding": binding.to_payload(),
        }

    def resolve_critical_prompt(
        self,
        prompt_key: str,
        *,
        fallback_ar: str,
        fallback_en: str,
    ) -> dict[str, Any]:
        language_key = language_key_for_locale(self.language)
        entry = self._critical_prompt_catalog.get(prompt_key, {})
        ar_text = str(entry.get("ar", "") or "").strip()
        en_text = str(entry.get("en", "") or "").strip()
        selected_text = ar_text if language_key == "ar" else en_text
        failure_reason = self._critical_text_failure_reason(language=language_key, text=selected_text)
        fallback_used = failure_reason is not None
        if fallback_used:
            selected = fallback_ar if language_key == "ar" else fallback_en
        else:
            selected = selected_text
        return {
            "prompt_key": prompt_key,
            "surface_id": None,
            "language": self.language,
            "language_key": language_key,
            "integrity_status": INTEGRITY_FALLBACK_USED if fallback_used else INTEGRITY_VALID,
            "fallback_used": fallback_used,
            "failure_reason": failure_reason,
            "text": selected,
            "ar": ar_text if not fallback_used else fallback_ar,
            "en": en_text if not fallback_used else fallback_en,
            "catalog_source": approved_catalog_source(),
            "signal_emitted": False,
        }

    def truncate_for_wearable(self, text: str, *, word_limit: int | None = None) -> str:
        clean_text = str(text or "").strip()
        if not clean_text:
            return ""
        limit = word_limit or self.concise_word_limit
        words = clean_text.split()
        if len(words) <= limit:
            return clean_text
        return " ".join(words[:limit]).strip()

    def _priority_rank(self, priority: str | None) -> int:
        key = str(priority or "info").strip().lower()
        return _SPEECH_PRIORITY_RANK.get(key, _SPEECH_PRIORITY_RANK["info"])

    def speak(
        self,
        text: str,
        *,
        interrupt_event: Any | None = None,
        priority: str = "info",
        preempt: bool = False,
    ):
        if not text:
            return None
        if not self._tts_engine:
            logger.warning("[SETTINGS] TTS engine is not attached; cannot speak")
            return None
        rank = self._priority_rank(priority)
        with self._speech_state:
            if self._speech_active and (preempt or rank < self._speech_active_rank):
                request_stop = getattr(self._tts_engine, "request_stop", None)
                if callable(request_stop):
                    request_stop()
            while self._speech_active:
                self._speech_state.wait(timeout=0.02)
            self._speech_active = True
            self._speech_active_rank = rank
        try:
            try:
                self._tts_engine.speak(
                    text,
                    max_duration_s=self.max_speak_seconds,
                    interrupt_event=interrupt_event,
                    priority=priority,
                    preempt=preempt,
                )
            except TypeError:
                try:
                    self._tts_engine.speak(
                        text,
                        max_duration_s=self.max_speak_seconds,
                        interrupt_event=interrupt_event,
                    )
                except TypeError:
                    self._tts_engine.speak(text)
        except KeyboardInterrupt:
            logger.info("[SETTINGS] Speech interrupted")
        except Exception:  # noqa: BLE001
            logger.exception("[SETTINGS] Failed to synthesize speech")
        finally:
            with self._speech_state:
                self._speech_active = False
                self._speech_active_rank = max(_SPEECH_PRIORITY_RANK.values()) + 1
                self._speech_state.notify_all()
        return text

    def speak_localized(
        self,
        ar_text: str,
        en_text: str,
        *,
        interrupt_event: Any | None = None,
        priority: str = "info",
        preempt: bool = False,
    ):
        text = ar_text if self.language.startswith("ar") else en_text
        self.speak(
            text,
            interrupt_event=interrupt_event,
            priority=priority,
            preempt=preempt,
        )
        return text

    def _current_voice_id(self) -> str:
        return self._voice_profiles.get((self.language, self.voice_gender), self._default_voice)

    def _apply_voice_profile(self):
        if self._tts_engine:
            self._tts_engine.set_voice_profile(self._current_voice_id())


settings_manager = SettingsManager()
