import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from core.critical_prompts import (
    REQUIRED_PROMPT_LANGUAGES,
    build_default_critical_prompt_catalog,
    contains_arabic_mojibake,
    contains_replacement_character,
    has_unexpected_unicode,
    required_prompt_keys,
)
from core.text_integrity import normalize_nfc


@dataclass
class UserProfile:
    username: str = ""
    language: str = "en-US"
    voice_gender: str = "female"
    speech_speed: float = 1.0
    speech_provider: str = "legacy"
    pending_speech_provider: str | None = None
    deferred_provider_switch: bool = False
    max_listen_seconds: float = 8.0
    max_speak_seconds: float = 8.0
    priority_coalescing_window_s: float = 2.0
    concise_word_limit: int = 12
    offline_allowlisted_capabilities: list[str] = None
    # Deprecated persisted field: runtime now derives connectivity from probe state.
    network_available: bool = True
    wake_primary_mode: str = "keyword_low_power"
    wake_fallback_mode: str = "hardware_trigger"
    wake_dev_fallback_mode: str = "stt_based_wake"
    stt_wake_allowed_in_production: bool = False
    low_power_standby_enabled: bool = True
    non_speech_cues_enabled: bool = True
    command_confidence_high_threshold: float = 0.82
    command_confidence_medium_threshold: float = 0.55
    command_protected_threshold: float = 0.9
    command_allow_missing_confidence_for_unprotected: bool = True
    command_max_retry_cycles: int = 1
    command_fallback_enabled: bool = True
    command_rescue_enabled: bool = True
    command_offline_local_allowed: bool = True
    standby_capture_profile_id: str = "standby_wake.default"
    onboarding_capture_profile_id: str = "onboarding.default"
    command_capture_profile_id: str = "command.default"
    confirmation_capture_profile_id: str = "confirmation.default"
    closed_vocabulary_retry_limit: int = 1
    speech_qualification_profile: str = "default"
    enable_audio_noise_suppression: bool = False
    enable_capture_relisten: bool = True
    enable_dictionary_bias: bool = True
    critical_prompt_catalog: dict[str, dict[str, str]] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.username and self.language and self.voice_gender)

    def to_snapshot(self) -> dict[str, Any]:
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
            "offline_allowlisted_capabilities": list(
                self.offline_allowlisted_capabilities or ["system_status"]
            ),
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
            "critical_prompt_catalog": self.critical_prompt_catalog or {},
        }


def _profile_path() -> Path:
    # Store under settings/ so it's easy to find, and keep it local to the app folder.
    return Path(__file__).resolve().parent / "user_profile.json"


def profile_exists() -> bool:
    return _profile_path().exists()


def load_profile() -> Optional[UserProfile]:
    path = _profile_path()
    if not path.exists():
        return None

    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return profile_from_snapshot(data)


def save_profile(profile: UserProfile) -> None:
    path = _profile_path()
    payload = profile.to_snapshot()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_critical_prompt_catalog_snapshot(
    raw_catalog: Any,
) -> tuple[dict[str, dict[str, str]], bool, list[str]]:
    default_catalog = build_default_critical_prompt_catalog()
    catalog: dict[str, dict[str, str]] = {}
    repaired_keys: list[str] = []

    source_map = raw_catalog if isinstance(raw_catalog, Mapping) else {}
    for prompt_key in required_prompt_keys():
        approved_entry = default_catalog[prompt_key]
        raw_entry = source_map.get(prompt_key, {})
        entry_mapping = raw_entry if isinstance(raw_entry, Mapping) else {}
        normalized_entry: dict[str, str] = {}
        repaired = not isinstance(raw_entry, Mapping)

        for language in REQUIRED_PROMPT_LANGUAGES:
            raw_value = str(entry_mapping.get(language, "") or "").strip()
            value = normalize_nfc(raw_value)
            corrupt = (
                not value
                or raw_value != value
                or contains_replacement_character(value)
                or has_unexpected_unicode(value)
                or (language == "ar" and contains_arabic_mojibake(value))
            )
            if corrupt:
                repaired = True
                value = approved_entry[language]
            normalized_entry[language] = value

        catalog[prompt_key] = normalized_entry
        if repaired:
            repaired_keys.append(prompt_key)

    for key, value in source_map.items():
        prompt_key = str(key)
        if prompt_key in catalog or not isinstance(value, Mapping):
            continue
        catalog[prompt_key] = {
            language: str(value.get(language, "") or "")
            for language in REQUIRED_PROMPT_LANGUAGES
        }

    return catalog, bool(repaired_keys), repaired_keys


def profile_from_snapshot(snapshot: Mapping[str, Any]) -> UserProfile:
    pending_provider = snapshot.get("pending_speech_provider")
    pending_provider_normalized = str(pending_provider).strip().lower() if pending_provider else None
    raw_allowlist = snapshot.get("offline_allowlisted_capabilities", ["system_status"])
    allowlist = [str(item).strip().lower() for item in list(raw_allowlist or []) if str(item).strip()]
    raw_catalog = snapshot.get("critical_prompt_catalog") or {}
    critical_catalog, _, _ = normalize_critical_prompt_catalog_snapshot(raw_catalog)
    command_fallback_enabled = bool(snapshot.get("command_fallback_enabled", True))
    command_rescue_enabled = bool(snapshot.get("command_rescue_enabled", command_fallback_enabled))
    return UserProfile(
        username=str(snapshot.get("username", "") or ""),
        language=str(snapshot.get("language", "en-US") or "en-US"),
        voice_gender=str(snapshot.get("voice_gender", "female") or "female"),
        speech_speed=float(snapshot.get("speech_speed", 1.0) or 1.0),
        speech_provider=str(snapshot.get("speech_provider", "legacy") or "legacy").strip().lower(),
        pending_speech_provider=pending_provider_normalized or None,
        deferred_provider_switch=bool(snapshot.get("deferred_provider_switch", False)),
        max_listen_seconds=float(snapshot.get("max_listen_seconds", 8.0) or 8.0),
        max_speak_seconds=float(snapshot.get("max_speak_seconds", 8.0) or 8.0),
        priority_coalescing_window_s=float(snapshot.get("priority_coalescing_window_s", 2.0) or 2.0),
        concise_word_limit=int(snapshot.get("concise_word_limit", 12) or 12),
        offline_allowlisted_capabilities=allowlist or ["system_status"],
        # Persisted network truth is intentionally ignored; startup always probes.
        network_available=True,
        wake_primary_mode=str(snapshot.get("wake_primary_mode", "keyword_low_power") or "keyword_low_power"),
        wake_fallback_mode=str(snapshot.get("wake_fallback_mode", "hardware_trigger") or "hardware_trigger"),
        wake_dev_fallback_mode=str(
            snapshot.get("wake_dev_fallback_mode", "stt_based_wake") or "stt_based_wake"
        ),
        stt_wake_allowed_in_production=bool(snapshot.get("stt_wake_allowed_in_production", False)),
        low_power_standby_enabled=bool(snapshot.get("low_power_standby_enabled", True)),
        non_speech_cues_enabled=bool(snapshot.get("non_speech_cues_enabled", True)),
        command_confidence_high_threshold=float(snapshot.get("command_confidence_high_threshold", 0.82) or 0.82),
        command_confidence_medium_threshold=float(
            snapshot.get("command_confidence_medium_threshold", 0.55) or 0.55
        ),
        command_protected_threshold=float(snapshot.get("command_protected_threshold", 0.9) or 0.9),
        command_allow_missing_confidence_for_unprotected=bool(
            snapshot.get("command_allow_missing_confidence_for_unprotected", True)
        ),
        command_max_retry_cycles=max(0, int(snapshot.get("command_max_retry_cycles", 1) or 1)),
        command_fallback_enabled=command_fallback_enabled,
        command_rescue_enabled=command_rescue_enabled,
        command_offline_local_allowed=bool(snapshot.get("command_offline_local_allowed", True)),
        standby_capture_profile_id=str(
            snapshot.get("standby_capture_profile_id", "standby_wake.default") or "standby_wake.default"
        ),
        onboarding_capture_profile_id=str(
            snapshot.get("onboarding_capture_profile_id", "onboarding.default") or "onboarding.default"
        ),
        command_capture_profile_id=str(
            snapshot.get("command_capture_profile_id", "command.default") or "command.default"
        ),
        confirmation_capture_profile_id=str(
            snapshot.get("confirmation_capture_profile_id", "confirmation.default") or "confirmation.default"
        ),
        closed_vocabulary_retry_limit=max(1, int(snapshot.get("closed_vocabulary_retry_limit", 1) or 1)),
        speech_qualification_profile=str(snapshot.get("speech_qualification_profile", "default") or "default"),
        enable_audio_noise_suppression=bool(snapshot.get("enable_audio_noise_suppression", False)),
        enable_capture_relisten=bool(snapshot.get("enable_capture_relisten", True)),
        enable_dictionary_bias=bool(snapshot.get("enable_dictionary_bias", True)),
        critical_prompt_catalog=critical_catalog,
    )


def load_profile_snapshot() -> Optional[dict[str, Any]]:
    profile = load_profile()
    if not profile:
        return None
    return profile.to_snapshot()


def save_profile_snapshot(snapshot: Mapping[str, Any]) -> None:
    save_profile(profile_from_snapshot(snapshot))
