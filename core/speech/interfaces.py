"""Contracts for provider-agnostic speech services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, Sequence, runtime_checkable

from core.command_models import CommandRecognitionResult

LEGACY_PROVIDER_ID = "legacy"
SPEAKKIT_PROVIDER_ID = "speakkit"
SUPPORTED_PROVIDER_IDS = frozenset({LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID})
WAKE_MODE_KEYWORD_LOW_POWER = "keyword_low_power"
WAKE_MODE_HARDWARE_TRIGGER = "hardware_trigger"
WAKE_MODE_STT_BASED = "stt_based_wake"
SUPPORTED_WAKE_MODES = frozenset(
    {
        WAKE_MODE_KEYWORD_LOW_POWER,
        WAKE_MODE_HARDWARE_TRIGGER,
        WAKE_MODE_STT_BASED,
    }
)


class ProviderAvailability(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


def normalize_provider_id(provider_id: str | None) -> str:
    cleaned = (provider_id or "").strip().lower()
    if not cleaned:
        return LEGACY_PROVIDER_ID
    return cleaned


@runtime_checkable
class WakeService(Protocol):
    def detect(self, input_text: str) -> Any:
        """Return wake-detection result, or None when no wake action is found."""

    def wait_for_wake(
        self,
        *,
        timeout_s: float = 1.0,
        wake_mode: str | None = None,
    ) -> Any:
        """Wait for a wake signal from provider-owned wake boundaries."""

    def supports_mode(self, wake_mode: str) -> bool:
        """Return True when this wake service can handle the requested wake mode."""


@runtime_checkable
class SpeechToTextService(Protocol):
    def listen_command(self, **kwargs: Any) -> str | None:
        """Capture a command utterance."""

    def listen_command_result(self, **kwargs: Any) -> CommandRecognitionResult | None:
        """Capture a command utterance with structured metadata."""

    def listen_any(
        self,
        languages: Sequence[str],
        prompt: str = "[STT] Listening...",
        timeout: int = 7,
        phrase_time_limit: int = 10,
    ) -> str | None:
        """Capture speech and try recognition for multiple languages."""

    def set_language(self, language_code: str) -> None:
        """Apply runtime language preference."""

    def provider_availability_state(self) -> dict[str, Any]:
        """Return provider-availability metadata for diagnostics."""

    def recognition_configuration_snapshot(self) -> dict[str, Any]:
        """Return field-safe recognition configuration controls."""


@dataclass(frozen=True)
class SpeechRecognitionContext:
    usage_mode: str = "command"
    capture_profile_id: str | None = None
    dictionary_bias_mode: str | None = None
    closed_vocabulary_id: str | None = None
    qualification_profile_id: str = "default"


@dataclass(frozen=True)
class ProviderAvailabilityState:
    provider_source: str
    availability: str
    credential_state: str
    client_import_state: str
    network_required: bool
    startup_safe: bool
    reason_code: str | None = None
    checked_at_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_source": self.provider_source,
            "availability": self.availability,
            "credential_state": self.credential_state,
            "client_import_state": self.client_import_state,
            "network_required": bool(self.network_required),
            "startup_safe": bool(self.startup_safe),
            "reason_code": self.reason_code,
            "checked_at_ms": max(0, int(self.checked_at_ms)),
        }


@runtime_checkable
class TextToSpeechService(Protocol):
    def speak(self, text: str, **kwargs: Any) -> Any:
        """Synthesize and play spoken text."""

    def set_language(self, language_code: str) -> None:
        """Apply runtime language preference."""

    def set_voice_gender(self, gender: str) -> None:
        """Apply runtime voice-gender preference."""

    def set_speech_speed(self, speed: float) -> None:
        """Apply runtime speech-speed preference."""


@dataclass(frozen=True)
class SpeechProviderProfile:
    provider_id: str
    display_name: str
    supports_wake: bool = True
    supports_stt: bool = True
    supports_tts: bool = True
    requires_network: bool = False
    availability: ProviderAvailability = ProviderAvailability.READY
    startup_timeout_s: float = 5.0

    def __post_init__(self) -> None:
        if self.startup_timeout_s <= 0:
            raise ValueError("startup_timeout_s must be positive")
        normalized_id = normalize_provider_id(self.provider_id)
        object.__setattr__(self, "provider_id", normalized_id)


@dataclass(frozen=True)
class WakeCapabilityDescriptor:
    provider_id: str
    wake_modes_supported: tuple[str, ...]
    default_wake_mode: str = WAKE_MODE_KEYWORD_LOW_POWER
    fallback_wake_mode: str = WAKE_MODE_HARDWARE_TRIGGER
    dev_only_wake_mode: str = WAKE_MODE_STT_BASED

    def __post_init__(self) -> None:
        normalized_id = normalize_provider_id(self.provider_id)
        object.__setattr__(self, "provider_id", normalized_id)
        unsupported = set(self.wake_modes_supported) - SUPPORTED_WAKE_MODES
        if unsupported:
            raise ValueError(f"Unsupported wake mode(s): {sorted(unsupported)}")
        if self.default_wake_mode not in SUPPORTED_WAKE_MODES:
            raise ValueError("default_wake_mode is invalid")
        if self.fallback_wake_mode not in SUPPORTED_WAKE_MODES:
            raise ValueError("fallback_wake_mode is invalid")
        if self.dev_only_wake_mode not in SUPPORTED_WAKE_MODES:
            raise ValueError("dev_only_wake_mode is invalid")


def default_wake_policy() -> WakeCapabilityDescriptor:
    return WakeCapabilityDescriptor(
        provider_id=LEGACY_PROVIDER_ID,
        wake_modes_supported=(
            WAKE_MODE_KEYWORD_LOW_POWER,
            WAKE_MODE_HARDWARE_TRIGGER,
            WAKE_MODE_STT_BASED,
        ),
        default_wake_mode=WAKE_MODE_KEYWORD_LOW_POWER,
        fallback_wake_mode=WAKE_MODE_HARDWARE_TRIGGER,
        dev_only_wake_mode=WAKE_MODE_STT_BASED,
    )


def provider_requires_network(profile: SpeechProviderProfile) -> bool:
    """Authoritative accessor for provider network requirements."""
    return bool(profile.requires_network)
