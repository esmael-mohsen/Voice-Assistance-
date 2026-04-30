"""Speech provider abstractions and adapters."""

from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    SPEAKKIT_PROVIDER_ID,
    ProviderAvailabilityState,
    ProviderAvailability,
    SpeechProviderProfile,
    SpeechRecognitionContext,
    SpeechToTextService,
    TextToSpeechService,
    WakeService,
    normalize_provider_id,
)
from core.speech.provider_registry import ProviderBundle, ProviderRegistry, create_default_provider_registry
from core.speech.provider_resolver import (
    FailureResolution,
    ProviderSwitchDecision,
    StartupResolution,
    resolve_provider_switch_request,
    resolve_runtime_failure,
    resolve_startup_provider,
)

__all__ = [
    "LEGACY_PROVIDER_ID",
    "SPEAKKIT_PROVIDER_ID",
    "ProviderAvailability",
    "ProviderAvailabilityState",
    "SpeechProviderProfile",
    "SpeechRecognitionContext",
    "SpeechToTextService",
    "TextToSpeechService",
    "WakeService",
    "normalize_provider_id",
    "ProviderBundle",
    "ProviderRegistry",
    "create_default_provider_registry",
    "FailureResolution",
    "ProviderSwitchDecision",
    "StartupResolution",
    "resolve_provider_switch_request",
    "resolve_runtime_failure",
    "resolve_startup_provider",
]
