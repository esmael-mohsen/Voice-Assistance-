"""Unit coverage for provider registry behavior."""

from __future__ import annotations

from core.command_models import CommandRecognitionResult
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, ProviderAvailability, SpeechProviderProfile
from core.speech.legacy_stt import LegacySpeechToTextAdapter
from core.speech.provider_registry import ProviderBundle, ProviderRegistry, create_default_provider_registry


class _Service:
    def __init__(self, *, available: bool = True) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):  # pragma: no cover - protocol shape helper
        return None

    def listen_command(self):  # pragma: no cover - protocol shape helper
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):  # pragma: no cover
        return None

    def set_language(self, _language):  # pragma: no cover
        return None

    def set_voice_gender(self, _gender):  # pragma: no cover
        return None

    def set_speech_speed(self, _speed):  # pragma: no cover
        return None

    def speak(self, _text):  # pragma: no cover
        return None

    def configure(self, **_kwargs):  # pragma: no cover
        return None

    def provider_availability_state(self):  # pragma: no cover - protocol helper
        return {
            "provider_source": "cloud_primary",
            "availability": "ready" if self._available else "unavailable",
            "credential_state": "not_required",
            "client_import_state": "available",
            "network_required": False,
            "startup_safe": True,
            "reason_code": None if self._available else "provider_unavailable",
            "checked_at_ms": 0,
        }

    def recognition_configuration_snapshot(self):  # pragma: no cover - protocol helper
        return {
            "cloud_primary_enabled": False,
            "strict_vosk_fallback_enabled": False,
            "sphinx_compat_enabled": False,
            "cloud_timeout_s": 3.0,
            "cloud_max_alternatives": 3,
            "selected_profile_language": "en-US",
            "configured_from_environment": True,
            "field_safe": True,
            "credential_material_present": False,
        }


def _bundle(provider_id: str, *, wake_available: bool, stt_available: bool, tts_available: bool) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(provider_id=provider_id, display_name=provider_id.title()),
        wake_service=_Service(available=wake_available),
        stt_service=_Service(available=stt_available),
        tts_service=_Service(available=tts_available),
    )


def test_registry_registers_and_retrieves_bundle() -> None:
    registry = ProviderRegistry()
    legacy = _bundle(LEGACY_PROVIDER_ID, wake_available=True, stt_available=True, tts_available=True)
    registry.register(legacy)

    assert registry.has(LEGACY_PROVIDER_ID)
    assert registry.require(LEGACY_PROVIDER_ID).profile.provider_id == LEGACY_PROVIDER_ID
    assert registry.list_provider_ids() == [LEGACY_PROVIDER_ID]


def test_registry_reports_ready_degraded_and_unavailable_states() -> None:
    registry = ProviderRegistry()
    registry.register(_bundle("ready", wake_available=True, stt_available=True, tts_available=True))
    registry.register(_bundle("degraded", wake_available=True, stt_available=False, tts_available=True))
    registry.register(_bundle("down", wake_available=False, stt_available=False, tts_available=False))

    assert registry.get_availability("ready") == ProviderAvailability.READY
    assert registry.get_availability("degraded") == ProviderAvailability.DEGRADED
    assert registry.get_availability("down") == ProviderAvailability.UNAVAILABLE


def test_default_registry_contains_legacy_and_speakkit_paths(
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    registry = create_default_provider_registry(
        default_language="en-US",
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
    )

    ids = registry.list_provider_ids()
    assert LEGACY_PROVIDER_ID in ids
    assert SPEAKKIT_PROVIDER_ID in ids
    assert registry.is_ready(LEGACY_PROVIDER_ID) is True
    assert registry.is_available(SPEAKKIT_PROVIDER_ID) is False
    assert registry.requires_network(LEGACY_PROVIDER_ID) is False
    assert registry.requires_network(SPEAKKIT_PROVIDER_ID) is True


def test_provider_network_metadata_is_authoritative() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(
                provider_id="networked",
                display_name="Networked",
                requires_network=True,
            ),
            wake_service=_Service(available=True),
            stt_service=_Service(available=True),
            tts_service=_Service(available=True),
        )
    )
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(
                provider_id="local",
                display_name="Local",
                requires_network=False,
            ),
            wake_service=_Service(available=True),
            stt_service=_Service(available=True),
            tts_service=_Service(available=True),
        )
    )

    assert registry.requires_network("networked") is True
    assert registry.requires_network("local") is False


def test_registry_wake_source_snapshot_reports_availability_flags() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id="wake", display_name="Wake"),
            wake_service=_Service(available=True),
            stt_service=_Service(available=False),
            tts_service=_Service(available=True),
        )
    )
    snapshot = registry.wake_source_snapshot("wake")
    assert snapshot["provider_id"] == "wake"
    assert snapshot["keyword_wake_available"] is True
    assert snapshot["hardware_trigger_available"] is True
    assert snapshot["stt_wake_available"] is False


def test_registry_wake_source_snapshot_prefers_explicit_wake_capability_probes() -> None:
    class _WakeServiceWithProbes(_Service):
        def keyword_wake_available(self) -> bool:
            return False

        def hardware_trigger_available(self) -> bool:
            return False

        def supports_mode(self, _wake_mode: str) -> bool:
            return True

    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id="wake-probed", display_name="Wake Probed"),
            wake_service=_WakeServiceWithProbes(available=True),
            stt_service=_Service(available=True),
            tts_service=_Service(available=True),
        )
    )
    snapshot = registry.wake_source_snapshot("wake-probed")
    assert snapshot["keyword_wake_available"] is False
    assert snapshot["hardware_trigger_available"] is False


def test_provider_metadata_includes_availability_state_and_recognition_snapshot() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id="meta", display_name="Meta"),
            wake_service=_Service(available=True),
            stt_service=_Service(available=True),
            tts_service=_Service(available=True),
        )
    )
    metadata = registry.provider_metadata("meta")
    assert metadata["stt_provider_availability_state"]["provider_source"] == "cloud_primary"
    assert metadata["recognition_configuration"]["cloud_timeout_s"] == 3.0
    assert metadata["recognition_configuration"]["credential_material_present"] is False


def test_legacy_adapter_preserves_cloud_primary_metadata_when_listener_returns_structured_result() -> None:
    class _StructuredListener:
        language = "en-US"

        def listen_command_result(self, **_kwargs):
            return CommandRecognitionResult(
                session_id="session-cloud",
                recognition_path="local_first",
                provider_id="legacy",
                primary_transcript="start obstacle detection",
                confidence_available=True,
                confidence_score=0.9,
                alternative_transcripts=("start obstacle detection",),
                detected_language="en-US",
                selected_language="en-US",
                latency_ms=12,
                error_code=None,
                recognition_source="cloud_primary",
            )

    adapter = LegacySpeechToTextAdapter(listener=_StructuredListener(), default_language="en-US")
    result = adapter.listen_command_result(timeout=1, phrase_time_limit=1)
    assert result is not None
    assert result.recognition_source == "cloud_primary"
    assert result.primary_transcript == "start obstacle detection"
