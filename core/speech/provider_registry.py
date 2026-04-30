"""Provider registry and availability evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    SPEAKKIT_PROVIDER_ID,
    ProviderAvailabilityState,
    ProviderAvailability,
    SpeechProviderProfile,
    SpeechToTextService,
    TextToSpeechService,
    WakeService,
    normalize_provider_id,
    provider_requires_network,
)
from core.speech.legacy_stt import LegacySpeechToTextAdapter
from core.speech.legacy_tts import LegacyTextToSpeechAdapter
from core.speech.legacy_wake import LegacyWakeService
from core.speech.speakkit_stt import SpeakKitSpeechToTextAdapter
from core.speech.speakkit_tts import SpeakKitTextToSpeechAdapter
from core.speech.speakkit_wake import SpeakKitWakeService


def _service_is_available(service: Any) -> bool:
    checker = getattr(service, "is_available", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:  # noqa: BLE001
            return False
    return service is not None


def _supports_structured_recognition(service: Any) -> bool:
    listener = getattr(service, "listen_command_result", None)
    return callable(listener)


def _provider_availability_state(service: Any) -> dict[str, Any]:
    probe = getattr(service, "provider_availability_state", None)
    if callable(probe):
        try:
            payload = probe()
            if isinstance(payload, ProviderAvailabilityState):
                return payload.to_dict()
            if isinstance(payload, dict):
                return dict(payload)
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _recognition_configuration_snapshot(service: Any) -> dict[str, Any]:
    probe = getattr(service, "recognition_configuration_snapshot", None)
    if callable(probe):
        try:
            payload = probe()
            if isinstance(payload, dict):
                return dict(payload)
        except Exception:  # noqa: BLE001
            return {}
    return {}


@dataclass
class ProviderBundle:
    profile: SpeechProviderProfile
    wake_service: WakeService
    stt_service: SpeechToTextService
    tts_service: TextToSpeechService

    def availability(self) -> ProviderAvailability:
        checks = (
            _service_is_available(self.wake_service),
            _service_is_available(self.stt_service),
            _service_is_available(self.tts_service),
        )
        if all(checks):
            return ProviderAvailability.READY
        if any(checks):
            return ProviderAvailability.DEGRADED
        return ProviderAvailability.UNAVAILABLE


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderBundle] = {}

    def register(self, bundle: ProviderBundle, *, replace_existing: bool = False) -> None:
        provider_id = normalize_provider_id(bundle.profile.provider_id)
        if provider_id in self._providers and not replace_existing:
            raise ValueError(f"Provider '{provider_id}' already registered")
        self._providers[provider_id] = bundle

    def get(self, provider_id: str) -> ProviderBundle | None:
        return self._providers.get(normalize_provider_id(provider_id))

    def require(self, provider_id: str) -> ProviderBundle:
        bundle = self.get(provider_id)
        if bundle is None:
            raise KeyError(f"Provider '{provider_id}' is not registered")
        return bundle

    def has(self, provider_id: str) -> bool:
        return normalize_provider_id(provider_id) in self._providers

    def list_provider_ids(self) -> list[str]:
        return sorted(self._providers.keys())

    def list_profiles(self) -> list[SpeechProviderProfile]:
        return [self._providers[provider_id].profile for provider_id in self.list_provider_ids()]

    def get_availability(self, provider_id: str) -> ProviderAvailability:
        bundle = self.get(provider_id)
        if bundle is None:
            return ProviderAvailability.UNAVAILABLE
        return bundle.availability()

    def is_available(self, provider_id: str) -> bool:
        return self.get_availability(provider_id) != ProviderAvailability.UNAVAILABLE

    def is_ready(self, provider_id: str) -> bool:
        return self.get_availability(provider_id) == ProviderAvailability.READY

    def availability_matrix(self) -> dict[str, ProviderAvailability]:
        return {provider_id: self.get_availability(provider_id) for provider_id in self.list_provider_ids()}

    def requires_network(self, provider_id: str) -> bool:
        bundle = self.get(provider_id)
        if bundle is None:
            return False
        return provider_requires_network(bundle.profile)

    def provider_metadata(self, provider_id: str) -> dict[str, Any]:
        bundle = self.require(provider_id)
        availability = bundle.availability()
        availability_state = _provider_availability_state(bundle.stt_service)
        recognition_snapshot = _recognition_configuration_snapshot(bundle.stt_service)
        return {
            "provider_id": bundle.profile.provider_id,
            "display_name": bundle.profile.display_name,
            "requires_network": provider_requires_network(bundle.profile),
            "availability": availability.value,
            "supports_wake": bundle.profile.supports_wake,
            "supports_stt": bundle.profile.supports_stt,
            "supports_tts": bundle.profile.supports_tts,
            "supports_structured_recognition": _supports_structured_recognition(bundle.stt_service),
            "supports_capture_profiles": _supports_structured_recognition(bundle.stt_service),
            "startup_timeout_s": bundle.profile.startup_timeout_s,
            "stt_provider_availability_state": availability_state,
            "recognition_configuration": recognition_snapshot,
        }

    def wake_source_snapshot(self, provider_id: str) -> dict[str, Any]:
        bundle = self.require(provider_id)
        availability = bundle.availability()
        wake_available = _service_is_available(bundle.wake_service)
        stt_available = _service_is_available(bundle.stt_service)
        recognition_snapshot = _recognition_configuration_snapshot(bundle.stt_service)
        supports_mode = getattr(bundle.wake_service, "supports_mode", None)
        keyword_available_probe = getattr(bundle.wake_service, "keyword_wake_available", None)
        hardware_available_probe = getattr(bundle.wake_service, "hardware_trigger_available", None)

        def _supports(mode: str) -> bool:
            if callable(supports_mode):
                try:
                    return bool(supports_mode(mode))
                except Exception:  # noqa: BLE001
                    return False
            return wake_available

        keyword_wake_available = bool(wake_available and _supports("keyword_low_power"))
        if callable(keyword_available_probe):
            try:
                keyword_wake_available = bool(wake_available and keyword_available_probe())
            except Exception:  # noqa: BLE001
                keyword_wake_available = bool(wake_available and _supports("keyword_low_power"))

        hardware_trigger_available = bool(wake_available and _supports("hardware_trigger"))
        if callable(hardware_available_probe):
            try:
                hardware_trigger_available = bool(wake_available and hardware_available_probe())
            except Exception:  # noqa: BLE001
                hardware_trigger_available = bool(wake_available and _supports("hardware_trigger"))

        return {
            "provider_id": bundle.profile.provider_id,
            "provider_availability": availability.value,
            "keyword_wake_available": keyword_wake_available,
            "hardware_trigger_available": hardware_trigger_available,
            "stt_wake_available": bool(stt_available),
            "strict_local_wake_fallback_available": bool(
                recognition_snapshot.get("strict_vosk_fallback_enabled", False)
            ),
        }

    def metadata_matrix(self) -> dict[str, dict[str, Any]]:
        return {
            provider_id: self.provider_metadata(provider_id)
            for provider_id in self.list_provider_ids()
        }


def create_default_provider_registry(
    *,
    default_language: str,
    listener_factory: Callable[..., Any],
    tts_engine_factory: Callable[[], Any],
    wake_detector_factory: Callable[[], Any],
    speakkit_listener_factory: Callable[..., Any] | None = None,
    speakkit_tts_factory: Callable[[], Any] | None = None,
    speakkit_wake_factory: Callable[[], Any] | None = None,
) -> ProviderRegistry:
    registry = ProviderRegistry()
    legacy_listener = listener_factory(default_language=default_language)
    legacy_wake_detector = wake_detector_factory()

    legacy_bundle = ProviderBundle(
        profile=SpeechProviderProfile(
            provider_id=LEGACY_PROVIDER_ID,
            display_name="Legacy (On-Device First)",
            supports_wake=True,
            supports_stt=True,
            supports_tts=True,
            requires_network=False,
        ),
        wake_service=LegacyWakeService(
            detector=legacy_wake_detector,
            listener=legacy_listener,
        ),
        stt_service=LegacySpeechToTextAdapter(
            listener=legacy_listener,
            default_language=default_language,
        ),
        tts_service=LegacyTextToSpeechAdapter(tts_engine=tts_engine_factory()),
    )
    registry.register(legacy_bundle)

    speakkit_listener = None
    speakkit_tts = None
    speakkit_wake = None

    if speakkit_listener_factory is not None:
        speakkit_listener = speakkit_listener_factory(default_language=default_language)
    if speakkit_tts_factory is not None:
        speakkit_tts = speakkit_tts_factory()
    if speakkit_wake_factory is not None:
        speakkit_wake = speakkit_wake_factory()

    speakkit_bundle = ProviderBundle(
        profile=SpeechProviderProfile(
            provider_id=SPEAKKIT_PROVIDER_ID,
            display_name="SpeakKit",
            supports_wake=True,
            supports_stt=True,
            supports_tts=True,
            requires_network=True,
        ),
        wake_service=SpeakKitWakeService(backend=speakkit_wake, available=speakkit_wake is not None),
        stt_service=SpeakKitSpeechToTextAdapter(
            backend=speakkit_listener,
            default_language=default_language,
            available=speakkit_listener is not None,
        ),
        tts_service=SpeakKitTextToSpeechAdapter(backend=speakkit_tts, available=speakkit_tts is not None),
    )
    registry.register(speakkit_bundle)

    return registry
