"""Shared assistant runtime models and execution engine."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from core import parser as command_parser
from core.command_post_processing import process_command_transcript
from core.command_models import (
    CommandExecutionResult,
    GuidedDialogOutcome,
    CommandRecognitionResult,
    CommandPostProcessingOutcome,
    ConfidenceDecisionOutcome,
    ConfidenceDecisionPolicy,
    InFlightOperationContext,
    InterruptDetectionResult,
    InteractionPriorityEvent,
    ParsedCommandIntent,
    RecognitionTelemetrySample,
    RuntimeRecoveryOutcome,
    TurnTakingWindowOutcome,
    StandbyWakeOutcome,
    WakePolicySelection,
    coalesce_priority_events,
)
from core.closed_vocabulary import (
    closed_vocabulary_choices,
    closed_vocabulary_context,
    is_global_safety_preemption,
    match_closed_vocabulary,
)
from core.dialog_policy import is_affirmative
from core.runtime_diagnostics import attach_runtime_diagnostic_fields
from core.release_metrics import (
    build_failure_scenario_from_event,
    classify_stt_confidence_bucket,
    classify_stt_failure_category,
    classify_stt_latency_bucket,
    classify_stt_recovery_outcome,
    clear_runtime_latency_metrics,
    get_runtime_latency_metrics,
    record_stt_failure_scenario_result,
    record_stt_observability_event,
    record_audio_qualification_run,
    record_interrupt_preemption,
    record_runtime_state_transition,
)
from core.release_models import SttTelemetryEventRecord
from core.turn_taking import (
    build_turn_window,
    listening_status_for_window,
)
from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    ProviderAvailability,
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
)
from core.speech.network_probe import TCPNetworkProbe
from core.speech.provider_registry import ProviderBundle, ProviderRegistry, create_default_provider_registry
from core.speech.provider_resolver import (
    DUAL_PROVIDER_UNAVAILABLE_REASON,
    NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON,
    STARTUP_UNAVAILABLE_REASON,
    connectivity_state_from_snapshot,
    evaluate_offline_execution_policy,
    resolve_provider_switch_request,
    resolve_runtime_failure,
    resolve_startup_provider,
    resolve_wake_mode,
)
from core.wake_word import (
    CANONICAL_WAKE_PHRASES,
    WakeAction,
    detect_interrupt_signal,
    detect_wake,
    normalize_wake_phrase,
)
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)

_INTERRUPT_INTENTS: tuple[str, ...] = ("stop", "cancel", "emergency")
_INTERRUPT_SURFACE_IDS: dict[str, str] = {
    "stop": "runtime.interrupt.stop",
    "cancel": "runtime.interrupt.cancel",
    "emergency": "runtime.interrupt.emergency",
}


class RuntimeMode(str, Enum):
    GUI = "gui"
    CONSOLE = "console"


class RuntimeState(str, Enum):
    STANDBY = "standby"
    WAKE = "wake"
    SETUP = "setup"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
    OFFLINE = "offline"
    ONLINE = "online"  # migration compatibility
    STOPPING = "stopping"  # migration compatibility


CANONICAL_RUNTIME_STATES: frozenset[RuntimeState] = frozenset(
    {
        RuntimeState.STANDBY,
        RuntimeState.WAKE,
        RuntimeState.SETUP,
        RuntimeState.LISTENING,
        RuntimeState.THINKING,
        RuntimeState.SPEAKING,
        RuntimeState.ERROR,
        RuntimeState.OFFLINE,
    }
)


ACTIVE_RUNTIME_STATES: frozenset[RuntimeState] = frozenset(
    {
        RuntimeState.WAKE,
        RuntimeState.SETUP,
        RuntimeState.LISTENING,
        RuntimeState.THINKING,
        RuntimeState.SPEAKING,
        RuntimeState.ONLINE,
    }
)


class RuntimeEventType(str, Enum):
    STATUS = "status"
    SYSTEM = "system"
    CONFIG = "config"
    USER = "user"
    ASSISTANT = "assistant"
    ERROR = "error"


class UnrecoverableRuntimeError(RuntimeError):
    """Exception type for runtime failures that must transition to offline."""


class OnboardingStep(str, Enum):
    LANGUAGE = "language"
    VOICE = "voice"
    SPEED = "speed"
    NAME = "name"
    CONFIRMATION = "confirmation"
    COMPLETE = "complete"


@dataclass(frozen=True)
class SettingsSnapshot:
    language: str
    voice_gender: str
    speech_speed: float
    username: str = ""
    speech_provider: str = LEGACY_PROVIDER_ID
    pending_speech_provider: str | None = None
    deferred_provider_switch: bool = False
    max_listen_seconds: float = 8.0
    max_speak_seconds: float = 8.0
    priority_coalescing_window_s: float = 2.0
    concise_word_limit: int = 12
    wake_primary_mode: str = WAKE_MODE_KEYWORD_LOW_POWER
    wake_fallback_mode: str = WAKE_MODE_HARDWARE_TRIGGER
    wake_dev_fallback_mode: str = "stt_based_wake"
    stt_wake_allowed_in_production: bool = False
    low_power_standby_enabled: bool = True
    non_speech_cues_enabled: bool = True
    network_available: bool = True
    network_override_mode: str = "auto"
    connectivity_detected_status: str = "online"
    connectivity_last_confirmed_status: str = "online"
    connectivity_last_confirmed_at: float | None = None
    connectivity_grace_window_deadline_at: float | None = None
    connectivity_probe_generation: int = 0
    connectivity_startup_reset_applied: bool = False
    connectivity_grace_window_s: float = 2.0
    offline_allowlisted_capabilities: tuple[str, ...] = ("system_status",)
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
    stt_rollout_requested_mode: str = "shadow"
    stt_rollout_effective_mode: str = "shadow"
    stt_rollout_rollback_override_active: bool = False
    stt_rollout_rollback_reason_code: str | None = None

    def __post_init__(self) -> None:
        if not self.language:
            raise ValueError("language is required")
        if not self.voice_gender:
            raise ValueError("voice_gender is required")
        if self.speech_speed <= 0:
            raise ValueError("speech_speed must be positive")
        if not self.speech_provider:
            raise ValueError("speech_provider is required")
        if self.max_listen_seconds <= 0:
            raise ValueError("max_listen_seconds must be positive")
        if self.max_speak_seconds <= 0:
            raise ValueError("max_speak_seconds must be positive")
        if self.priority_coalescing_window_s <= 0:
            raise ValueError("priority_coalescing_window_s must be positive")
        if self.concise_word_limit <= 0:
            raise ValueError("concise_word_limit must be positive")
        if self.connectivity_grace_window_s <= 0:
            raise ValueError("connectivity_grace_window_s must be positive")
        if self.command_confidence_high_threshold < self.command_confidence_medium_threshold:
            raise ValueError("command_confidence_high_threshold must be >= medium threshold")
        if self.command_protected_threshold < self.command_confidence_high_threshold:
            raise ValueError("command_protected_threshold must be >= high threshold")
        if self.command_max_retry_cycles < 0:
            raise ValueError("command_max_retry_cycles must be non-negative")
        if self.closed_vocabulary_retry_limit <= 0:
            raise ValueError("closed_vocabulary_retry_limit must be positive")


@dataclass
class ProviderSelectionState:
    persisted_provider: str = LEGACY_PROVIDER_ID
    session_provider: str = LEGACY_PROVIDER_ID
    pending_provider: str | None = None
    deferred_until_restart: bool = False
    degraded_mode: bool = False
    degraded_reason: str | None = None
    fallback_from: str | None = None
    fallback_to: str | None = None


@dataclass(frozen=True)
class OnboardingState:
    required: bool = True
    selected_language: str | None = None
    selected_voice_gender: str | None = None
    selected_speech_speed: float | None = None
    proposed_username: str | None = None
    confirmed_username: str | None = None
    step: OnboardingStep = OnboardingStep.LANGUAGE

    def with_step(self, step: OnboardingStep) -> "OnboardingState":
        return replace(self, step=step)

    def mark_complete(self, username: str) -> "OnboardingState":
        cleaned_username = (username or "").strip()
        if not cleaned_username:
            raise ValueError("username is required to complete onboarding")
        return replace(
            self,
            required=False,
            proposed_username=cleaned_username,
            confirmed_username=cleaned_username,
            step=OnboardingStep.COMPLETE,
        )


@dataclass(frozen=True)
class RuntimeEvent:
    type: RuntimeEventType
    session_id: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dictionary")


@dataclass(frozen=True)
class RuntimeObserverModel:
    observer_id: str
    mode: RuntimeMode
    supported_event_types: frozenset[RuntimeEventType] = field(
        default_factory=lambda: frozenset(RuntimeEventType)
    )

    def accepts(self, event_type: RuntimeEventType) -> bool:
        return event_type in self.supported_event_types


@dataclass
class RuntimeSession:
    mode: RuntimeMode
    session_id: str = field(default_factory=lambda: uuid4().hex)
    state: RuntimeState = RuntimeState.OFFLINE
    configured: bool = False
    active: bool = False
    language: str = "en-US"
    voice_gender: str = "female"
    speech_speed: float = 1.0
    stop_requested: bool = False
    last_error: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.mode, str):
            self.mode = RuntimeMode(self.mode)
        if isinstance(self.state, str):
            self.state = RuntimeState(self.state)
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.speech_speed <= 0:
            raise ValueError("speech_speed must be positive")

    def can_transition_to(self, next_state: RuntimeState | str) -> bool:
        if isinstance(next_state, str):
            next_state = RuntimeState(next_state)

        if next_state == self.state:
            return True

        allowed_next = ALLOWED_STATE_TRANSITIONS.get(self.state, frozenset())
        return next_state in allowed_next

    def transition_to(self, next_state: RuntimeState | str) -> RuntimeState:
        if isinstance(next_state, str):
            next_state = RuntimeState(next_state)

        if not self.can_transition_to(next_state):
            raise ValueError(f"Invalid runtime transition: {self.state.value} -> {next_state.value}")

        self.state = next_state
        self.active = next_state in ACTIVE_RUNTIME_STATES
        self.stop_requested = next_state in {RuntimeState.STOPPING, RuntimeState.OFFLINE}
        return self.state

    def apply_settings(self, snapshot: SettingsSnapshot) -> None:
        self.language = snapshot.language
        self.voice_gender = snapshot.voice_gender
        self.speech_speed = snapshot.speech_speed
        self.configured = bool(snapshot.username.strip())


ALLOWED_STATE_TRANSITIONS: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.OFFLINE: frozenset({RuntimeState.STANDBY}),
    RuntimeState.STANDBY: frozenset(
        {RuntimeState.WAKE, RuntimeState.ERROR, RuntimeState.OFFLINE, RuntimeState.STOPPING}
    ),
    RuntimeState.WAKE: frozenset(
        {RuntimeState.SETUP, RuntimeState.LISTENING, RuntimeState.ERROR, RuntimeState.OFFLINE}
    ),
    RuntimeState.SETUP: frozenset({RuntimeState.LISTENING, RuntimeState.ERROR, RuntimeState.OFFLINE}),
    RuntimeState.LISTENING: frozenset(
        {RuntimeState.THINKING, RuntimeState.STANDBY, RuntimeState.ERROR, RuntimeState.OFFLINE}
    ),
    RuntimeState.THINKING: frozenset(
        {RuntimeState.SPEAKING, RuntimeState.STANDBY, RuntimeState.ERROR, RuntimeState.OFFLINE}
    ),
    RuntimeState.SPEAKING: frozenset(
        {RuntimeState.LISTENING, RuntimeState.STANDBY, RuntimeState.ERROR, RuntimeState.OFFLINE}
    ),
    RuntimeState.ERROR: frozenset({RuntimeState.STANDBY, RuntimeState.OFFLINE}),
    RuntimeState.ONLINE: frozenset(
        {
            RuntimeState.LISTENING,
            RuntimeState.THINKING,
            RuntimeState.SPEAKING,
            RuntimeState.STANDBY,
            RuntimeState.ERROR,
            RuntimeState.STOPPING,
            RuntimeState.OFFLINE,
        }
    ),
    RuntimeState.STOPPING: frozenset({RuntimeState.OFFLINE}),
}


_COMPATIBILITY_STATE_MAP: dict[RuntimeState, RuntimeState] = {
    RuntimeState.ONLINE: RuntimeState.LISTENING,
    RuntimeState.STOPPING: RuntimeState.OFFLINE,
}


def truncate_to_word_limit(text: str, *, word_limit: int) -> str:
    clean = str(text or "").strip()
    if not clean or word_limit <= 0:
        return ""
    words = clean.split()
    if len(words) <= word_limit:
        return clean
    return " ".join(words[:word_limit]).strip()


def map_non_speech_cue(runtime_state: str) -> str | None:
    state = str(runtime_state or "").strip().lower()
    cue_map = {
        "ready": "tone_ready",
        "standby": "haptic_standby",
        "warning": "tone_warning",
        "error": "tone_error",
    }
    return cue_map.get(state)


def canonical_runtime_state(state: RuntimeState | str) -> RuntimeState:
    if isinstance(state, str):
        state = RuntimeState(state)
    return _COMPATIBILITY_STATE_MAP.get(state, state)


def build_event(
    event_type: RuntimeEventType | str,
    *,
    session_id: str,
    payload: dict[str, Any],
) -> RuntimeEvent:
    if isinstance(event_type, str):
        event_type = RuntimeEventType(event_type)
    return RuntimeEvent(type=event_type, session_id=session_id, payload=dict(payload))


def status_event(session: RuntimeSession, state: RuntimeState | str) -> RuntimeEvent:
    if isinstance(state, str):
        state = RuntimeState(state)
    canonical_state = canonical_runtime_state(state)
    payload = {"state": canonical_state.value}
    if canonical_state != state:
        payload["raw_state"] = state.value
    return build_event(
        RuntimeEventType.STATUS,
        session_id=session.session_id,
        payload=payload,
    )


def config_event(
    session: RuntimeSession,
    snapshot: SettingsSnapshot,
    *,
    provider_state: ProviderSelectionState | None = None,
    stt_configuration: dict[str, Any] | None = None,
    stt_provider_availability_state: dict[str, Any] | None = None,
) -> RuntimeEvent:
    payload: dict[str, Any] = {
        "language": snapshot.language,
        "gender": snapshot.voice_gender,
        "speed": snapshot.speech_speed,
        "max_listen_seconds": snapshot.max_listen_seconds,
        "max_speak_seconds": snapshot.max_speak_seconds,
        "coalescing_window_s": snapshot.priority_coalescing_window_s,
        "wake_primary_mode": snapshot.wake_primary_mode,
        "wake_fallback_mode": snapshot.wake_fallback_mode,
        "override_mode": snapshot.network_override_mode,
        "detected_status": snapshot.connectivity_detected_status,
        "effective_network_available": snapshot.network_available,
        "last_confirmed_status": snapshot.connectivity_last_confirmed_status,
        "last_confirmed_at": snapshot.connectivity_last_confirmed_at,
        "grace_window_deadline_at": snapshot.connectivity_grace_window_deadline_at,
        "probe_generation": snapshot.connectivity_probe_generation,
        "startup_reset_applied": snapshot.connectivity_startup_reset_applied,
        "command_confidence_high_threshold": snapshot.command_confidence_high_threshold,
        "command_confidence_medium_threshold": snapshot.command_confidence_medium_threshold,
        "command_protected_threshold": snapshot.command_protected_threshold,
        "command_fallback_enabled": snapshot.command_fallback_enabled,
        "command_rescue_enabled": snapshot.command_rescue_enabled,
        "command_capture_profile_id": snapshot.command_capture_profile_id,
        "confirmation_capture_profile_id": snapshot.confirmation_capture_profile_id,
        "speech_qualification_profile": snapshot.speech_qualification_profile,
        "enable_capture_relisten": snapshot.enable_capture_relisten,
        "enable_dictionary_bias": snapshot.enable_dictionary_bias,
        "stt_rollout_requested_mode": snapshot.stt_rollout_requested_mode,
        "stt_rollout_effective_mode": snapshot.stt_rollout_effective_mode,
        "stt_rollout_rollback_override_active": snapshot.stt_rollout_rollback_override_active,
        "stt_rollout_rollback_reason_code": snapshot.stt_rollout_rollback_reason_code,
    }
    if stt_configuration:
        payload.update(
            {
                "stt_cloud_primary_enabled": bool(stt_configuration.get("cloud_primary_enabled", False)),
                "stt_strict_vosk_fallback_enabled": bool(
                    stt_configuration.get("strict_vosk_fallback_enabled", False)
                ),
                "stt_sphinx_compat_enabled": bool(stt_configuration.get("sphinx_compat_enabled", False)),
                "stt_cloud_timeout_s": float(stt_configuration.get("cloud_timeout_s", 3.0)),
                "stt_cloud_max_alternatives": int(stt_configuration.get("cloud_max_alternatives", 3)),
            }
        )
    if stt_provider_availability_state:
        payload["stt_provider_availability_state"] = dict(stt_provider_availability_state)
    if provider_state is not None:
        payload["speech_provider"] = provider_state.session_provider
        payload["persisted_speech_provider"] = provider_state.persisted_provider
        payload["provider_availability"] = "degraded" if provider_state.degraded_mode else "ready"
        if provider_state.pending_provider:
            payload["pending_speech_provider"] = provider_state.pending_provider
        if provider_state.deferred_until_restart:
            payload["deferred_provider_switch"] = True
        if provider_state.degraded_mode:
            payload["degraded_mode"] = True
            if provider_state.degraded_reason:
                payload["degraded_reason"] = provider_state.degraded_reason
        if provider_state.fallback_from:
            payload["fallback_from"] = provider_state.fallback_from
        if provider_state.fallback_to:
            payload["fallback_to"] = provider_state.fallback_to
        payload = attach_runtime_diagnostic_fields(
            payload,
            session_or_run_id=session.session_id,
            event_category="provider_selection",
            status_or_decision="degraded" if provider_state.degraded_mode else "selected",
            reason_code=provider_state.degraded_reason,
            provider_id=provider_state.session_provider,
            provider_availability=payload.get("provider_availability"),
            degraded_mode=provider_state.degraded_mode,
            degraded_reason=provider_state.degraded_reason,
            next_state=session.state.value,
        )
    return build_event(
        RuntimeEventType.CONFIG,
        session_id=session.session_id,
        payload=payload,
    )


def error_event(
    session: RuntimeSession,
    *,
    message: str,
    recoverable: bool,
    next_state: RuntimeState | str,
    provider: str | None = None,
    stage: str | None = None,
    fallback_applied: bool | None = None,
    fallback_to: str | None = None,
    manual_restart_required: bool | None = None,
    reason_code: str | None = None,
) -> RuntimeEvent:
    if isinstance(next_state, str):
        next_state = RuntimeState(next_state)
    payload: dict[str, Any] = {
        "message": message,
        "recoverable": recoverable,
        "next_state": next_state.value,
    }
    if provider:
        payload["provider"] = provider
    if stage:
        payload["stage"] = stage
    if fallback_applied is not None:
        payload["fallback_applied"] = fallback_applied
    if fallback_to:
        payload["fallback_to"] = fallback_to
    if manual_restart_required is not None:
        payload["manual_restart_required"] = manual_restart_required
    if reason_code:
        payload["reason_code"] = reason_code
    return build_event(
        RuntimeEventType.ERROR,
        session_id=session.session_id,
        payload=payload,
    )


RuntimeObserver = Callable[[RuntimeEvent], None]

_CLOSE_INTENT_WORDS = (
    "اقفل",
    "قفل",
    "قف",
    "وقف",
    "اخرج",
    "خروج",
    "انهاء",
    "انهي",
    "مع السلامة",
    "باي",
    "وداعا",
    "stop",
    "close",
    "quit",
    "exit",
    "shutdown",
    "goodbye",
    "bye",
)

_THANKS_INTENT_WORDS = ("شكراً", "شكرا", "شكر", "متشكر", "thanks", "thank you")
_PROTECTED_INTENTS: frozenset[str] = frozenset({"stop_system", "reset_settings"})
_CONFIDENCE_REASON_SURFACES: dict[str, str] = {
    "high_confidence": "runtime.command.execute",
    "missing_confidence_unprotected_allowed": "runtime.command.execute",
    "medium_confidence_normalized_execute": "runtime.command.execute",
    "offline_local_execute": "runtime.command.execute",
    "parser_rejected_recovery": "runtime.command.fallback",
    "language_mismatch_recovery": "runtime.command.fallback",
    "fallback_required": "runtime.command.fallback",
    "retry_required": "runtime.command.retry",
    "retry_exhausted": "runtime.command.refuse",
    "protected_confirmation_required": "resolver.confirmation.required",
    "low_confidence_refusal": "runtime.command.refuse",
    "fallback_unavailable": "runtime.command.refuse",
}


def _command_intent_family(intent_id: str | None) -> str | None:
    normalized = str(intent_id or "").strip().lower()
    if not normalized:
        return None
    if normalized.startswith("set_language_"):
        return "set_language"
    if normalized.startswith("set_voice_gender_"):
        return "set_voice_gender"
    return normalized


def _command_intents_materially_conflict(primary_intent: str | None, alternative_intent: str | None) -> bool:
    primary = str(primary_intent or "").strip().lower()
    alternative = str(alternative_intent or "").strip().lower()
    if not primary or not alternative or primary == alternative:
        return False

    primary_family = _command_intent_family(primary)
    alternative_family = _command_intent_family(alternative)
    if primary_family != alternative_family:
        return True

    generic_family_intents = {"set_language", "set_voice_gender"}
    return primary not in generic_family_intents and alternative not in generic_family_intents


def _default_dispatch(
    text: str,
    *,
    canonical_command_text: str | None = None,
    recognition_metadata: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> Any:
    from core.dispatcher import dispatch

    return dispatch(
        text,
        canonical_command_text=canonical_command_text,
        recognition_metadata=recognition_metadata,
        runtime_context=runtime_context,
    )


def _default_listener_factory(*, default_language: str) -> Any:
    from core.stt import VoiceListener

    return VoiceListener(
        default_language=default_language,
        prefer_offline=False,
        allow_cloud_fallback=True,
    )


def _default_tts_engine_factory() -> Any:
    from tts.tts_engine import TTSEngine

    return TTSEngine()


def _default_wake_detector_factory() -> Any:
    from core.wake_word import WakeWordDetector

    return WakeWordDetector()


class AssistantRuntime:
    """Shared assistant runtime loop for GUI and console observers."""

    def __init__(
        self,
        mode: RuntimeMode | str,
        observer: RuntimeObserver,
        *,
        default_language: str | None = None,
        settings_manager_obj: Any = None,
        listener_factory: Callable[..., Any] | None = None,
        tts_engine_factory: Callable[[], Any] | None = None,
        wake_detector_factory: Callable[[], Any] | None = None,
        provider_registry_obj: ProviderRegistry | None = None,
        network_probe: TCPNetworkProbe | None = None,
        speakkit_listener_factory: Callable[..., Any] | None = None,
        speakkit_tts_engine_factory: Callable[[], Any] | None = None,
        speakkit_wake_detector_factory: Callable[[], Any] | None = None,
        dispatcher: Callable[[str], Any] | None = None,
        max_onboarding_attempts: int = 6,
    ) -> None:
        self.mode = RuntimeMode(mode) if isinstance(mode, str) else mode
        self.observer = observer
        self.session = RuntimeSession(mode=self.mode)

        self._settings = settings_manager_obj or settings_manager
        self._default_language = default_language
        self._listener_factory = listener_factory or _default_listener_factory
        self._tts_engine_factory = tts_engine_factory or _default_tts_engine_factory
        self._wake_detector_factory = wake_detector_factory or _default_wake_detector_factory
        self._speakkit_listener_factory = speakkit_listener_factory
        self._speakkit_tts_engine_factory = speakkit_tts_engine_factory
        self._speakkit_wake_detector_factory = speakkit_wake_detector_factory
        self._provider_registry: ProviderRegistry | None = provider_registry_obj
        self._network_probe = network_probe or TCPNetworkProbe()
        self._dispatcher = dispatcher or _default_dispatch
        self._max_onboarding_attempts = max(1, max_onboarding_attempts)

        self._listener: Any = None
        self._tts_engine: Any = None
        self._wake_detector: Any = None
        self._provider_state = ProviderSelectionState()
        self._stop_event = threading.Event()
        self._interrupt_event = threading.Event()
        self._interrupt_latched = False
        self._active_operation_context: InFlightOperationContext | None = None
        self._thread: threading.Thread | None = None
        self._active = False
        self._initialized = False
        self._finalized = False
        self._startup_started_at = 0.0
        self._priority_buffer: list[InteractionPriorityEvent] = []
        self._last_coalesced_at: dict[tuple[str, str], float] = {}
        self._session_sequence = 0
        self._wake_selection: WakePolicySelection | None = None
        self._wake_cycle_locked = False
        self._last_degraded_guidance_reason: str | None = None
        self._wake_miss_streak = 0
        self._pending_standby_wake_details: dict[str, Any] = {}
        self._confidence_retry_cycles = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start_in_background(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._interrupt_event.clear()
        self._interrupt_latched = False
        self._thread = threading.Thread(target=self.run_forever, name="AssistantRuntime", daemon=True)
        self._thread.start()

    def request_stop(self) -> None:
        self._stop_event.set()
        self._interrupt_event.set()
        self._active = False
        self._wake_cycle_locked = False

        wake_stop = getattr(self._wake_detector, "request_stop", None)
        if callable(wake_stop):
            wake_stop()
        listener_stop = getattr(self._listener, "request_stop", None)
        if callable(listener_stop):
            listener_stop()
        tts_stop = getattr(self._tts_engine, "request_stop", None)
        if callable(tts_stop):
            tts_stop()

    def shutdown(self, join_timeout_s: float = 2.0) -> None:
        self.request_stop()
        if self._thread:
            self._thread.join(timeout=join_timeout_s)
        if not self._finalized:
            self._finalize_shutdown()

    def run_forever(self, max_cycles: int | None = None) -> None:
        self._interrupt_event.clear()
        self._interrupt_latched = False
        self._initialize_runtime()
        if self._finalized:
            return

        cycles = 0
        try:
            while not self._stop_event.is_set():
                if max_cycles is not None and cycles >= max_cycles:
                    break
                self._run_cycle()
                cycles += 1
        except KeyboardInterrupt:
            logger.info("[RUNTIME] Keyboard interrupt received")
            self.request_stop()
        finally:
            self._finalize_shutdown()

    def _initialize_runtime(self) -> None:
        if self._initialized:
            return

        self._startup_started_at = time.perf_counter()
        try:
            self._settings.load_user_profile()
            self._settings.reset_network_override_for_startup()
            if self._default_language and not self._settings.is_configured():
                self._settings.apply_settings_snapshot({"language": self._default_language}, persist=False)

            if self._settings.deferred_provider_switch and self._settings.pending_speech_provider:
                self._settings.consume_deferred_speech_provider()

            if self._provider_registry is None:
                self._provider_registry = create_default_provider_registry(
                    default_language=self._settings.language,
                    listener_factory=self._listener_factory,
                    tts_engine_factory=self._tts_engine_factory,
                    wake_detector_factory=self._wake_detector_factory,
                    speakkit_listener_factory=self._speakkit_listener_factory,
                    speakkit_tts_factory=self._speakkit_tts_engine_factory,
                    speakkit_wake_factory=self._speakkit_wake_detector_factory,
                )

            connectivity_state = self._refresh_connectivity_state(source="startup")
            startup = resolve_startup_provider(
                persisted_provider=self._settings.speech_provider,
                registry=self._provider_registry,
                connectivity_state=connectivity_state,
            )
            self._provider_state.persisted_provider = startup.persisted_provider
            self._provider_state.session_provider = startup.session_provider
            self._provider_state.pending_provider = self._settings.pending_speech_provider
            self._provider_state.deferred_until_restart = self._settings.deferred_provider_switch
            self._provider_state.degraded_mode = startup.degraded_mode
            self._provider_state.degraded_reason = startup.degraded_reason

            if startup.offline_required:
                message = self._resolve_runtime_critical_prompt(
                    "runtime.startup.provider_unavailable"
                )["text"]
                self.session.last_error = message
                self._emit(
                    error_event(
                        self.session,
                        message=message,
                        recoverable=False,
                        next_state=RuntimeState.OFFLINE,
                        provider=startup.persisted_provider,
                        stage="startup",
                        fallback_applied=False,
                        manual_restart_required=True,
                        reason_code=DUAL_PROVIDER_UNAVAILABLE_REASON,
                    )
                )
                self._force_state(RuntimeState.OFFLINE)
                self._emit(status_event(self.session, RuntimeState.OFFLINE))
                self._emit_startup_readiness(
                    status="offline",
                    degraded_reason=startup.degraded_reason or DUAL_PROVIDER_UNAVAILABLE_REASON,
                )
                self._finalized = True
                return

            self._activate_provider(startup.session_provider)
            if startup.requires_network and not startup.effective_network_available:
                self._provider_state.degraded_mode = True
                self._provider_state.degraded_reason = (
                    startup.degraded_reason or NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON
                )

            self.session.apply_settings(self._settings_snapshot())
            self._transition_and_emit(RuntimeState.STANDBY, force=True)
            self._wake_selection = self._resolve_wake_selection()
            self._emit_wake_policy_event(self._wake_selection)
            if startup.degraded_mode:
                degraded = self._resolve_runtime_critical_prompt("runtime.startup.degraded")
                self._emit_system(degraded["text"])
            else:
                ready_prompt = self._resolve_runtime_critical_prompt("runtime.startup.ready")
                self._emit_system(ready_prompt["text"])
            wake_prompt = self._resolve_runtime_critical_prompt("runtime.startup.wake_hint")
            self._emit_system(wake_prompt["text"])
            self._emit_config()
            self._emit_startup_readiness(
                status="degraded" if startup.degraded_mode else "ready",
                degraded_reason=startup.degraded_reason,
            )
            self._emit_non_speech_cue("ready")

            self._initialized = True
            logger.info(
                "[RUNTIME] initialized mode=%s session=%s configured=%s provider=%s",
                self.mode.value,
                self.session.session_id,
                self.session.configured,
                self._provider_state.session_provider,
            )
        except Exception as err:  # noqa: BLE001
            logger.exception("[RUNTIME] Initialization failed")
            self.session.last_error = str(err)
            self._emit(
                error_event(
                    self.session,
                    message=str(err),
                    recoverable=False,
                    next_state=RuntimeState.OFFLINE,
                    provider=self._provider_state.session_provider,
                    stage="startup",
                    fallback_applied=False,
                    manual_restart_required=True,
                    reason_code=STARTUP_UNAVAILABLE_REASON,
                )
            )
            self._force_state(RuntimeState.OFFLINE)
            self._emit(status_event(self.session, RuntimeState.OFFLINE))
            self._emit_startup_readiness(status="offline", degraded_reason=STARTUP_UNAVAILABLE_REASON)
            self._finalized = True

    def _run_cycle(self) -> None:
        stage = "wake"
        try:
            recognition_result: CommandRecognitionResult | None = None
            if self._active:
                stage = "listening"
                self._transition_and_emit(RuntimeState.LISTENING, force=True)
                recognition_result = self._listen_command_result_bounded(recognition_path="local_first")
                recognized_text = (
                    recognition_result.primary_transcript
                    if recognition_result is not None and not recognition_result.error_code
                    else None
                )
                if recognized_text is None and not self._stop_event.is_set():
                    self._active = False
                    self._wake_cycle_locked = False
                    self._emit_timeout_outcome(stage="listening")
                    self._transition_and_emit(RuntimeState.STANDBY, force=True)
                    return
            else:
                stage = "wake"
                self._transition_and_emit(RuntimeState.STANDBY, force=True)
                self._pending_standby_wake_details = {}
                standby_attempt = self._await_standby_wake_attempt()
                if standby_attempt is None:
                    return
                recognized_text, attempt_mode = standby_attempt

            if self._stop_event.is_set() or not recognized_text:
                return

            if not self._active:
                self._handle_standby_input(recognized_text, attempt_mode=attempt_mode)
            else:
                self._handle_active_input(recognized_text, recognition_result=recognition_result)
        except Exception as err:  # noqa: BLE001
            if isinstance(err, UnrecoverableRuntimeError):
                self._handle_unrecoverable_failure(err, stage=stage)
            else:
                self._handle_recoverable_failure(err, stage=stage)

    def _resolve_wake_selection(self) -> WakePolicySelection:
        if self._provider_registry is None:
            raise RuntimeError("provider registry is not initialized")

        wake_snapshot = self._provider_registry.wake_source_snapshot(self._provider_state.session_provider)
        connectivity = self._connectivity_state()
        selection = resolve_wake_mode(
            wake_primary_mode=self._settings.wake_primary_mode,
            wake_fallback_mode=self._settings.wake_fallback_mode,
            wake_dev_fallback_mode=self._settings.wake_dev_fallback_mode,
            stt_wake_allowed_in_production=self._settings.stt_wake_allowed_in_production,
            runtime_environment="production_like",
            keyword_wake_available=bool(wake_snapshot.get("keyword_wake_available", False)),
            hardware_trigger_available=bool(wake_snapshot.get("hardware_trigger_available", False)),
            stt_wake_available=bool(wake_snapshot.get("stt_wake_available", False)),
            strict_local_wake_fallback_available=bool(
                wake_snapshot.get("strict_local_wake_fallback_available", False)
            ),
            provider_availability=str(wake_snapshot.get("provider_availability", "ready")),
            effective_network_available=bool(connectivity.get("effective_network_available", True)),
        )
        return WakePolicySelection(
            selected_mode=selection.selected_mode,
            fallback_mode=selection.fallback_mode,
            dev_fallback_mode=selection.dev_fallback_mode,
            selection_source=selection.selection_source,
            degraded_mode=selection.degraded_mode,
            degraded_reason=selection.degraded_reason,
            fallback_reason=selection.fallback_reason,
        )

    def _emit_wake_policy_event(self, selection: WakePolicySelection) -> None:
        payload = {
            "wake_mode": selection.selected_mode,
            "wake_fallback_mode": selection.fallback_mode,
            "wake_dev_fallback_mode": selection.dev_fallback_mode,
            "selection_source": selection.selection_source,
            "degraded_mode": selection.degraded_mode,
            "degraded_reason": selection.degraded_reason,
            "wake_fallback_reason": selection.fallback_reason,
        }
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=payload,
            )
        )

    def _resolve_canonical_wake_details(self, recognized_text: str) -> tuple[str | None, bool]:
        normalized = normalize_wake_phrase(recognized_text)
        if not normalized:
            return None, False

        for canonical in CANONICAL_WAKE_PHRASES:
            canonical_norm = normalize_wake_phrase(canonical)
            if normalized == canonical_norm:
                return canonical_norm, False
            if normalized.startswith(f"{canonical_norm} "):
                return canonical_norm, True

        decision = detect_wake(normalized)
        if not decision.accepted:
            decision = detect_wake(normalized, profile="development")
        if not decision.accepted:
            return None, False

        matched_alias = normalize_wake_phrase(decision.matched_alias or "")
        marhaba_norm = normalize_wake_phrase("\u0645\u0631\u062d\u0628\u0627")
        canonical_alias = "\u0645\u0631\u062d\u0628\u0627" if matched_alias == marhaba_norm else "hi egb"
        alias_for_suffix = matched_alias or normalize_wake_phrase(canonical_alias)
        suffix_ignored = False
        if alias_for_suffix and normalized != alias_for_suffix:
            alias_compact = alias_for_suffix.replace(" ", "")
            normalized_compact = normalized.replace(" ", "")
            suffix_ignored = normalized.startswith(f"{alias_for_suffix} ") or (
                bool(alias_compact)
                and normalized_compact.startswith(alias_compact)
                and len(normalized_compact) > len(alias_compact)
            )
        return canonical_alias, suffix_ignored

    def _await_standby_wake_attempt(self) -> tuple[str, str] | None:
        selection = self._resolve_wake_selection()
        self._wake_selection = selection
        self._emit_wake_policy_event(selection)

        if selection.degraded_mode:
            self._emit_degraded_standby_guidance(selection)
            return None

        self._last_degraded_guidance_reason = None
        if selection.selected_mode == WAKE_MODE_STT_BASED:
            listener = self._listener
            if listener is None:
                return None
            timeout_s = max(1, int(round(self._settings.max_listen_seconds)))
            wake_result: CommandRecognitionResult | None = None
            listen_command_result = getattr(listener, "listen_command_result", None)
            if callable(listen_command_result):
                try:
                    wake_result = listen_command_result(
                        timeout_s=timeout_s,
                        phrase_time_limit_s=min(6, timeout_s),
                        interrupt_event=self._interrupt_event,
                        languages=["ar-EG", "en-US"],
                        recognition_path="local_first",
                        usage_mode="standby_wake",
                        capture_profile_id=self._settings.standby_capture_profile_id,
                        dictionary_bias_mode="none",
                        qualification_profile_id=self._settings.speech_qualification_profile,
                    )
                except TypeError:
                    recognized = listener.listen_any(["ar-EG", "en-US"])
                    if recognized:
                        wake_result = CommandRecognitionResult(
                            session_id=self.session.session_id,
                            recognition_path="local_first",
                            provider_id=self._provider_state.session_provider,
                            primary_transcript=recognized,
                            confidence_available=False,
                            confidence_score=None,
                            alternative_transcripts=(recognized,),
                            detected_language=self.session.language,
                            selected_language=self.session.language,
                            latency_ms=0,
                            error_code=None,
                            recognition_source="legacy_local",
                        )
            if wake_result is None:
                try:
                    recognized = listener.listen_any(
                        ["ar-EG", "en-US"],
                        prompt="[STT] Wake listening...",
                        timeout=timeout_s,
                        phrase_time_limit=6,
                        interrupt_event=self._interrupt_event,
                    )
                except TypeError:
                    recognized = listener.listen_any(["ar-EG", "en-US"])
                if recognized:
                    wake_result = CommandRecognitionResult(
                        session_id=self.session.session_id,
                        recognition_path="local_first",
                        provider_id=self._provider_state.session_provider,
                        primary_transcript=recognized,
                        confidence_available=False,
                        confidence_score=None,
                        alternative_transcripts=(recognized,),
                        detected_language=self.session.language,
                        selected_language=self.session.language,
                        latency_ms=0,
                        error_code=None,
                        recognition_source="legacy_local",
                    )

            if wake_result is None or wake_result.error_code:
                self._wake_miss_streak += 1
                source_classification = wake_result.recognition_source if wake_result is not None else None
                failure_reason = wake_result.failure_reason_code if wake_result is not None else None
                error_code = (wake_result.error_code if wake_result is not None else None) or failure_reason or "wake_not_detected"
                self._emit_wake_outcome(
                    StandbyWakeOutcome(
                        trigger="wake_policy",
                        status="wake_missed",
                        spoken_text="",
                        error_code=error_code,
                        next_runtime_state=RuntimeState.STANDBY.value,
                        selected_wake_mode=selection.selected_mode,
                        attempt_source_mode=WAKE_MODE_STT_BASED,
                        source_classification=source_classification,
                        canonical_wake_alias=None,
                        command_suffix_ignored=False,
                        degraded_mode=False,
                        degraded_reason=None,
                        payload=self._standby_outcome_payload(
                            selection=selection,
                            attempt_source_mode=WAKE_MODE_STT_BASED,
                            source_classification=source_classification,
                            canonical_wake_alias=None,
                            command_suffix_ignored=False,
                            fallback_attempted=bool(failure_reason),
                            fallback_used=bool(source_classification == "wake_strict_vosk_fallback"),
                            cloud_failure_reason=failure_reason,
                            wake_miss_streak=self._wake_miss_streak,
                        ),
                    )
                )
                return None

            recognized = wake_result.primary_transcript
            canonical_alias, command_suffix_ignored = self._resolve_canonical_wake_details(recognized)
            if canonical_alias is None:
                self._wake_miss_streak += 1
                self._emit_wake_outcome(
                    StandbyWakeOutcome(
                        trigger="wake_policy",
                        status="wake_rejected",
                        spoken_text="",
                        error_code="wake_phrase_not_approved",
                        next_runtime_state=RuntimeState.STANDBY.value,
                        selected_wake_mode=selection.selected_mode,
                        attempt_source_mode=WAKE_MODE_STT_BASED,
                        source_classification="noncanonical_rejected",
                        canonical_wake_alias=None,
                        command_suffix_ignored=False,
                        degraded_mode=False,
                        degraded_reason=None,
                        payload=self._standby_outcome_payload(
                            selection=selection,
                            attempt_source_mode=WAKE_MODE_STT_BASED,
                            source_classification="noncanonical_rejected",
                            canonical_wake_alias=None,
                            command_suffix_ignored=False,
                            fallback_attempted=bool(wake_result.failure_reason_code),
                            fallback_used=bool(wake_result.recognition_source == "wake_strict_vosk_fallback"),
                            cloud_failure_reason=wake_result.failure_reason_code,
                            wake_miss_streak=self._wake_miss_streak,
                        ),
                    )
                )
                return None

            self._pending_standby_wake_details = {
                "source_classification": wake_result.recognition_source,
                "canonical_wake_alias": canonical_alias,
                "command_suffix_ignored": command_suffix_ignored,
                "fallback_attempted": bool(wake_result.failure_reason_code),
                "fallback_used": bool(wake_result.recognition_source == "wake_strict_vosk_fallback"),
                "cloud_failure_reason": wake_result.failure_reason_code,
            }
            return canonical_alias, WAKE_MODE_STT_BASED

        wake = self._wait_for_provider_wake(selection.selected_mode)
        if wake is None:
            return None
        if getattr(wake, "action", WakeAction.START) != WakeAction.START:
            return None
        phrase = str(getattr(wake, "phrase", "") or selection.selected_mode)
        canonical_alias, command_suffix_ignored = self._resolve_canonical_wake_details(phrase)
        self._pending_standby_wake_details = {
            "source_classification": selection.selected_mode,
            "canonical_wake_alias": canonical_alias,
            "command_suffix_ignored": command_suffix_ignored,
            "fallback_attempted": False,
            "fallback_used": False,
            "cloud_failure_reason": None,
        }
        return phrase, selection.selected_mode

    def _wait_for_provider_wake(self, wake_mode: str) -> Any | None:
        wake_service = self._wake_detector
        if wake_service is None:
            return None
        wait_for_wake = getattr(wake_service, "wait_for_wake", None)
        if callable(wait_for_wake):
            timeout_s = float(self._settings.max_listen_seconds)
            result_holder: dict[str, Any] = {}
            completed = threading.Event()

            def _invoke_wake_wait() -> None:
                try:
                    try:
                        result_holder["value"] = wait_for_wake(
                            timeout_s=timeout_s,
                            wake_mode=wake_mode,
                            interrupt_event=self._interrupt_event,
                        )
                    except TypeError:
                        try:
                            result_holder["value"] = wait_for_wake(
                                timeout_s=timeout_s,
                                wake_mode=wake_mode,
                            )
                        except TypeError:
                            result_holder["value"] = wait_for_wake(timeout_s=timeout_s)
                except Exception as exc:  # noqa: BLE001
                    result_holder["error"] = exc
                finally:
                    completed.set()

            worker = threading.Thread(target=_invoke_wake_wait, name="RuntimeWakeBounded", daemon=True)
            worker.start()
            deadline = time.perf_counter() + max(0.2, timeout_s + 0.5)
            while not completed.wait(timeout=0.01):
                if self._stop_event.is_set() or self._interrupt_event.is_set() or time.perf_counter() >= deadline:
                    wake_stop = getattr(wake_service, "request_stop", None)
                    if callable(wake_stop):
                        wake_stop()
                    listener_stop = getattr(self._listener, "request_stop", None)
                    if callable(listener_stop):
                        listener_stop()
                    return None

            if result_holder.get("error") is not None:
                raise result_holder["error"]
            wake_result = result_holder.get("value")
            if wake_result is not None:
                return wake_result
        if self._stop_event.is_set() or self._interrupt_event.is_set():
            return None
        detector = getattr(wake_service, "detect", None)
        if callable(detector):
            return detector("")
        return None

    def _emit_degraded_standby_guidance(self, selection: WakePolicySelection) -> None:
        reason = selection.degraded_reason or "no_permitted_wake_source"
        if self._last_degraded_guidance_reason == reason:
            return
        guidance = self._resolve_runtime_critical_prompt(
            "runtime.offline.safe_refusal",
            priority="warning",
            preempt=True,
        )["text"]
        self._emit_wake_outcome(
            StandbyWakeOutcome(
                trigger="wake_policy",
                status="degraded_standby",
                spoken_text=guidance,
                error_code=reason,
                next_runtime_state=RuntimeState.STANDBY.value,
                selected_wake_mode=selection.selected_mode,
                attempt_source_mode=None,
                degraded_mode=True,
                degraded_reason=reason,
                payload=self._standby_outcome_payload(selection=selection, attempt_source_mode=None),
            )
        )
        self._last_degraded_guidance_reason = reason

    def _standby_outcome_payload(
        self,
        *,
        selection: WakePolicySelection,
        attempt_source_mode: str | None,
        source_classification: str | None = None,
        canonical_wake_alias: str | None = None,
        command_suffix_ignored: bool = False,
        fallback_attempted: bool = False,
        fallback_used: bool = False,
        cloud_failure_reason: str | None = None,
        wake_miss_streak: int | None = None,
    ) -> dict[str, Any]:
        return {
            "runtime_environment": "production_like",
            "wake_cycle_locked": self._wake_cycle_locked,
            "degraded_guidance_announced": self._last_degraded_guidance_reason is not None,
            "selected_mode": selection.selected_mode,
            "selection_source": selection.selection_source,
            "attempt_source_mode": attempt_source_mode,
            "wake_to_listen_ms": get_runtime_latency_metrics(self.session.session_id).get("wake_to_listen"),
            "listen_to_response_ms": get_runtime_latency_metrics(self.session.session_id).get(
                "listen_to_result"
            ),
            "source_classification": source_classification,
            "canonical_wake_alias": canonical_wake_alias,
            "command_suffix_ignored": bool(command_suffix_ignored),
            "fallback_attempted": bool(fallback_attempted),
            "fallback_used": bool(fallback_used),
            "cloud_failure_reason": cloud_failure_reason,
            "wake_miss_streak": int(wake_miss_streak if wake_miss_streak is not None else self._wake_miss_streak),
            "field_safe": True,
            "raw_user_content_present": False,
        }

    def _emit_wake_outcome(self, outcome: StandbyWakeOutcome) -> None:
        payload = outcome.to_dict()
        payload["next_state"] = payload.pop("next_runtime_state")
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=payload,
            )
        )

    def _handle_standby_input(self, recognized_text: str, *, attempt_mode: str) -> None:
        selection = self._wake_selection or self._resolve_wake_selection()
        wake_details = dict(self._pending_standby_wake_details or {})
        if self._wake_cycle_locked:
            self._emit_wake_outcome(
                StandbyWakeOutcome(
                    trigger="wake_policy",
                    status="wake_rejected",
                    spoken_text="",
                    error_code="wake_cycle_locked",
                    next_runtime_state=RuntimeState.STANDBY.value,
                    selected_wake_mode=selection.selected_mode,
                    attempt_source_mode=attempt_mode,
                    source_classification=wake_details.get("source_classification"),
                    canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                    command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                    degraded_mode=selection.degraded_mode,
                    degraded_reason=selection.degraded_reason,
                    payload=self._standby_outcome_payload(
                        selection=selection,
                        attempt_source_mode=attempt_mode,
                        source_classification=wake_details.get("source_classification"),
                        canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                        command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                        fallback_attempted=bool(wake_details.get("fallback_attempted", False)),
                        fallback_used=bool(wake_details.get("fallback_used", False)),
                        cloud_failure_reason=wake_details.get("cloud_failure_reason"),
                    ),
                )
            )
            return

        if attempt_mode != selection.selected_mode:
            self._emit_wake_outcome(
                StandbyWakeOutcome(
                    trigger="wake_policy",
                    status="wake_rejected",
                    spoken_text="",
                    error_code="wake_mode_not_selected",
                    next_runtime_state=RuntimeState.STANDBY.value,
                    selected_wake_mode=selection.selected_mode,
                    attempt_source_mode=attempt_mode,
                    source_classification=wake_details.get("source_classification"),
                    canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                    command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                    degraded_mode=selection.degraded_mode,
                    degraded_reason=selection.degraded_reason,
                    payload=self._standby_outcome_payload(
                        selection=selection,
                        attempt_source_mode=attempt_mode,
                        source_classification=wake_details.get("source_classification"),
                        canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                        command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                        fallback_attempted=bool(wake_details.get("fallback_attempted", False)),
                        fallback_used=bool(wake_details.get("fallback_used", False)),
                        cloud_failure_reason=wake_details.get("cloud_failure_reason"),
                    ),
                )
            )
            return

        self._wake_miss_streak = 0
        self._wake_cycle_locked = True
        self._transition_and_emit(RuntimeState.WAKE, force=True)
        session_lang = self._infer_session_language(recognized_text)
        if session_lang:
            self._settings.apply_settings_snapshot({"language": session_lang}, persist=False)
            self.session.apply_settings(self._settings_snapshot())

        self._active = True

        self._emit_wake_outcome(
            StandbyWakeOutcome(
                trigger="wake_policy",
                status="wake_accepted",
                spoken_text="",
                next_runtime_state=RuntimeState.WAKE.value,
                selected_wake_mode=selection.selected_mode,
                attempt_source_mode=attempt_mode,
                source_classification=wake_details.get("source_classification"),
                canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                degraded_mode=selection.degraded_mode,
                degraded_reason=selection.degraded_reason,
                payload=self._standby_outcome_payload(
                    selection=selection,
                    attempt_source_mode=attempt_mode,
                    source_classification=wake_details.get("source_classification"),
                    canonical_wake_alias=wake_details.get("canonical_wake_alias"),
                    command_suffix_ignored=bool(wake_details.get("command_suffix_ignored", False)),
                    fallback_attempted=bool(wake_details.get("fallback_attempted", False)),
                    fallback_used=bool(wake_details.get("fallback_used", False)),
                    cloud_failure_reason=wake_details.get("cloud_failure_reason"),
                ),
            )
        )

        if not self._settings.is_configured():
            self._transition_and_emit(RuntimeState.SETUP, force=True)
            onboarding_intro = self._resolve_runtime_critical_prompt("runtime.onboarding.intro")
            self._emit_assistant(onboarding_intro["text"])
            self._run_voice_onboarding(session_lang=self._settings.language)
            self.session.apply_settings(self._settings_snapshot())
            self._emit_config()

        greeting = self._settings.speak_localized(
            "تمام. أنا جاهز، تفضل.",
            "Alright. I'm listening.",
            priority="action_confirmation",
        )
        self._emit_assistant(greeting)
        self._transition_and_emit(RuntimeState.LISTENING, force=True)

    def _handle_active_input(
        self,
        recognized_text: str,
        *,
        recognition_result: CommandRecognitionResult | None = None,
    ) -> None:
        interrupt_detection = self._interrupt_signal_type(recognized_text)
        if interrupt_detection:
            self._handle_interrupt_signal(interrupt_detection)
            return

        if self._is_close_intent(recognized_text):
            msg = self._settings.speak_localized(
                "تمام، مش هقفل. انا موجود.",
                "Okay, I won't close. I'm here.",
                priority="action_confirmation",
            )
            self._emit_assistant(msg)
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return

        if self._is_thanks_intent(recognized_text):
            msg = self._settings.speak_localized(
                "العفو!",
                "You're welcome!",
                priority="info",
            )
            self._emit_assistant(msg)
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return

        active_recognition = recognition_result or CommandRecognitionResult(
            session_id=self.session.session_id,
            recognition_path="local_first",
            provider_id=self._provider_state.session_provider,
            primary_transcript=recognized_text,
            confidence_score=None,
            confidence_available=False,
            alternative_transcripts=(recognized_text,),
            detected_language=self.session.language,
            latency_ms=0,
            error_code=None,
        )
        active_recognition = self._rerank_command_recognition(active_recognition)
        post_processing = process_command_transcript(
            active_recognition.primary_transcript,
            alternative_transcripts=active_recognition.alternative_transcripts,
            language_hints=[active_recognition.detected_language] if active_recognition.detected_language else None,
            dictionary_mode=(
                active_recognition.dictionary_bias_mode
                or ("closed_choice" if active_recognition.closed_vocabulary_id else "command_inventory")
            ),
            closed_vocabulary_id=active_recognition.closed_vocabulary_id,
            closed_vocabulary=self._closed_vocabulary_options(active_recognition.closed_vocabulary_id),
        )
        closed_context = closed_vocabulary_context(active_recognition.closed_vocabulary_id)
        closed_match = match_closed_vocabulary(
            utterance=active_recognition.primary_transcript,
            vocabulary_id=active_recognition.closed_vocabulary_id,
        )
        if (
            post_processing.post_processing_status == "constrained_retry"
            and closed_match is not None
            and closed_match.confidence >= 0.90
        ):
            post_processing = CommandPostProcessingOutcome(
                source_transcript=post_processing.source_transcript,
                normalized_transcript=post_processing.normalized_transcript,
                canonical_command_text=closed_match.canonical_value,
                substitution_ids=post_processing.substitution_ids,
                language_hints=post_processing.language_hints,
                dictionary_mode="closed_choice",
                closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                confusion_pair_id=post_processing.confusion_pair_id,
                ambiguity_flags=tuple(flag for flag in post_processing.ambiguity_flags if flag != "out_of_closed_vocabulary"),
                post_processing_status="normalized",
            )
        if post_processing.post_processing_status == "constrained_retry":
            if (
                closed_context is not None
                and closed_context.global_safety_preemption_only
                and is_global_safety_preemption(recognized_text)
            ):
                guidance = self._settings.speak_localized(
                    "تم قبول أمر السلامة العام.",
                    "Global safety command accepted.",
                    priority="warning",
                )
                self._emit_assistant(guidance, priority="warning")
                self._emit_guided_dialog_outcome(
                    status="rejected",
                    spoken_text=guidance,
                    error_code="global_safety_preempted",
                    next_runtime_state=RuntimeState.LISTENING.value,
                    closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                    retry_count=self._confidence_retry_cycles,
                    retry_limit=self._settings.closed_vocabulary_retry_limit,
                    preserved_safety_state="global_safety_preempted",
                )
                self._transition_and_emit(RuntimeState.LISTENING, force=True)
                return
            if self._confidence_retry_cycles < self._settings.closed_vocabulary_retry_limit:
                guidance = self._settings.speak_localized(
                    "اختار من الخيارات المتاحة فقط، من فضلك.",
                    "Please answer using one of the available options only.",
                    priority="action_confirmation",
                )
                self._confidence_retry_cycles += 1
                self._emit_assistant(guidance, priority="action_confirmation")
                self._emit_guided_dialog_outcome(
                    status="retry_required",
                    spoken_text=guidance,
                    error_code="out_of_domain_answer",
                    next_runtime_state=RuntimeState.LISTENING.value,
                    closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                    retry_count=self._confidence_retry_cycles,
                    retry_limit=self._settings.closed_vocabulary_retry_limit,
                )
            else:
                guidance = self._settings.speak_localized(
                    "لم اقدر تحديد خيار آمن من إجابتك.",
                    "I could not map that to a safe option.",
                    priority="warning",
                )
                self._confidence_retry_cycles = 0
                self._emit_assistant(guidance, priority="warning")
                self._emit_guided_dialog_outcome(
                    status="graceful_exit",
                    spoken_text=guidance,
                    error_code="retry_exhausted",
                    next_runtime_state=RuntimeState.LISTENING.value,
                    closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                    retry_count=self._confidence_retry_cycles,
                    retry_limit=self._settings.closed_vocabulary_retry_limit,
                    graceful_exit=True,
                    fallback_or_exit_reason="closed_vocabulary_retry_exhausted",
                )
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return
        canonical_text = post_processing.canonical_command_text or recognized_text
        recognition_metadata = self._build_recognition_metadata(
            recognition_result=active_recognition,
            post_processing=post_processing,
        )
        parsed = command_parser.parse_command(
            canonical_text,
            canonical_command_text=canonical_text,
            recognition_metadata=recognition_metadata,
        )
        confidence_policy = self._command_confidence_policy()
        confidence_decision = self._evaluate_confidence_decision(
            recognition_result=active_recognition,
            post_processing=post_processing,
            parsed_intent=parsed,
            policy=confidence_policy,
            retry_count=self._confidence_retry_cycles,
        )

        while confidence_decision.decision_action == "fallback":
            fallback_result = self._listen_command_result_bounded(
                recognition_path="rescue",
                session_id=active_recognition.session_id,
            )
            if (
                fallback_result is None
                or fallback_result.error_code
                or not fallback_result.primary_transcript.strip()
            ):
                confidence_decision = self._evaluate_confidence_decision(
                    recognition_result=active_recognition,
                    post_processing=post_processing,
                    parsed_intent=parsed,
                    policy=confidence_policy,
                    retry_count=self._confidence_retry_cycles,
                    fallback_attempted_override=True,
                )
                break
            active_recognition = fallback_result
            post_processing = process_command_transcript(
                active_recognition.primary_transcript,
                alternative_transcripts=active_recognition.alternative_transcripts,
                language_hints=[active_recognition.detected_language] if active_recognition.detected_language else None,
                dictionary_mode=(
                    active_recognition.dictionary_bias_mode
                    or ("closed_choice" if active_recognition.closed_vocabulary_id else "command_inventory")
                ),
                closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                closed_vocabulary=self._closed_vocabulary_options(active_recognition.closed_vocabulary_id),
            )
            if post_processing.post_processing_status == "constrained_retry":
                confidence_decision = self._evaluate_confidence_decision(
                    recognition_result=active_recognition,
                    post_processing=post_processing,
                    parsed_intent=command_parser.parse_command(""),
                    policy=confidence_policy,
                    retry_count=self._confidence_retry_cycles,
                    fallback_attempted_override=True,
                )
                break
            canonical_text = post_processing.canonical_command_text or active_recognition.primary_transcript
            recognition_metadata = self._build_recognition_metadata(
                recognition_result=active_recognition,
                post_processing=post_processing,
            )
            parsed = command_parser.parse_command(
                canonical_text,
                canonical_command_text=canonical_text,
                recognition_metadata=recognition_metadata,
            )
            confidence_decision = self._evaluate_confidence_decision(
                recognition_result=active_recognition,
                post_processing=post_processing,
                parsed_intent=parsed,
                policy=confidence_policy,
                retry_count=self._confidence_retry_cycles,
            )

        self._emit_recognition_telemetry(confidence_decision.telemetry)

        if confidence_decision.decision_action == "retry":
            guidance = self._settings.speak_localized(
                "الامر غير واضح. من فضلك اعد المحاولة مرة واحدة.",
                "I am not confident about that command. Please repeat once.",
                priority="action_confirmation",
            )
            self._confidence_retry_cycles += 1
            self._emit_assistant(guidance, priority="action_confirmation")
            self._emit_guided_dialog_outcome(
                status="retry_required",
                spoken_text=guidance,
                error_code=confidence_decision.reason_code,
                next_runtime_state=RuntimeState.LISTENING.value,
                closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                retry_count=self._confidence_retry_cycles,
                retry_limit=self._settings.command_max_retry_cycles,
            )
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return

        if confidence_decision.decision_action in {"refuse", "defer"}:
            guidance = self._settings.speak_localized(
                "لا اقدر تنفيذ هذا الامر بأمان الآن.",
                "I cannot execute that command safely right now.",
                priority="warning",
                preempt=True,
            )
            self._confidence_retry_cycles = 0
            self._emit_assistant(guidance, priority="warning")
            self._emit_guided_dialog_outcome(
                status="graceful_exit",
                spoken_text=guidance,
                error_code=confidence_decision.reason_code,
                next_runtime_state=RuntimeState.LISTENING.value,
                closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                retry_count=self._confidence_retry_cycles,
                retry_limit=self._settings.command_max_retry_cycles,
                graceful_exit=True,
                fallback_or_exit_reason=confidence_decision.reason_code,
            )
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return

        self._emit(
            build_event(
                RuntimeEventType.USER,
                session_id=self.session.session_id,
                payload={
                    "text": canonical_text,
                    "recognition_path": active_recognition.recognition_path,
                    "profile_id": active_recognition.profile_id,
                    "capture_attempt_id": active_recognition.capture_attempt_id,
                },
            )
        )
        self._transition_and_emit(RuntimeState.THINKING, force=True)

        intent_id = parsed.intent_id if parsed and parsed.accepted else None
        capability_id = self._capability_id_for_intent(intent_id)
        requires_network = self._requires_network_for_intent(intent_id)
        connectivity = self._refresh_connectivity_state(source="background")
        provider_availability = self._provider_availability_for_session()
        offline_decision = evaluate_offline_execution_policy(
            flow="command",
            capability_id=capability_id,
            provider_id=self._provider_state.session_provider,
            requires_network=requires_network,
            effective_network_available=bool(connectivity.get("effective_network_available", True)),
            override_mode=str(connectivity.get("override_mode", "auto")),
            detected_status=str(connectivity.get("detected_status", "online")),
            provider_availability=provider_availability,
            offline_allowlist=self._settings.offline_allowlisted_capabilities,
        )

        offline_payload = attach_runtime_diagnostic_fields(
            offline_decision.to_dict(),
            session_or_run_id=self.session.session_id,
            event_category="offline_policy",
            status_or_decision=offline_decision.decision,
            reason_code=offline_decision.error_code,
            provider_id=self._provider_state.session_provider,
            provider_availability=provider_availability,
            degraded_mode=self._provider_state.degraded_mode,
            degraded_reason=self._provider_state.degraded_reason,
            next_state=(
                RuntimeState.LISTENING.value
                if offline_decision.decision in {"safe_refusal", "provider_degraded"}
                else RuntimeState.THINKING.value
            ),
            user_outcome=offline_decision.spoken_text or None,
        )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=offline_payload,
            )
        )

        if offline_decision.decision in {"safe_refusal", "provider_degraded"}:
            guidance = self._resolve_runtime_critical_prompt(
                "runtime.offline.safe_refusal",
                priority="warning",
                preempt=True,
            )["text"]
            self._emit_assistant(guidance, priority="warning")
            self._emit_guided_dialog_outcome(
                status="rejected",
                spoken_text=guidance,
                error_code=offline_decision.error_code,
                next_runtime_state=RuntimeState.LISTENING.value,
                closed_vocabulary_id=active_recognition.closed_vocabulary_id,
                retry_count=self._confidence_retry_cycles,
                retry_limit=self._settings.command_max_retry_cycles,
                fallback_or_exit_reason=offline_decision.error_code,
                preserved_safety_state="offline_guard_active",
            )
            self._emit_recovery_outcome(
                RuntimeRecoveryOutcome(
                    trigger="offline_policy",
                    status="safe_refusal",
                    spoken_text=guidance,
                    error_code=offline_decision.error_code,
                    duration_ms=0,
                    next_runtime_state=RuntimeState.LISTENING.value,
                    completion_status="interrupted",
                    offline_policy_decision=offline_decision.decision,
                    capability_id=capability_id,
                    provider_id=self._provider_state.session_provider,
                )
            )
            self._transition_and_emit(RuntimeState.LISTENING, force=True)
            return

        runtime_context = {
            "network_available": bool(connectivity.get("effective_network_available", True)),
            "effective_network_available": bool(connectivity.get("effective_network_available", True)),
            "override_mode": str(connectivity.get("override_mode", "auto")),
            "detected_status": str(connectivity.get("detected_status", "online")),
            "provider_availability": provider_availability,
            "provider_id": self._provider_state.session_provider,
            "offline_allowlist": sorted(self._settings.offline_allowlisted_capabilities),
            "requires_network_override": requires_network,
            "offline_policy_decision": offline_decision.decision,
            "capability_id": capability_id,
            "interrupt_event": self._interrupt_event,
            "recognition_metadata": recognition_metadata,
            "confidence_decision_band": confidence_decision.decision_band,
            "confidence_decision_action": confidence_decision.decision_action,
            "confidence_reason_code": confidence_decision.reason_code,
            "confidence_retry_count": confidence_decision.retry_count,
            "post_processing_outcome": post_processing.to_dict(),
        }
        self._active_operation_context = InFlightOperationContext(
            operation_id=uuid4().hex,
            intent_id=intent_id,
            capability_id=capability_id,
            runtime_state=RuntimeState.THINKING.value,
            reversible=self._is_reversible_operation(intent_id=intent_id, requires_network=requires_network),
            cancellation_state="idle",
            follow_on_work_suppressed=False,
            provider_id=self._provider_state.session_provider,
            requires_network=requires_network,
        )
        dispatch_started_at = time.perf_counter()
        try:
            result = self._dispatcher(
                canonical_text,
                canonical_command_text=canonical_text,
                recognition_metadata=recognition_metadata,
                runtime_context=runtime_context,
            )
        except TypeError:
            try:
                result = self._dispatcher(canonical_text, runtime_context=runtime_context)
            except TypeError:
                result = self._dispatcher(canonical_text)
        dispatch_duration_ms = int((time.perf_counter() - dispatch_started_at) * 1000)
        self._emit_config()
        self._emit_dispatch_outcome(result, dispatch_duration_ms=dispatch_duration_ms)

        if isinstance(result, CommandExecutionResult):
            logger.info(
                "[RUNTIME] command outcome intent=%s status=%s duration_ms=%s error=%s",
                result.intent_id,
                result.status,
                dispatch_duration_ms,
                result.error_code,
            )
            if result.status in {"timeout", "failed", "unavailable", "rejected"}:
                logger.warning(
                    "[RUNTIME] command failure intent=%s status=%s duration_ms=%s metadata=%s",
                    result.intent_id,
                    result.status,
                    dispatch_duration_ms,
                    result.metadata,
                )

        if self._interrupt_latched:
            self._clear_active_operation()
            self._transition_and_emit(RuntimeState.STANDBY, force=True)
            return

        self._confidence_retry_cycles = 0
        self._transition_and_emit(RuntimeState.SPEAKING, force=True)
        spoken_result = self._normalize_dispatch_result(result)
        self._emit_assistant(spoken_result)
        self._emit_guided_dialog_outcome(
            status="accepted",
            spoken_text=spoken_result,
            error_code=None,
            next_runtime_state=RuntimeState.LISTENING.value,
            closed_vocabulary_id=active_recognition.closed_vocabulary_id,
            accepted_option_id=str(intent_id or "command_dispatched"),
            retry_count=self._confidence_retry_cycles,
            retry_limit=self._settings.command_max_retry_cycles,
        )
        self._clear_active_operation()
        self._transition_and_emit(RuntimeState.LISTENING, force=True)

    def _command_confidence_policy(self) -> ConfidenceDecisionPolicy:
        snapshot = self._settings_snapshot()
        return ConfidenceDecisionPolicy(
            high_confidence_threshold=snapshot.command_confidence_high_threshold,
            medium_confidence_threshold=snapshot.command_confidence_medium_threshold,
            protected_command_threshold=snapshot.command_protected_threshold,
            allow_missing_confidence_for_unprotected=(
                snapshot.command_allow_missing_confidence_for_unprotected
            ),
            max_retry_cycles=snapshot.command_max_retry_cycles,
            fallback_enabled=(snapshot.command_fallback_enabled or snapshot.command_rescue_enabled),
            offline_local_allowed=snapshot.command_offline_local_allowed,
        )

    def _confidence_band(
        self,
        *,
        confidence_available: bool,
        confidence_score: float | None,
        policy: ConfidenceDecisionPolicy,
    ) -> str:
        if not confidence_available or confidence_score is None:
            return "missing_confidence"
        if confidence_score >= policy.high_confidence_threshold:
            return "high"
        if confidence_score >= policy.medium_confidence_threshold:
            return "medium"
        return "low"

    def _has_material_alternative_conflict(
        self,
        *,
        recognition_result: CommandRecognitionResult,
        parsed_intent: ParsedCommandIntent | None,
    ) -> bool:
        if not parsed_intent or not parsed_intent.accepted:
            return False
        primary_family = _command_intent_family(parsed_intent.intent_id)
        if not primary_family:
            return False

        transcripts = self._ordered_unique_transcripts(
            recognition_result.primary_transcript,
            recognition_result.alternative_transcripts,
        )
        for transcript in transcripts:
            if not transcript or transcript == recognition_result.primary_transcript:
                continue
            outcome = process_command_transcript(
                transcript,
                alternative_transcripts=(),
                language_hints=[recognition_result.detected_language]
                if recognition_result.detected_language
                else None,
                dictionary_mode=(
                    recognition_result.dictionary_bias_mode
                    or ("closed_choice" if recognition_result.closed_vocabulary_id else "command_inventory")
                ),
                closed_vocabulary_id=recognition_result.closed_vocabulary_id,
                closed_vocabulary=self._closed_vocabulary_options(recognition_result.closed_vocabulary_id),
            )
            if outcome.post_processing_status in {"rejected", "constrained_retry"}:
                continue
            parsed_alternative = command_parser.parse_command(
                outcome.canonical_command_text or transcript,
                canonical_command_text=outcome.canonical_command_text or transcript,
            )
            if not parsed_alternative or not parsed_alternative.accepted:
                continue
            if _command_intents_materially_conflict(
                parsed_intent.intent_id,
                parsed_alternative.intent_id,
            ):
                return True
        return False

    def _evaluate_confidence_decision(
        self,
        *,
        recognition_result: CommandRecognitionResult,
        post_processing: CommandPostProcessingOutcome,
        parsed_intent: Any,
        policy: ConfidenceDecisionPolicy,
        retry_count: int,
        fallback_attempted_override: bool | None = None,
    ) -> ConfidenceDecisionOutcome:
        fallback_attempted = (
            bool(fallback_attempted_override)
            if fallback_attempted_override is not None
            else recognition_result.recognition_path in {"fallback", "rescue"}
        )
        is_protected = bool(
            parsed_intent
            and getattr(parsed_intent, "accepted", False)
            and getattr(parsed_intent, "intent_id", None) in _PROTECTED_INTENTS
        )
        band = self._confidence_band(
            confidence_available=recognition_result.confidence_available,
            confidence_score=recognition_result.confidence_score,
            policy=policy,
        )
        parsed_accepted = bool(parsed_intent and getattr(parsed_intent, "accepted", False))
        intent_id = getattr(parsed_intent, "intent_id", None) if parsed_intent is not None else None

        def _language_family(language_code: str | None) -> str | None:
            cleaned = str(language_code or "").strip().lower()
            if not cleaned:
                return None
            if cleaned.startswith("ar"):
                return "ar"
            if cleaned.startswith("en"):
                return "en"
            return cleaned.split("-", 1)[0]

        selected_family = _language_family(recognition_result.selected_language)
        detected_family = _language_family(recognition_result.detected_language)
        language_mismatch = bool(
            selected_family and detected_family and selected_family != detected_family
        )
        parser_rejected = not parsed_accepted
        ambiguity_flags = set(post_processing.ambiguity_flags)
        material_ambiguity_flags = set(ambiguity_flags)
        if "conflicting_alternatives" in material_ambiguity_flags:
            material_ambiguity_flags.remove("conflicting_alternatives")
            if self._has_material_alternative_conflict(
                recognition_result=recognition_result,
                parsed_intent=parsed_intent,
            ):
                material_ambiguity_flags.add("conflicting_alternatives")
        ambiguity_detected = bool(material_ambiguity_flags) or parser_rejected or language_mismatch

        reason_code = "high_confidence"
        decision_action = "execute"
        confirmation_required = False
        fallback_reason = (
            "language_mismatch_recovery"
            if language_mismatch
            else "parser_rejected_recovery" if parser_rejected else "fallback_required"
        )
        retry_reason = (
            "language_mismatch_recovery"
            if language_mismatch
            else "parser_rejected_recovery" if parser_rejected else "retry_required"
        )

        if band == "high":
            if is_protected:
                decision_action = "confirm"
                confirmation_required = True
                reason_code = "protected_confirmation_required"
            elif ambiguity_detected:
                decision_action = "fallback" if policy.fallback_enabled and not fallback_attempted else "retry"
                reason_code = fallback_reason if decision_action == "fallback" else retry_reason
        elif band == "medium":
            normalized_unprotected_command = bool(
                parsed_accepted
                and not is_protected
                and not ambiguity_detected
                and post_processing.post_processing_status == "normalized"
            )
            if normalized_unprotected_command and fallback_attempted:
                decision_action = "execute"
                reason_code = "medium_confidence_normalized_execute"
            elif policy.fallback_enabled and not fallback_attempted:
                decision_action = "fallback"
                reason_code = fallback_reason
            elif is_protected:
                decision_action = "confirm"
                confirmation_required = True
                reason_code = "protected_confirmation_required"
            elif normalized_unprotected_command:
                decision_action = "execute"
                reason_code = "medium_confidence_normalized_execute"
            elif retry_count < policy.max_retry_cycles:
                decision_action = "retry"
                reason_code = retry_reason
            else:
                decision_action = "refuse"
                reason_code = "retry_exhausted"
        elif band == "low":
            if policy.fallback_enabled and not fallback_attempted:
                decision_action = "fallback"
                reason_code = fallback_reason
            elif is_protected:
                decision_action = "confirm"
                confirmation_required = True
                reason_code = "protected_confirmation_required"
            else:
                decision_action = "refuse"
                reason_code = "low_confidence_refusal"
        else:
            # missing confidence
            if (
                parsed_accepted
                and not is_protected
                and policy.allow_missing_confidence_for_unprotected
                and not ambiguity_detected
            ):
                decision_action = "execute"
                reason_code = "missing_confidence_unprotected_allowed"
            elif policy.fallback_enabled and not fallback_attempted:
                decision_action = "fallback"
                reason_code = fallback_reason
            elif is_protected:
                decision_action = "confirm"
                confirmation_required = True
                reason_code = "protected_confirmation_required"
            elif retry_count < policy.max_retry_cycles:
                decision_action = "retry"
                reason_code = retry_reason
            else:
                decision_action = "refuse"
                reason_code = "retry_exhausted"

        if decision_action == "retry" and retry_count >= policy.max_retry_cycles:
            decision_action = "refuse"
            reason_code = "retry_exhausted"
        if decision_action == "fallback" and fallback_attempted:
            if (
                policy.offline_local_allowed
                and parsed_accepted
                and not is_protected
                and band in {"high", "missing_confidence"}
            ):
                decision_action = "execute"
                reason_code = "offline_local_execute"
            elif retry_count < policy.max_retry_cycles:
                decision_action = "retry"
                reason_code = "retry_required"
            else:
                decision_action = "refuse"
                reason_code = "fallback_unavailable"

        telemetry = RecognitionTelemetrySample(
            session_id=recognition_result.session_id,
            event_id=f"recognition-{uuid4().hex}",
            recognition_path=recognition_result.recognition_path,
            confidence_band=band,
            fallback_used=fallback_attempted,
            decision_outcome=decision_action,
            protected_command=is_protected,
            latency_ms=recognition_result.latency_ms,
            profile_id=recognition_result.profile_id,
            closed_vocabulary_id=recognition_result.closed_vocabulary_id,
            qualification_profile_id=recognition_result.qualification_profile_id,
            field_safe=True,
            raw_utterance_present=False,
        )
        return ConfidenceDecisionOutcome(
            intent_id=intent_id,
            decision_band=band,
            decision_action=decision_action,
            protected_command=is_protected,
            fallback_attempted=fallback_attempted,
            confirmation_required=confirmation_required,
            retry_count=retry_count,
            spoken_guidance_surface=_CONFIDENCE_REASON_SURFACES.get(reason_code, "runtime.command.refuse"),
            reason_code=reason_code,
            telemetry=telemetry,
        )

    def _build_recognition_metadata(
        self,
        *,
        recognition_result: CommandRecognitionResult,
        post_processing: CommandPostProcessingOutcome,
    ) -> dict[str, Any]:
        return {
            "session_id": recognition_result.session_id,
            "recognition_path": recognition_result.recognition_path,
            "provider_id": recognition_result.provider_id,
            "capture_attempt_id": recognition_result.capture_attempt_id,
            "profile_id": recognition_result.profile_id,
            "confidence_available": recognition_result.confidence_available,
            "confidence_score": recognition_result.confidence_score,
            "alternative_count": len(recognition_result.alternative_transcripts),
            "detected_language": recognition_result.detected_language,
            "language_candidates": list(recognition_result.language_candidates),
            "latency_ms": recognition_result.latency_ms,
            "dictionary_bias_applied": recognition_result.dictionary_bias_applied,
            "dictionary_bias_mode": recognition_result.dictionary_bias_mode,
            "closed_vocabulary_id": recognition_result.closed_vocabulary_id,
            "endpoint_quality_hints": list(recognition_result.endpoint_quality_hints),
            "qualification_profile_id": recognition_result.qualification_profile_id,
            "error_code": recognition_result.error_code,
            "recognition_source": recognition_result.recognition_source,
            "failure_reason_code": recognition_result.failure_reason_code,
            "selected_language": recognition_result.selected_language,
            "post_processing_status": post_processing.post_processing_status,
            "canonicalization_status": post_processing.canonicalization_status,
            "dictionary_mode": post_processing.dictionary_mode,
            "closed_vocabulary_id_post": post_processing.closed_vocabulary_id,
            "confusion_pair_id": post_processing.confusion_pair_id,
            "substitution_ids": list(post_processing.substitution_ids),
            "ambiguity_flags": list(post_processing.ambiguity_flags),
        }

    def _rerank_command_recognition(
        self,
        recognition_result: CommandRecognitionResult,
    ) -> CommandRecognitionResult:
        transcripts = self._ordered_unique_transcripts(
            recognition_result.primary_transcript,
            recognition_result.alternative_transcripts,
        )
        if len(transcripts) <= 1:
            return recognition_result

        best_transcript = recognition_result.primary_transcript
        best_rank = float("-inf")
        best_intent: str | None = None
        best_parsed_accepted = False
        primary_rank = float("-inf")
        primary_intent: str | None = None
        primary_parsed_accepted = False
        evaluated = 0

        for transcript in transcripts[:6]:
            evaluated += 1
            outcome = process_command_transcript(
                transcript,
                alternative_transcripts=transcripts,
                language_hints=[recognition_result.detected_language]
                if recognition_result.detected_language
                else None,
                dictionary_mode=(
                    recognition_result.dictionary_bias_mode
                    or ("closed_choice" if recognition_result.closed_vocabulary_id else "command_inventory")
                ),
                closed_vocabulary_id=recognition_result.closed_vocabulary_id,
                closed_vocabulary=self._closed_vocabulary_options(recognition_result.closed_vocabulary_id),
            )
            parsed = command_parser.parse_command(
                outcome.canonical_command_text or transcript,
                canonical_command_text=outcome.canonical_command_text or transcript,
            )
            parsed_accepted = bool(parsed and parsed.accepted)
            rank = self._score_command_candidate_for_rerank(
                parsed_intent=parsed,
                post_processing=outcome,
                candidate_text=transcript,
                primary_text=recognition_result.primary_transcript,
            )
            if transcript == recognition_result.primary_transcript:
                primary_rank = rank
                primary_intent = parsed.intent_id if parsed is not None else None
                primary_parsed_accepted = parsed_accepted
            should_select = False
            if parsed_accepted and not best_parsed_accepted:
                should_select = True
            elif parsed_accepted == best_parsed_accepted and rank > best_rank:
                should_select = True

            if should_select:
                best_rank = rank
                best_transcript = transcript
                best_intent = parsed.intent_id
                best_parsed_accepted = parsed_accepted

        if not best_parsed_accepted:
            return recognition_result

        if best_transcript == recognition_result.primary_transcript:
            return recognition_result
        if (
            primary_parsed_accepted
            and not _command_intents_materially_conflict(primary_intent, best_intent)
            and best_rank < primary_rank + 4.0
        ):
            return recognition_result

        logger.info(
            "[STT] Command rerank selected transcript='%s' over primary='%s' intent=%s candidates=%s",
            best_transcript,
            recognition_result.primary_transcript,
            best_intent,
            evaluated,
        )
        alternatives = tuple(
            item for item in transcripts if item and item != best_transcript
        )
        return CommandRecognitionResult(
            session_id=recognition_result.session_id,
            recognition_path=recognition_result.recognition_path,
            provider_id=recognition_result.provider_id,
            primary_transcript=best_transcript,
            confidence_score=recognition_result.confidence_score,
            confidence_available=recognition_result.confidence_available,
            alternative_transcripts=alternatives,
            detected_language=recognition_result.detected_language,
            language_candidates=recognition_result.language_candidates,
            capture_attempt_id=recognition_result.capture_attempt_id,
            profile_id=recognition_result.profile_id,
            dictionary_bias_applied=recognition_result.dictionary_bias_applied,
            dictionary_bias_mode=recognition_result.dictionary_bias_mode,
            closed_vocabulary_id=recognition_result.closed_vocabulary_id,
            endpoint_quality_hints=recognition_result.endpoint_quality_hints,
            capture_attempt=recognition_result.capture_attempt,
            qualification_profile_id=recognition_result.qualification_profile_id,
            latency_ms=recognition_result.latency_ms,
            error_code=recognition_result.error_code,
        )

    def _score_command_candidate_for_rerank(
        self,
        *,
        parsed_intent: ParsedCommandIntent,
        post_processing: CommandPostProcessingOutcome,
        candidate_text: str,
        primary_text: str,
    ) -> float:
        rank = float(parsed_intent.score)
        if parsed_intent.accepted:
            rank += 22.0
        elif parsed_intent.rejection_reason == "ambiguous":
            rank -= 8.0
        elif parsed_intent.rejection_reason == "below_threshold":
            rank -= 4.0
        else:
            rank -= 6.0

        status = post_processing.post_processing_status
        if status == "normalized":
            rank += 1.5
        elif status == "rejected":
            rank -= 12.0

        ambiguity_flags = set(post_processing.ambiguity_flags)
        if "conflicting_alternatives" in ambiguity_flags:
            rank -= 2.5
        if "mixed_language_connector" in ambiguity_flags:
            rank -= 1.5

        token_count = len(post_processing.canonical_command_text.split())
        if token_count > 10:
            rank -= 5.0
        elif token_count > 7:
            rank -= 2.0

        if candidate_text == primary_text:
            rank += 0.5
        return rank

    def _ordered_unique_transcripts(
        self,
        primary: str,
        alternatives: tuple[str, ...] | list[str] | None,
    ) -> tuple[str, ...]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in [primary, *(alternatives or ())]:
            normalized = str(item or "").strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(normalized)
        return tuple(ordered)

    def _closed_vocabulary_options(self, vocabulary_id: str | None) -> tuple[str, ...]:
        return closed_vocabulary_choices(vocabulary_id)

    def _emit_recognition_telemetry(self, sample: RecognitionTelemetrySample) -> None:
        settings_snapshot = self._settings_snapshot()
        confidence_lookup = {"high": 0.9, "medium": 0.7, "low": 0.3}
        confidence_available = sample.confidence_band != "missing_confidence"
        confidence_score = confidence_lookup.get(sample.confidence_band)
        source = "strict_vosk" if sample.recognition_path in {"fallback", "rescue"} else "google_cloud"
        failure_reason = "fallback_required" if sample.decision_outcome in {"fallback", "retry", "refuse"} else None
        failure_category = classify_stt_failure_category(failure_reason)
        recovery_outcome = classify_stt_recovery_outcome(sample.decision_outcome)
        event_status = "failed" if recovery_outcome != "none" else "succeeded"
        event_record = SttTelemetryEventRecord(
            event_id=sample.event_id,
            session_id=sample.session_id,
            candidate_run_id=self.session.session_id,
            event_type="command_recognition",
            source=source,
            rollout_mode=settings_snapshot.stt_rollout_effective_mode,  # type: ignore[arg-type]
            status=event_status,
            confidence_bucket=classify_stt_confidence_bucket(
                confidence_available=confidence_available,
                confidence_score=confidence_score,
            ),
            failure_category=failure_category,  # type: ignore[arg-type]
            recovery_outcome=recovery_outcome,  # type: ignore[arg-type]
            latency_bucket=classify_stt_latency_bucket(latency_ms=sample.latency_ms),
            reason_code=sample.decision_outcome,
        )
        record_stt_observability_event(event=event_record)
        if event_status == "failed":
            record_stt_failure_scenario_result(
                result=build_failure_scenario_from_event(
                    event=event_record,
                    spoken_guidance_surface=f"runtime.command.{sample.decision_outcome}",
                ),
                session_id=sample.session_id,
            )
        record_audio_qualification_run(
            session_id=sample.session_id,
            qualification_profile_id=sample.qualification_profile_id or settings_snapshot.speech_qualification_profile,
            capture_profile_id=sample.profile_id or settings_snapshot.command_capture_profile_id,
            recognition_path=sample.recognition_path,
            capture_complete=sample.decision_outcome in {"execute", "confirm"},
            latency_ms=sample.latency_ms,
            accuracy=None,
            demoted_enhancements=[],
        )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={"command_recognition_telemetry": sample.to_dict()},
            )
        )

    def _emit_turn_taking_window_outcome(
        self,
        *,
        status: str,
        spoken_text: str,
        next_runtime_state: str,
        prompt_surface_id: str,
        prompt_class: str,
        barge_in_allowed: bool,
        closed_vocabulary_id: str | None = None,
        retry_count: int = 0,
        global_safety_only_preemption: bool = False,
        error_code: str | None = None,
    ) -> None:
        outcome = TurnTakingWindowOutcome(
            trigger="turn_taking",
            status=status,
            spoken_text=spoken_text,
            error_code=error_code,
            next_runtime_state=next_runtime_state,
            prompt_surface_id=prompt_surface_id,
            prompt_class=prompt_class,
            barge_in_allowed=barge_in_allowed,
            closed_vocabulary_id=closed_vocabulary_id,
            payload={
                "window_id": f"turn-window-{uuid4().hex[:8]}",
                "global_safety_only_preemption": bool(global_safety_only_preemption),
                "retry_count": max(0, int(retry_count)),
                "prompt_echo_guard_enabled": True,
                "recent_prompt_text_present": bool(spoken_text.strip()),
            },
        )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={"turn_taking_window": outcome.to_dict()},
            )
        )

    def _emit_guided_dialog_outcome(
        self,
        *,
        status: str,
        spoken_text: str,
        next_runtime_state: str,
        closed_vocabulary_id: str | None = None,
        error_code: str | None = None,
        accepted_option_id: str | None = None,
        safe_default_applied: bool = False,
        graceful_exit: bool = False,
        retry_count: int = 0,
        retry_limit: int | None = None,
        fallback_or_exit_reason: str | None = None,
        prompt_echo_suppressed: bool = False,
        preserved_safety_state: str = "guided_context_active",
    ) -> None:
        outcome = GuidedDialogOutcome(
            trigger="guided_dialog",
            status=status,
            spoken_text=spoken_text,
            error_code=error_code,
            next_runtime_state=next_runtime_state,
            closed_vocabulary_id=closed_vocabulary_id,
            payload={
                "dialog_session_id": f"guided-dialog-{uuid4().hex[:8]}",
                "accepted_option_id": accepted_option_id,
                "retry_count": max(0, int(retry_count)),
                "retry_limit": max(0, int(retry_limit or self._settings.closed_vocabulary_retry_limit)),
                "prompt_echo_suppressed": bool(prompt_echo_suppressed),
                "safe_default_applied": bool(safe_default_applied),
                "graceful_exit": bool(graceful_exit),
                "preserved_safety_state": preserved_safety_state,
                "fallback_or_exit_reason": fallback_or_exit_reason,
            },
        )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={"guided_dialog_outcome": outcome.to_dict()},
            )
        )

    def _coerce_command_recognition_result(
        self,
        value: Any,
        *,
        recognition_path: str,
        session_id: str | None = None,
    ) -> CommandRecognitionResult | None:
        if value is None:
            return None
        if isinstance(value, CommandRecognitionResult):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return CommandRecognitionResult(
                session_id=session_id or self.session.session_id,
                recognition_path=recognition_path,
                provider_id=self._provider_state.session_provider,
                primary_transcript=text,
                confidence_score=None,
                confidence_available=False,
                alternative_transcripts=(text,),
                detected_language=self.session.language,
                language_candidates=(self.session.language, "en-US", "ar-EG"),
                profile_id=self._settings.command_capture_profile_id,
                dictionary_bias_applied=self._settings.enable_dictionary_bias,
                dictionary_bias_mode="command_inventory" if self._settings.enable_dictionary_bias else "none",
                qualification_profile_id=self._settings.speech_qualification_profile,
                latency_ms=0,
                error_code=None,
            )
        if isinstance(value, dict):
            payload = dict(value)
            payload.setdefault("session_id", session_id or self.session.session_id)
            payload.setdefault("recognition_path", recognition_path)
            payload.setdefault("provider_id", self._provider_state.session_provider)
            payload.setdefault("primary_transcript", "")
            payload.setdefault("confidence_available", False)
            payload.setdefault("confidence_score", None)
            payload.setdefault("alternative_transcripts", ())
            payload.setdefault("detected_language", self.session.language)
            payload.setdefault("language_candidates", (self.session.language, "en-US", "ar-EG"))
            payload.setdefault("capture_attempt_id", None)
            payload.setdefault("profile_id", self._settings.command_capture_profile_id)
            payload.setdefault("dictionary_bias_applied", self._settings.enable_dictionary_bias)
            payload.setdefault(
                "dictionary_bias_mode",
                "command_inventory" if self._settings.enable_dictionary_bias else "none",
            )
            payload.setdefault("closed_vocabulary_id", None)
            payload.setdefault("endpoint_quality_hints", ())
            payload.setdefault("capture_attempt", None)
            payload.setdefault("qualification_profile_id", self._settings.speech_qualification_profile)
            payload.setdefault("latency_ms", 0)
            payload.setdefault("error_code", None)
            payload["alternative_transcripts"] = tuple(payload.get("alternative_transcripts", ()))
            payload["language_candidates"] = tuple(payload.get("language_candidates", ()))
            payload["endpoint_quality_hints"] = tuple(payload.get("endpoint_quality_hints", ()))
            try:
                return CommandRecognitionResult(**payload)
            except Exception:  # noqa: BLE001
                return None
        return None

    def _listen_command_result_bounded(
        self,
        *,
        recognition_path: str = "local_first",
        session_id: str | None = None,
    ) -> CommandRecognitionResult | None:
        snapshot = self._settings_snapshot()
        timeout = self._settings.max_listen_seconds
        phrase_limit = min(self._settings.max_listen_seconds, 10.0)
        listener = self._listener
        if listener is None:
            return None
        if recognition_path in {"rescue", "fallback"} and not (
            snapshot.command_fallback_enabled or snapshot.command_rescue_enabled
        ):
            return None
        usage_mode = "command"
        capture_profile_id = snapshot.command_capture_profile_id
        qualification_profile_id = snapshot.speech_qualification_profile
        dictionary_bias_mode = "command_inventory" if snapshot.enable_dictionary_bias else "none"
        language_candidates = [self.session.language, "en-US", "ar-EG"]
        stop_listener = getattr(listener, "request_stop", None)

        def _invoke_listener() -> Any:
            listen_command_result = getattr(listener, "listen_command_result", None)
            if callable(listen_command_result):
                try:
                    return listen_command_result(
                        timeout_s=timeout,
                        phrase_time_limit_s=phrase_limit,
                        interrupt_event=self._interrupt_event,
                        languages=language_candidates,
                        recognition_path=recognition_path,
                        session_id=session_id or self.session.session_id,
                        usage_mode=usage_mode,
                        capture_profile_id=capture_profile_id,
                        dictionary_bias_mode=dictionary_bias_mode,
                        qualification_profile_id=qualification_profile_id,
                    )
                except TypeError:
                    try:
                        return listen_command_result(
                            timeout=timeout,
                            phrase_time_limit=phrase_limit,
                            interrupt_event=self._interrupt_event,
                            recognition_path=recognition_path,
                            usage_mode=usage_mode,
                            capture_profile_id=capture_profile_id,
                            dictionary_bias_mode=dictionary_bias_mode,
                            qualification_profile_id=qualification_profile_id,
                        )
                    except TypeError:
                        return listen_command_result()

            listen_command = getattr(listener, "listen_command", None)
            if callable(listen_command):
                try:
                    return listen_command(
                        timeout=timeout,
                        phrase_time_limit=phrase_limit,
                        interrupt_event=self._interrupt_event,
                        recognition_path=recognition_path,
                    )
                except TypeError:
                    return listen_command()
            return None

        result_holder: dict[str, Any] = {}
        completed = threading.Event()

        def _runner() -> None:
            try:
                result_holder["value"] = _invoke_listener()
            except Exception as exc:  # noqa: BLE001
                result_holder["error"] = exc
            finally:
                completed.set()

        worker = threading.Thread(target=_runner, name="RuntimeListenBounded", daemon=True)
        worker.start()
        cloud_timeout_s = float(
            getattr(snapshot, "stt_cloud_timeout_s", getattr(self._settings, "stt_cloud_timeout_s", 3.0))
        )
        recognition_grace_s = max(4.0, min(8.0, cloud_timeout_s + 5.0))
        deadline = time.perf_counter() + max(0.1, float(timeout)) + recognition_grace_s
        while not completed.wait(timeout=0.01):
            if self._interrupt_event.is_set() or time.perf_counter() >= deadline:
                if callable(stop_listener):
                    stop_listener()
                return None

        if result_holder.get("error") is not None:
            raise result_holder["error"]
        return self._coerce_command_recognition_result(
            result_holder.get("value"),
            recognition_path=recognition_path,
            session_id=session_id,
        )
        return None

    def _listen_command_bounded(self) -> str | None:
        recognition_result = self._listen_command_result_bounded(recognition_path="local_first")
        if recognition_result is None or recognition_result.error_code:
            return None
        return recognition_result.primary_transcript

    def _emit_timeout_outcome(self, *, stage: str) -> None:
        spoken = self._settings.speak_localized(
            "انتهت مهلة الاستماع، ما زلت جاهزاً.",
            "Listening timed out. I am still ready.",
            priority="action_confirmation",
        )
        error_code = "listen_timeout" if stage == "listening" else "speak_timeout"
        self._emit_recovery_outcome(
            RuntimeRecoveryOutcome(
                trigger="timeout",
                status="recovered",
                spoken_text=spoken,
                error_code=error_code,
                duration_ms=int(self._settings.max_listen_seconds * 1000),
                next_runtime_state=RuntimeState.STANDBY.value,
                completion_status="timeout",
            )
        )
        self._emit_assistant(spoken, priority="action_confirmation")

    def _interrupt_signal_type(self, text: str) -> InterruptDetectionResult | None:
        raw_text = str(text or "").strip()
        if not raw_text:
            return None
        match = detect_interrupt_signal(raw_text)
        if match is None:
            return None
        return InterruptDetectionResult(
            raw_utterance=raw_text,
            normalized_utterance=match.normalized_phrase,
            matched_vocabulary_ids=match.matched_vocabulary_ids,
            signal_type=match.signal_type,
            accepted=True,
            active_runtime_state=self.session.state.value,
            active_language=self.session.language,
            runtime_load_profile=self._runtime_load_profile(),
        )

    def _handle_interrupt_signal(self, detection: InterruptDetectionResult | str) -> None:
        if isinstance(detection, str):
            normalized = self._interrupt_signal_type(detection)
            detection = normalized or InterruptDetectionResult(
                raw_utterance=detection,
                normalized_utterance=str(detection or "").strip().lower(),
                matched_vocabulary_ids=(),
                signal_type=str(detection or "stop"),
                accepted=True,
                active_runtime_state=self.session.state.value,
                active_language=self.session.language,
                runtime_load_profile=self._runtime_load_profile(),
            )

        self._interrupt_event.set()
        started_at = time.perf_counter()
        self._interrupt_latched = True
        self._active = False
        self._wake_cycle_locked = False
        request_stop = getattr(self._tts_engine, "request_stop", None)
        if callable(request_stop):
            request_stop()
        listener_stop = getattr(self._listener, "request_stop", None)
        if callable(listener_stop):
            listener_stop()

        operation = self._active_operation_context
        degraded_mode = bool(self._provider_state.degraded_mode)
        degraded_reason = self._provider_state.degraded_reason
        status = "recovered"
        completion_status = "interrupted"
        error_code = "interrupt_applied"
        cancellation_state = None
        follow_on_work_suppressed = False
        if operation is not None:
            operation.follow_on_work_suppressed = True
            follow_on_work_suppressed = True
            if operation.reversible:
                operation.cancellation_state = "cancelled"
                cancellation_state = "cancelled"
            else:
                operation.cancellation_state = "best_effort_only"
                cancellation_state = "best_effort_only"
                status = "best_effort_only"
                completion_status = "partial"
                error_code = "interrupt_best_effort"
                degraded_mode = True
                degraded_reason = degraded_reason or "provider_stall"

        surface_id = _INTERRUPT_SURFACE_IDS.get(detection.signal_type, _INTERRUPT_SURFACE_IDS["stop"])
        ack = self._resolve_runtime_critical_prompt(
            surface_id,
            priority="warning",
            preempt=True,
        )["text"]
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        latency_record = record_interrupt_preemption(
            session_id=self.session.session_id,
            interrupt_signal_type=detection.signal_type,
            preemption_latency_ms=duration_ms,
            runtime_load_profile=detection.runtime_load_profile,
        )
        self._emit_recovery_outcome(
            RuntimeRecoveryOutcome(
                trigger="interrupt",
                status=status,
                spoken_text=ack,
                error_code=error_code,
                duration_ms=duration_ms,
                next_runtime_state=RuntimeState.STANDBY.value,
                completion_status=completion_status,
                interrupt_signal_type=detection.signal_type,
                preemption_latency_ms=duration_ms,
                payload={
                    "interrupt_detection": detection.to_dict(),
                    "latency_target_bucket": latency_record.latency_target_bucket,
                    "operation": operation.to_dict() if operation is not None else None,
                },
                matched_vocabulary_ids=detection.matched_vocabulary_ids,
                follow_on_work_suppressed=follow_on_work_suppressed,
                cancellation_state=cancellation_state,
                degraded_mode=degraded_mode,
                degraded_reason=degraded_reason,
                runtime_load_profile=detection.runtime_load_profile,
            )
        )
        self._emit_assistant(ack, priority="warning")
        self._transition_and_emit(RuntimeState.STANDBY, force=True)
        if operation is None:
            self._interrupt_event.clear()
            self._interrupt_latched = False

    def _emit_recovery_outcome(self, outcome: RuntimeRecoveryOutcome) -> None:
        payload = outcome.to_dict()
        payload["recovery_trigger"] = payload.pop("trigger")
        payload["next_state"] = payload.pop("next_runtime_state")
        if payload["recovery_trigger"] == "interrupt":
            payload = attach_runtime_diagnostic_fields(
                payload,
                session_or_run_id=self.session.session_id,
                event_category="interrupt",
                status_or_decision=outcome.status,
                reason_code=outcome.error_code,
                provider_id=outcome.provider_id or self._provider_state.session_provider,
                provider_availability=self._provider_availability_for_session(),
                degraded_mode=outcome.degraded_mode,
                degraded_reason=outcome.degraded_reason,
                next_state=payload.get("next_state"),
                latency_ms=outcome.preemption_latency_ms,
                user_outcome=outcome.spoken_text,
            )
        elif payload["recovery_trigger"] == "offline_policy":
            payload = attach_runtime_diagnostic_fields(
                payload,
                session_or_run_id=self.session.session_id,
                event_category="offline_policy",
                status_or_decision=outcome.offline_policy_decision or outcome.status,
                reason_code=outcome.error_code,
                provider_id=outcome.provider_id or self._provider_state.session_provider,
                provider_availability=self._provider_availability_for_session(),
                degraded_mode=outcome.degraded_mode,
                degraded_reason=outcome.degraded_reason,
                next_state=payload.get("next_state"),
                latency_ms=outcome.duration_ms,
                user_outcome=outcome.spoken_text,
            )
        elif payload["recovery_trigger"] == "provider_failure":
            payload = attach_runtime_diagnostic_fields(
                payload,
                session_or_run_id=self.session.session_id,
                event_category="provider_selection",
                status_or_decision=outcome.status,
                reason_code=outcome.error_code,
                provider_id=outcome.provider_id or self._provider_state.session_provider,
                provider_availability=self._provider_availability_for_session(),
                degraded_mode=outcome.degraded_mode or self._provider_state.degraded_mode,
                degraded_reason=outcome.degraded_reason or self._provider_state.degraded_reason,
                next_state=payload.get("next_state"),
                latency_ms=outcome.duration_ms,
                user_outcome=outcome.spoken_text,
            )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=payload,
            )
        )

    def _runtime_load_profile(self) -> str:
        if self._active_operation_context is not None or self.session.state in {
            RuntimeState.THINKING,
            RuntimeState.SPEAKING,
        }:
            return "moderate"
        return "normal"

    def _clear_active_operation(self) -> None:
        self._active_operation_context = None
        self._interrupt_event.clear()
        self._interrupt_latched = False

    def _capability_id_for_intent(self, intent_id: str | None) -> str | None:
        if not intent_id:
            return None
        descriptor = None
        try:
            from controllers import capability_registry as cap_registry

            descriptor = cap_registry.get_default_registry().descriptor_for_intent(intent_id)
        except Exception:  # noqa: BLE001
            descriptor = None
        if descriptor is not None:
            return descriptor.capability_id
        fallback_map = {
            "get_system_status": "system_status",
            "enable_OCR": "ocr",
            "disable_OCR": "ocr",
            "enable_money_detection": "money_detection",
            "disable_money_detection": "money_detection",
            "recognize_face": "face_recognition",
            "recognize_emotion": "emotion_recognition",
        }
        return fallback_map.get(intent_id)

    def _requires_network_for_intent(self, intent_id: str | None) -> bool:
        provider_requires_network = False
        if self._provider_registry is not None:
            provider_requires_network = self._provider_registry.requires_network(
                self._provider_state.session_provider
            )
        intent_requires_network = intent_id in {
            "enable_OCR",
            "disable_OCR",
            "enable_money_detection",
            "disable_money_detection",
            "recognize_face",
            "recognize_emotion",
            "get_system_status",
        }
        return provider_requires_network and intent_requires_network

    def _is_reversible_operation(self, *, intent_id: str | None, requires_network: bool) -> bool:
        if requires_network:
            return False
        # Capability flows that can cross non-reversible boundaries should be
        # reported as best-effort cancellation when interrupted mid-flight.
        non_reversible_intents = {
            "enable_OCR",
            "disable_OCR",
            "enable_money_detection",
            "disable_money_detection",
            "recognize_face",
            "recognize_emotion",
        }
        return intent_id not in non_reversible_intents

    def _provider_availability_for_session(self) -> str:
        if self._provider_registry is None:
            return ProviderAvailability.UNAVAILABLE.value
        return self._provider_registry.get_availability(self._provider_state.session_provider).value

    def _connectivity_state(self) -> dict[str, Any]:
        snapshot = self._settings.get_connectivity_state_snapshot()
        normalized = connectivity_state_from_snapshot(snapshot, now_s=time.time())
        payload = normalized.to_dict()
        payload["grace_window_s"] = snapshot.get("grace_window_s")
        return payload

    def _refresh_connectivity_state(self, *, source: str) -> dict[str, Any]:
        probe_result: dict[str, Any]
        try:
            raw_probe_result = self._network_probe.probe(source=source)
            probe_result = raw_probe_result.to_dict() if hasattr(raw_probe_result, "to_dict") else dict(raw_probe_result)
        except Exception:  # noqa: BLE001
            logger.exception("[RUNTIME] Connectivity probe failed")
            probe_result = {
                "source": source,
                "target_label": "tcp_probe",
                "status": "uncertain",
                "latency_ms": 0,
                "checked_at": time.time(),
                "failure_reason": "probe_exception",
            }

        snapshot = self._settings.apply_network_probe_result(
            probe_result,
            grace_window_s=self._settings.connectivity_grace_window_s,
            persist=False,
        )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={
                    "connectivity_probe_source": probe_result.get("source"),
                    "connectivity_probe_status": probe_result.get("status"),
                    "connectivity_probe_latency_ms": probe_result.get("latency_ms"),
                    "connectivity_probe_failure_reason": probe_result.get("failure_reason"),
                    "override_mode": snapshot.get("override_mode"),
                    "detected_status": snapshot.get("detected_status"),
                    "effective_network_available": snapshot.get("effective_network_available"),
                    "grace_window_active": snapshot.get("grace_window_active"),
                    "grace_window_deadline_at": snapshot.get("grace_window_deadline_at"),
                },
            )
        )
        return snapshot

    def _emit_startup_readiness(self, *, status: str, degraded_reason: str | None) -> None:
        latency_ms = int((time.perf_counter() - self._startup_started_at) * 1000)
        connectivity = self._connectivity_state()
        provider_availability = self._provider_availability_for_session()
        provider_requires_network = False
        if self._provider_registry is not None:
            provider_requires_network = self._provider_registry.requires_network(
                self._provider_state.session_provider
            )
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=attach_runtime_diagnostic_fields(
                    {
                    "startup_status": status,
                    "startup_latency_ms": latency_ms,
                    "degraded_reason": degraded_reason,
                    "provider_id": self._provider_state.session_provider,
                    "provider_availability": provider_availability,
                    "requires_network": provider_requires_network,
                    "override_mode": connectivity.get("override_mode"),
                    "detected_status": connectivity.get("detected_status"),
                    "effective_network_available": connectivity.get("effective_network_available"),
                    "grace_window_active": connectivity.get("grace_window_active"),
                    "grace_window_deadline_at": connectivity.get("grace_window_deadline_at"),
                    },
                    session_or_run_id=self.session.session_id,
                    event_category="provider_selection",
                    status_or_decision=status,
                    reason_code=degraded_reason,
                    provider_id=self._provider_state.session_provider,
                    provider_availability=provider_availability,
                    degraded_mode=bool(degraded_reason),
                    degraded_reason=degraded_reason,
                    next_state=self.session.state.value,
                    latency_ms=latency_ms,
                ),
            )
        )

    def _emit_non_speech_cue(self, state: str) -> None:
        if not self._settings.non_speech_cues_enabled:
            return
        cue_id = map_non_speech_cue(state)
        if not cue_id:
            return
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={"cue_id": cue_id, "cue_state": state},
            )
        )

    def _resolve_runtime_critical_prompt(
        self,
        surface_id: str,
        *,
        format_kwargs: dict[str, Any] | None = None,
        interrupt_event: threading.Event | None = None,
        priority: str = "info",
        preempt: bool = False,
    ) -> dict[str, Any]:
        resolved = self._settings.resolve_critical_surface(surface_id, format_kwargs=format_kwargs)
        if resolved.get("text"):
            self._settings.speak(
                resolved["text"],
                interrupt_event=interrupt_event,
                priority=priority,
                preempt=preempt,
            )

        payload: dict[str, Any] = {
            "critical_prompt_surface_id": resolved.get("surface_id"),
            "prompt_key": resolved.get("prompt_key"),
            "integrity_status": resolved.get("integrity_status"),
            "fallback_used": bool(resolved.get("fallback_used", False)),
            "language": resolved.get("language"),
            "catalog_source": resolved.get("catalog_source"),
        }
        if resolved.get("failure_reason"):
            payload["failure_reason"] = resolved["failure_reason"]
        if resolved.get("fallback_used"):
            payload["prompt_integrity_failure"] = True
            resolved["signal_emitted"] = True
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=payload,
            )
        )
        return resolved

    def _emit_dispatch_outcome(self, result: Any, *, dispatch_duration_ms: int) -> None:
        if hasattr(result, "to_dict") and callable(result.to_dict):
            payload = {"command_result": result.to_dict()}
        elif isinstance(result, dict):
            payload = {"command_result": dict(result)}
        else:
            payload = {"command_result": str(result)}
        payload["dispatch_duration_ms"] = dispatch_duration_ms
        if isinstance(result, CommandExecutionResult):
            payload["intent_id"] = result.intent_id
            payload["status"] = result.status
            if result.metadata.get("canonical_command_text"):
                payload["canonical_command_text"] = result.metadata.get("canonical_command_text")
            if isinstance(result.metadata.get("recognition"), dict):
                payload["recognition_metadata"] = dict(result.metadata["recognition"])
            if result.metadata.get("offline_policy_decision"):
                payload["offline_policy_decision"] = result.metadata.get("offline_policy_decision")
            if result.metadata.get("requires_network") is not None:
                payload["requires_network"] = result.metadata.get("requires_network")
            if result.metadata.get("override_mode"):
                payload["override_mode"] = result.metadata.get("override_mode")
            if result.metadata.get("detected_status"):
                payload["detected_status"] = result.metadata.get("detected_status")
            if result.metadata.get("provider_availability"):
                payload["provider_availability"] = result.metadata.get("provider_availability")
            if result.metadata.get("effective_network_available") is not None:
                payload["effective_network_available"] = result.metadata.get("effective_network_available")
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload=payload,
            )
        )

    def _normalize_dispatch_result(self, result: Any) -> str:
        if result is None:
            return self._settings.speak_localized(
                "معذرة، لم افهم هذا الامر",
                "Sorry, I didn't understand that command.",
                priority="action_confirmation",
            )
        if isinstance(result, CommandExecutionResult):
            return result.spoken_text
        if hasattr(result, "spoken_text") and isinstance(result.spoken_text, str):
            return result.spoken_text
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and isinstance(result.get("spoken_text"), str):
            return result["spoken_text"]
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            return str(result)

    def _handle_recoverable_failure(self, err: Exception, *, stage: str) -> None:
        logger.exception("[RUNTIME] Recoverable runtime failure")
        self.session.last_error = str(err)
        self._transition_and_emit(RuntimeState.ERROR, force=True)

        if self._provider_registry is None:
            self._provider_registry = create_default_provider_registry(
                default_language=self._settings.language,
                listener_factory=self._listener_factory,
                tts_engine_factory=self._tts_engine_factory,
                wake_detector_factory=self._wake_detector_factory,
                speakkit_listener_factory=self._speakkit_listener_factory,
                speakkit_tts_factory=self._speakkit_tts_engine_factory,
                speakkit_wake_factory=self._speakkit_wake_detector_factory,
            )

        failure = resolve_runtime_failure(
            active_provider=self._provider_state.session_provider,
            recoverable=True,
            stage=stage,
            registry=self._provider_registry,
        )

        if failure.fallback_applied and failure.fallback_provider:
            previous_provider = self._provider_state.session_provider
            self._activate_provider(failure.fallback_provider)
            self._provider_state.fallback_from = previous_provider
            self._provider_state.fallback_to = failure.fallback_provider
            self._provider_state.degraded_mode = True
            self._provider_state.degraded_reason = failure.reason_code
            self._emit_config()

        next_state = RuntimeState(failure.next_state)
        self._emit(
            error_event(
                self.session,
                message=str(err),
                recoverable=True,
                next_state=next_state,
                provider=failure.active_provider,
                stage=failure.stage,
                fallback_applied=failure.fallback_applied,
                fallback_to=failure.fallback_provider,
                manual_restart_required=failure.manual_restart_required,
                reason_code=failure.reason_code,
            )
        )
        self._emit_recovery_outcome(
            RuntimeRecoveryOutcome(
                trigger="provider_failure",
                status="fallback_applied" if failure.fallback_applied else "safe_refusal",
                spoken_text=str(err),
                error_code=failure.reason_code,
                duration_ms=0,
                next_runtime_state=next_state.value,
                completion_status="failed",
                capability_id=None,
                provider_id=failure.active_provider,
            )
        )

        self._active = False
        self._wake_cycle_locked = False
        if next_state == RuntimeState.OFFLINE:
            self._transition_and_emit(RuntimeState.OFFLINE, force=True)
            self._stop_event.set()
            self._finalized = True
            return

        self._transition_and_emit(RuntimeState.STANDBY, force=True)

    def _handle_unrecoverable_failure(self, err: Exception, *, stage: str) -> None:
        logger.exception("[RUNTIME] Unrecoverable runtime failure")
        self.session.last_error = str(err)
        self._transition_and_emit(RuntimeState.ERROR, force=True)
        self._emit(
            error_event(
                self.session,
                message=str(err),
                recoverable=False,
                next_state=RuntimeState.OFFLINE,
                provider=self._provider_state.session_provider,
                stage=stage,
                fallback_applied=False,
                manual_restart_required=True,
                reason_code="unrecoverable_failure",
            )
        )
        self._emit_recovery_outcome(
            RuntimeRecoveryOutcome(
                trigger="provider_failure",
                status="safe_refusal",
                spoken_text=str(err),
                error_code="unrecoverable_failure",
                duration_ms=0,
                next_runtime_state=RuntimeState.OFFLINE.value,
                completion_status="failed",
                provider_id=self._provider_state.session_provider,
            )
        )
        self._active = False
        self._wake_cycle_locked = False
        self._transition_and_emit(RuntimeState.OFFLINE, force=True)
        self._stop_event.set()
        self._finalized = True

    def _run_voice_onboarding(self, session_lang: str) -> None:
        if session_lang:
            self._settings.persist_onboarding_configuration(language=session_lang)

        for _ in range(self._max_onboarding_attempts):
            answer, prompt_text = self._announce_and_listen_with_barge_in(
                "runtime.onboarding.language",
                ["ar-EG", "en-US"],
                prompt="[SETUP] Language",
                timeout=12,
                phrase_time_limit=8,
                allow_barge_in=False,
            )
            answer = self._resolve_onboarding_prompt_echo(
                answer=answer,
                prompt_text=prompt_text,
                languages=["ar-EG", "en-US"],
                prompt="[SETUP] Language",
                timeout=12,
                phrase_time_limit=8,
                accept_answer=lambda candidate: self._parse_onboarding_language_choice(candidate) is not None,
            )
            if not answer:
                self._announce_runtime_critical_prompt("resolver.clarification.language.required")
                continue
            if self._is_onboarding_noise_response(answer):
                logger.info("[SETUP] Ignoring wake/noise-like language response: %s", answer)
                self._announce_runtime_critical_prompt("resolver.clarification.language.required")
                continue
            selected_language = self._parse_onboarding_language_choice(answer)
            if selected_language:
                self._settings.persist_onboarding_configuration(language=selected_language)
                break
            self._announce_runtime_critical_prompt("resolver.clarification.language.required")
        self._emit_config()

        for _ in range(self._max_onboarding_attempts):
            answer, prompt_text = self._announce_and_listen_with_barge_in(
                "runtime.onboarding.voice",
                [self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Gender",
                timeout=12,
                phrase_time_limit=8,
                allow_barge_in=False,
            )
            answer = self._resolve_onboarding_prompt_echo(
                answer=answer,
                prompt_text=prompt_text,
                languages=[self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Gender",
                timeout=12,
                phrase_time_limit=8,
                accept_answer=lambda candidate: self._parse_onboarding_voice_choice(candidate) is not None,
            )
            if not answer:
                self._announce_runtime_critical_prompt("resolver.clarification.voice.required")
                continue
            if self._is_onboarding_noise_response(answer):
                logger.info("[SETUP] Ignoring wake/noise-like voice response: %s", answer)
                self._announce_runtime_critical_prompt("resolver.clarification.voice.required")
                continue
            selected_voice = self._parse_onboarding_voice_choice(answer)
            if selected_voice:
                self._settings.persist_onboarding_configuration(voice_gender=selected_voice)
                break
            self._announce_runtime_critical_prompt("resolver.clarification.voice.required")
        self._emit_config()

        for _ in range(self._max_onboarding_attempts):
            answer, prompt_text = self._announce_and_listen_with_barge_in(
                "runtime.onboarding.speed",
                [self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Speed",
                timeout=12,
                phrase_time_limit=8,
                allow_barge_in=False,
            )
            answer = self._resolve_onboarding_prompt_echo(
                answer=answer,
                prompt_text=prompt_text,
                languages=[self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Speed",
                timeout=12,
                phrase_time_limit=8,
                accept_answer=lambda candidate: self._parse_onboarding_speed_choice(candidate) is not None,
            )
            if not answer:
                continue
            if self._is_onboarding_noise_response(answer):
                logger.info("[SETUP] Ignoring wake/noise-like speed response: %s", answer)
                continue
            parsed_speed = self._parse_onboarding_speed_choice(answer)
            if parsed_speed is None:
                continue
            self._settings.persist_onboarding_configuration(speech_speed=parsed_speed)
            break
        self._emit_config()

        for _ in range(self._max_onboarding_attempts * 2):
            if self._stop_event.is_set() or self._settings.is_configured():
                break

            name, prompt_text = self._announce_and_listen_with_barge_in(
                "runtime.onboarding.name",
                [self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Name",
                timeout=14,
                phrase_time_limit=9,
                allow_barge_in=False,
            )
            name = self._resolve_onboarding_prompt_echo(
                answer=name,
                prompt_text=prompt_text,
                languages=[self._settings.language, "en-US", "ar-EG"],
                prompt="[SETUP] Name",
                timeout=14,
                phrase_time_limit=9,
                accept_answer=lambda candidate: self._is_plausible_username(candidate),
            )
            if not name:
                self._announce_runtime_critical_prompt("runtime.onboarding.name_retry")
                continue
            name = name.strip()
            if self._is_onboarding_noise_response(name):
                logger.info("[SETUP] Ignoring wake/noise-like name response: %s", name)
                self._announce_runtime_critical_prompt("runtime.onboarding.name_retry")
                continue
            if not self._is_plausible_username(name):
                self._announce_runtime_critical_prompt("runtime.onboarding.name_retry")
                continue

            name_confirmed = False
            for _confirm_attempt in range(2):
                confirm, confirm_prompt_text = self._announce_and_listen_with_barge_in(
                    "runtime.onboarding.name_confirm",
                    [self._settings.language, "en-US", "ar-EG"],
                    format_kwargs={"name": name},
                    prompt="[SETUP] Confirm",
                    timeout=10,
                    phrase_time_limit=6,
                    allow_barge_in=False,
                )
                confirm = self._resolve_onboarding_prompt_echo(
                    answer=confirm,
                    prompt_text=confirm_prompt_text,
                    languages=[self._settings.language, "en-US", "ar-EG"],
                    prompt="[SETUP] Confirm",
                    timeout=10,
                    phrase_time_limit=6,
                )
                if confirm and self._is_yes(confirm):
                    self._settings.persist_onboarding_configuration(username=name)
                    self._emit_config()
                    self._announce_runtime_critical_prompt("runtime.onboarding.saved")
                    name_confirmed = True
                    break
                if confirm:
                    break

            if name_confirmed:
                break

            self._announce_runtime_critical_prompt("runtime.onboarding.retry")

    def _activate_provider(self, provider_id: str) -> None:
        if self._provider_registry is None:
            raise RuntimeError("provider registry is not initialized")
        bundle: ProviderBundle = self._provider_registry.require(provider_id)
        self._listener = bundle.stt_service
        self._tts_engine = bundle.tts_service
        self._wake_detector = bundle.wake_service
        self._settings.attach_listener(self._listener)
        self._settings.attach_tts_engine(self._tts_engine)
        self._provider_state.session_provider = bundle.profile.provider_id

    def request_provider_switch(self, provider_id: str) -> dict[str, Any]:
        decision = resolve_provider_switch_request(
            active_provider=self._provider_state.session_provider,
            requested_provider=provider_id,
            runtime_active=self.running or self._initialized,
        )
        snapshot = self._settings.request_speech_provider(
            provider_id,
            runtime_active=decision.deferred_until_restart,
        )
        self._provider_state.persisted_provider = snapshot.get("speech_provider", LEGACY_PROVIDER_ID)
        self._provider_state.pending_provider = snapshot.get("pending_speech_provider")
        self._provider_state.deferred_until_restart = bool(snapshot.get("deferred_provider_switch", False))

        if self._initialized and not decision.deferred_until_restart:
            self._activate_provider(decision.applied_provider)
        self._emit_config()
        return {
            "active_provider": self._provider_state.session_provider,
            "persisted_provider": self._provider_state.persisted_provider,
            "pending_provider": self._provider_state.pending_provider,
            "deferred_until_restart": self._provider_state.deferred_until_restart,
        }

    def _transition_and_emit(self, next_state: RuntimeState, *, force: bool = False) -> None:
        if self.session.state != next_state:
            try:
                self.session.transition_to(next_state)
            except ValueError:
                if not force:
                    raise
                self._force_state(next_state)
        record_runtime_state_transition(
            session_id=self.session.session_id,
            state=next_state.value,
            timestamp_s=time.perf_counter(),
        )
        self._emit(status_event(self.session, next_state))

    def _force_state(self, next_state: RuntimeState) -> None:
        self.session.state = next_state
        self.session.active = next_state in ACTIVE_RUNTIME_STATES
        self.session.stop_requested = next_state in {RuntimeState.STOPPING, RuntimeState.OFFLINE}

    def _finalize_shutdown(self) -> None:
        if self._finalized:
            return
        if self.session.state != RuntimeState.OFFLINE:
            self._emit_assistant(
                self._settings.speak_localized(
                    "تم إيقاف المساعد.",
                    "Assistant stopped.",
                    priority="warning",
                    preempt=True,
                )
            )
            self._active = False
            self._transition_and_emit(RuntimeState.OFFLINE, force=True)
        metrics = get_runtime_latency_metrics(self.session.session_id)
        if metrics:
            logger.info(
                "[RELEASE_GATE] runtime_latency_metrics session=%s metrics=%s",
                self.session.session_id,
                metrics,
            )
        clear_runtime_latency_metrics(self.session.session_id)
        self._finalized = True
        logger.info("[RUNTIME] shutdown complete session=%s", self.session.session_id)

    def _settings_snapshot(self) -> SettingsSnapshot:
        snapshot = self._settings.get_settings_snapshot()
        return SettingsSnapshot(
            language=snapshot["language"],
            voice_gender=snapshot["voice_gender"],
            speech_speed=float(snapshot["speech_speed"]),
            username=snapshot.get("username", ""),
            speech_provider=snapshot.get("speech_provider", LEGACY_PROVIDER_ID),
            pending_speech_provider=snapshot.get("pending_speech_provider"),
            deferred_provider_switch=bool(snapshot.get("deferred_provider_switch", False)),
            max_listen_seconds=float(snapshot.get("max_listen_seconds", 8.0)),
            max_speak_seconds=float(snapshot.get("max_speak_seconds", 8.0)),
            priority_coalescing_window_s=float(snapshot.get("priority_coalescing_window_s", 2.0)),
            concise_word_limit=int(snapshot.get("concise_word_limit", 12)),
            wake_primary_mode=str(snapshot.get("wake_primary_mode", WAKE_MODE_KEYWORD_LOW_POWER)),
            wake_fallback_mode=str(snapshot.get("wake_fallback_mode", WAKE_MODE_HARDWARE_TRIGGER)),
            wake_dev_fallback_mode=str(snapshot.get("wake_dev_fallback_mode", "stt_based_wake")),
            stt_wake_allowed_in_production=bool(snapshot.get("stt_wake_allowed_in_production", False)),
            low_power_standby_enabled=bool(snapshot.get("low_power_standby_enabled", True)),
            non_speech_cues_enabled=bool(snapshot.get("non_speech_cues_enabled", True)),
            network_available=bool(snapshot.get("network_available", True)),
            network_override_mode=str(snapshot.get("network_override_mode", "auto")),
            connectivity_detected_status=str(snapshot.get("connectivity_detected_status", "online")),
            connectivity_last_confirmed_status=str(snapshot.get("connectivity_last_confirmed_status", "online")),
            connectivity_last_confirmed_at=(
                float(snapshot["connectivity_last_confirmed_at"])
                if snapshot.get("connectivity_last_confirmed_at") is not None
                else None
            ),
            connectivity_grace_window_deadline_at=(
                float(snapshot["connectivity_grace_window_deadline_at"])
                if snapshot.get("connectivity_grace_window_deadline_at") is not None
                else None
            ),
            connectivity_probe_generation=int(snapshot.get("connectivity_probe_generation", 0)),
            connectivity_startup_reset_applied=bool(snapshot.get("connectivity_startup_reset_applied", False)),
            connectivity_grace_window_s=float(snapshot.get("connectivity_grace_window_s", 2.0)),
            offline_allowlisted_capabilities=tuple(snapshot.get("offline_allowlisted_capabilities", ("system_status",))),
            command_confidence_high_threshold=float(snapshot.get("command_confidence_high_threshold", 0.82)),
            command_confidence_medium_threshold=float(snapshot.get("command_confidence_medium_threshold", 0.55)),
            command_protected_threshold=float(snapshot.get("command_protected_threshold", 0.9)),
            command_allow_missing_confidence_for_unprotected=bool(
                snapshot.get("command_allow_missing_confidence_for_unprotected", True)
            ),
            command_max_retry_cycles=int(snapshot.get("command_max_retry_cycles", 1)),
            command_fallback_enabled=bool(snapshot.get("command_fallback_enabled", True)),
            command_rescue_enabled=bool(
                snapshot.get("command_rescue_enabled", snapshot.get("command_fallback_enabled", True))
            ),
            command_offline_local_allowed=bool(snapshot.get("command_offline_local_allowed", True)),
            standby_capture_profile_id=str(
                snapshot.get("standby_capture_profile_id", "standby_wake.default")
            ),
            onboarding_capture_profile_id=str(
                snapshot.get("onboarding_capture_profile_id", "onboarding.default")
            ),
            command_capture_profile_id=str(
                snapshot.get("command_capture_profile_id", "command.default")
            ),
            confirmation_capture_profile_id=str(
                snapshot.get("confirmation_capture_profile_id", "confirmation.default")
            ),
            closed_vocabulary_retry_limit=max(1, int(snapshot.get("closed_vocabulary_retry_limit", 1))),
            speech_qualification_profile=str(snapshot.get("speech_qualification_profile", "default")),
            enable_audio_noise_suppression=bool(snapshot.get("enable_audio_noise_suppression", False)),
            enable_capture_relisten=bool(snapshot.get("enable_capture_relisten", True)),
            enable_dictionary_bias=bool(snapshot.get("enable_dictionary_bias", True)),
            stt_rollout_requested_mode=str(snapshot.get("stt_rollout_requested_mode", "shadow")),
            stt_rollout_effective_mode=str(snapshot.get("stt_rollout_effective_mode", "shadow")),
            stt_rollout_rollback_override_active=bool(
                snapshot.get("stt_rollout_rollback_override_active", False)
            ),
            stt_rollout_rollback_reason_code=(
                str(snapshot.get("stt_rollout_rollback_reason_code"))
                if snapshot.get("stt_rollout_rollback_reason_code") is not None
                else None
            ),
        )

    def _emit_config(self) -> None:
        snapshot = self._settings_snapshot()
        self.session.apply_settings(snapshot)
        self._provider_state.persisted_provider = snapshot.speech_provider
        self._provider_state.pending_provider = snapshot.pending_speech_provider
        self._provider_state.deferred_until_restart = snapshot.deferred_provider_switch
        stt_configuration: dict[str, Any] | None = None
        stt_provider_availability_state: dict[str, Any] | None = None
        if self._listener is not None:
            config_probe = getattr(self._listener, "recognition_configuration_snapshot", None)
            if callable(config_probe):
                try:
                    payload = config_probe()
                    if isinstance(payload, dict):
                        stt_configuration = dict(payload)
                except Exception:  # noqa: BLE001
                    stt_configuration = None
            availability_probe = getattr(self._listener, "provider_availability_state", None)
            if callable(availability_probe):
                try:
                    payload = availability_probe()
                    if isinstance(payload, dict):
                        stt_provider_availability_state = dict(payload)
                except Exception:  # noqa: BLE001
                    stt_provider_availability_state = None
        self._emit(
            config_event(
                self.session,
                snapshot,
                provider_state=self._provider_state,
                stt_configuration=stt_configuration,
                stt_provider_availability_state=stt_provider_availability_state,
            )
        )

    def _emit_system(self, text: str) -> None:
        self._emit(
            build_event(
                RuntimeEventType.SYSTEM,
                session_id=self.session.session_id,
                payload={"text": text},
            )
        )

    def _emit_assistant(self, text: str, *, priority: str = "info") -> None:
        concise_text = truncate_to_word_limit(text, word_limit=self._settings.concise_word_limit)
        message_key = concise_text.strip().lower()
        created_at_s = time.perf_counter()
        event = InteractionPriorityEvent(
            event_id=f"assistant-{self._session_sequence}",
            priority=priority if priority in {"warning", "action_confirmation", "error", "info"} else "info",
            message_text=concise_text,
            message_key=message_key,
            created_at_s=created_at_s,
            source="runtime",
            coalescing_group=message_key,
        )
        self._session_sequence += 1

        self._priority_buffer.append(event)
        prior_count = len(self._priority_buffer)
        coalesced_events = coalesce_priority_events(
            self._priority_buffer,
            coalescing_window_s=self._settings.priority_coalescing_window_s,
        )
        self._priority_buffer = coalesced_events
        emitted = any(item.event_id == event.event_id for item in coalesced_events)
        if not emitted:
            return
        was_coalesced = len(coalesced_events) < prior_count

        self._emit(
            build_event(
                RuntimeEventType.ASSISTANT,
                session_id=self.session.session_id,
                payload={
                    "text": event.message_text,
                    "priority": event.priority,
                    "coalesced": was_coalesced,
                    "coalescing_window_s": self._settings.priority_coalescing_window_s,
                },
            )
        )

    def _emit(self, event: RuntimeEvent) -> None:
        if event.type == RuntimeEventType.STATUS:
            logger.info(
                "[RUNTIME] event=status session=%s mode=%s state=%s",
                event.session_id,
                self.mode.value,
                event.payload.get("state"),
            )
        else:
            logger.info(
                "[RUNTIME] event=%s session=%s mode=%s payload=%s",
                event.type.value,
                event.session_id,
                self.mode.value,
                event.payload,
            )

        try:
            self.observer(event)
        except Exception:  # noqa: BLE001
            logger.exception("[RUNTIME] Observer callback failed")

    def _is_close_intent(self, text: str) -> bool:
        lowered = (text or "").lower()
        if not lowered:
            return False
        return any(word in lowered for word in _CLOSE_INTENT_WORDS)

    def _is_thanks_intent(self, text: str) -> bool:
        lowered = (text or "").lower()
        if not lowered:
            return False
        return any(word in lowered for word in _THANKS_INTENT_WORDS)

    def _is_yes(self, text: str) -> bool:
        return is_affirmative(text)

    def _parse_speed(self, text: str) -> float:
        lowered = (text or "").lower()
        match = re.search(r"(\d+(?:\.\d+)?)", lowered)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        if any(word in lowered for word in ("fast", "faster", "سريع", "اسرع", "أسرع")):
            return 1.35
        if any(word in lowered for word in ("slow", "slower", "بطيء", "ابطأ", "أبطأ")):
            return 0.85
        return self._settings.default_speech_speed

    def _normalize_onboarding_text(self, text: str) -> str:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return ""
        normalized = (
            normalized.replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ى", "ي")
            .replace("ة", "ه")
        )
        normalized = re.sub(r"[^\w\s\u0600-\u06FF]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _contains_phrase(self, normalized_text: str, phrase: str) -> bool:
        candidate = self._normalize_onboarding_text(phrase)
        if not normalized_text or not candidate:
            return False
        return f" {candidate} " in f" {normalized_text} "

    def _last_phrase_position(self, normalized_text: str, phrases: tuple[str, ...]) -> int:
        best = -1
        if not normalized_text:
            return best
        haystack = f" {normalized_text} "
        for phrase in phrases:
            candidate = self._normalize_onboarding_text(phrase)
            if not candidate:
                continue
            index = haystack.rfind(f" {candidate} ")
            if index > best:
                best = index
        return best

    def _parse_onboarding_language_choice(self, text: str) -> str | None:
        normalized = self._normalize_onboarding_text(text)
        if not normalized:
            return None
        closed_match = match_closed_vocabulary(
            utterance=normalized,
            vocabulary_id="onboarding.language_choice",
            minimum_similarity=0.8,
        )
        if closed_match is not None and closed_match.persisted_value in {"ar-EG", "en-US"}:
            return closed_match.persisted_value
        arabic_markers = (
            "arabic",
            "arab",
            "ar",
            "عربي",
            "عربيه",
            "عربى",
            "العربيه",
            "العربية",
            "اللغة العربيه",
        )
        english_markers = (
            "english",
            "eng",
            "en",
            "انجليزي",
            "انجليزى",
            "انجليزيه",
            "الانجليزيه",
            "الانجليزية",
            "انجلش",
        )
        has_arabic = any(self._contains_phrase(normalized, marker) for marker in arabic_markers)
        has_english = any(self._contains_phrase(normalized, marker) for marker in english_markers)
        if has_arabic and not has_english:
            return "ar-EG"
        if has_english and not has_arabic:
            return "en-US"
        if has_arabic and has_english:
            # Ambiguous language answers should force a clarification turn instead
            # of selecting one language arbitrarily.
            return None
        return None

    def _parse_onboarding_voice_choice(self, text: str) -> str | None:
        normalized = self._normalize_onboarding_text(text)
        if not normalized:
            return None
        compact = normalized.replace(" ", "")
        if compact in {"female", "femail", "femal", "فيميل", "فيمايل", "فيمال"}:
            return "female"
        if compact in {"male", "mail", "ميل", "مايل"}:
            return "male"
        female_markers = (
            "female",
            "femail",
            "femal",
            "في ميل",
            "فيمايل",
            "she",
            "her",
            "woman",
            "girl",
            "هي",
            "انثي",
            "انثى",
            "بنت",
            "ست",
            "فيميل",
            "انثه",
        )
        male_markers = (
            "male",
            "mail",
            "mel",
            "he",
            "his",
            "him",
            "man",
            "boy",
            "هو",
            "ذكر",
            "راجل",
            "ولد",
            "ميل",
            "مايل",
            "مي",
            "مين",
            "ميله",
        )
        has_female = any(self._contains_phrase(normalized, marker) for marker in female_markers)
        has_male = any(self._contains_phrase(normalized, marker) for marker in male_markers)
        if has_female and not has_male:
            return "female"
        if has_male and not has_female:
            return "male"
        if has_female and has_male:
            female_pos = self._last_phrase_position(normalized, female_markers)
            male_pos = self._last_phrase_position(normalized, male_markers)
            return "female" if female_pos >= male_pos else "male"
        return None

    def _parse_onboarding_speed_choice(self, text: str) -> float | None:
        raw = str(text or "").strip().lower()
        normalized = self._normalize_onboarding_text(text)
        if not raw or not normalized:
            return None
        closed_match = match_closed_vocabulary(
            utterance=normalized,
            vocabulary_id="onboarding.speed_choice",
            minimum_similarity=0.78,
        )
        if closed_match is not None:
            try:
                return float(closed_match.persisted_value)
            except (TypeError, ValueError):
                return self._settings.default_speech_speed
        match = re.search(r"(\d+(?:[.,]\d+)?)", raw)
        if match:
            try:
                parsed = float(match.group(1).replace(",", "."))
            except ValueError:
                parsed = self._settings.default_speech_speed
            minimum = float(getattr(self._settings, "min_speech_speed", 0.7))
            maximum = float(getattr(self._settings, "max_speech_speed", 1.5))
            return max(minimum, min(maximum, parsed))
        if any(
            self._contains_phrase(normalized, marker)
            for marker in ("fast", "faster", "سريع", "اسرع", "أسرع")
        ):
            return 1.35
        if any(
            self._contains_phrase(normalized, marker)
            for marker in ("slow", "slower", "بطيء", "ابطأ", "أبطأ")
        ):
            return 0.85
        if any(
            self._contains_phrase(normalized, marker)
            for marker in ("normal", "norman", "regular", "default", "عادي", "طبيعي", "نورمال")
        ):
            return self._settings.default_speech_speed
        return None

    def _is_onboarding_noise_response(self, text: str) -> bool:
        normalized = self._normalize_onboarding_text(text)
        if not normalized:
            return True
        if detect_wake(normalized).accepted:
            return True
        return any(
            self._contains_phrase(normalized, token)
            for token in ("hi", "hello", "hey", "هاي", "هلا", "اهلا", "mm", "umm", "امم")
        )

    def _is_prompt_echo_response(self, response_text: str, prompt_text: str) -> bool:
        normalized_response = self._normalize_onboarding_text(response_text)
        normalized_prompt = self._normalize_onboarding_text(prompt_text)
        if not normalized_response or not normalized_prompt:
            return False
        response_tokens = [token for token in normalized_response.split() if token]
        prompt_scaffold_tokens = {
            "choose",
            "say",
            "prefer",
            "voice",
            "language",
            "speed",
            "name",
            "confirm",
            "اختر",
            "قل",
            "تفضل",
            "صوت",
            "سرعه",
            "اسمك",
            "هل",
            "نوع",
        }
        if len(response_tokens) <= 2:
            if any(token in prompt_scaffold_tokens for token in response_tokens):
                return True
            return False
        if normalized_response == normalized_prompt:
            return True
        if self._contains_phrase(normalized_prompt, normalized_response):
            # Most common self-capture case: recognizer transcribes question text.
            return True
        prompt_tokens = {token for token in normalized_prompt.split() if token}
        overlap = sum(1 for token in response_tokens if token in prompt_tokens)
        overlap_ratio = overlap / max(1, len(response_tokens))
        if overlap_ratio >= 0.75:
            return True
        scaffold_hits = sum(1 for token in response_tokens if token in prompt_scaffold_tokens)
        if len(response_tokens) >= 4 and scaffold_hits >= 1 and overlap_ratio >= 0.55:
            return True
        return False

    def _resolve_onboarding_prompt_echo(
        self,
        *,
        answer: str | None,
        prompt_text: str,
        languages: list[str],
        prompt: str,
        timeout: int,
        phrase_time_limit: int,
        accept_answer: Callable[[str], bool] | None = None,
    ) -> str | None:
        if not answer:
            return answer
        accepted_answer = False
        if callable(accept_answer):
            try:
                accepted_answer = bool(accept_answer(answer))
            except Exception:  # noqa: BLE001
                logger.debug("[SETUP] accept_answer callback failed", exc_info=True)
        if accepted_answer and len(self._normalize_onboarding_text(answer).split()) <= 2:
            return answer
        if not self._is_prompt_echo_response(answer, prompt_text):
            return answer
        logger.info("[SETUP] Ignoring prompt-echo response: %s", answer)
        self._emit_guided_dialog_outcome(
            status="prompt_echo_suppressed",
            spoken_text=prompt_text,
            error_code="prompt_echo_suppressed",
            next_runtime_state=RuntimeState.LISTENING.value,
            closed_vocabulary_id=None,
            retry_count=self._confidence_retry_cycles,
            retry_limit=self._settings.closed_vocabulary_retry_limit,
            prompt_echo_suppressed=True,
        )
        followup_timeout = max(2, min(5, int(timeout)))
        followup_phrase_limit = max(2, min(5, int(phrase_time_limit)))
        return self._listen_any_with_interrupt(
            languages,
            prompt=f"{prompt} (follow-up)",
            timeout=followup_timeout,
            phrase_time_limit=followup_phrase_limit,
        )

    def _is_plausible_username(self, text: str) -> bool:
        cleaned = self._normalize_onboarding_text(text)
        if not cleaned:
            return False
        if self._is_onboarding_noise_response(cleaned):
            return False
        if len(cleaned) < 2:
            return False
        tokens = [token for token in cleaned.split() if token]
        if not tokens or len(tokens) > 2:
            return False
        low_signal_tokens = {
            "what",
            "with",
            "that",
            "this",
            "there",
            "they",
            "have",
            "your",
            "name",
            "is",
            "the",
            "and",
            "or",
            "هل",
            "اسمك",
            "قل",
            "اختر",
            "نوع",
            "صوت",
        }
        if any(token in low_signal_tokens for token in tokens):
            return False
        if max((len(token) for token in tokens), default=0) < 3:
            return False
        if any(char.isdigit() for char in cleaned):
            return False
        return True

    def _listen_any_with_interrupt(
        self,
        languages: list[str],
        *,
        prompt: str,
        timeout: int,
        phrase_time_limit: int,
    ) -> str | None:
        listen_any = getattr(self._listener, "listen_any", None)
        if not callable(listen_any):
            return None
        try:
            return listen_any(
                languages,
                prompt=prompt,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
                interrupt_event=self._interrupt_event,
            )
        except TypeError:
            try:
                return listen_any(
                    languages,
                    prompt=prompt,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            except TypeError:
                return listen_any(languages)

    def _announce_and_listen_with_barge_in(
        self,
        surface_id: str,
        languages: list[str],
        *,
        prompt: str,
        timeout: int,
        phrase_time_limit: int,
        format_kwargs: dict[str, Any] | None = None,
        allow_barge_in: bool | None = None,
    ) -> tuple[str | None, str]:
        if self._stop_event.is_set():
            return None, ""

        turn_window = build_turn_window(prompt_surface_id=surface_id)
        effective_barge_in_allowed = (
            turn_window.barge_in_allowed if allow_barge_in is None else bool(allow_barge_in)
        )
        listening_status = listening_status_for_window(turn_window)

        spoken_prompt_text = ""
        if not effective_barge_in_allowed:
            resolved = self._announce_runtime_critical_prompt(surface_id, format_kwargs=format_kwargs)
            spoken_prompt_text = str(resolved.get("text", "") or "").strip()
            self._emit_turn_taking_window_outcome(
                status="speaking_only",
                spoken_text=spoken_prompt_text,
                error_code=None,
                next_runtime_state=RuntimeState.SPEAKING.value,
                prompt_surface_id=surface_id,
                prompt_class=turn_window.prompt_class,
                barge_in_allowed=False,
                closed_vocabulary_id=turn_window.closed_vocabulary_id,
                retry_count=turn_window.retry_count,
                global_safety_only_preemption=turn_window.global_safety_only_preemption,
            )
            answer = self._listen_any_with_interrupt(
                languages,
                prompt=prompt,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
            self._emit_turn_taking_window_outcome(
                status=listening_status,
                spoken_text=spoken_prompt_text,
                error_code=None,
                next_runtime_state=RuntimeState.LISTENING.value,
                prompt_surface_id=surface_id,
                prompt_class=turn_window.prompt_class,
                barge_in_allowed=effective_barge_in_allowed,
                closed_vocabulary_id=turn_window.closed_vocabulary_id,
                retry_count=turn_window.retry_count,
                global_safety_only_preemption=turn_window.global_safety_only_preemption,
            )
            return answer, spoken_prompt_text

        def _announce_prompt() -> None:
            nonlocal spoken_prompt_text
            try:
                resolved = self._announce_runtime_critical_prompt(surface_id, format_kwargs=format_kwargs)
                spoken_prompt_text = str(resolved.get("text", "") or "").strip()
            except Exception:  # noqa: BLE001
                logger.exception("[RUNTIME] Failed to announce onboarding prompt: %s", surface_id)

        announce_worker = threading.Thread(
            target=_announce_prompt,
            name=f"RuntimePrompt-{surface_id}",
            daemon=True,
        )
        announce_worker.start()
        self._emit_turn_taking_window_outcome(
            status=turn_window.status,
            spoken_text=spoken_prompt_text,
            error_code=None,
            next_runtime_state=RuntimeState.SPEAKING.value,
            prompt_surface_id=surface_id,
            prompt_class=turn_window.prompt_class,
            barge_in_allowed=True,
            closed_vocabulary_id=turn_window.closed_vocabulary_id,
            retry_count=turn_window.retry_count,
            global_safety_only_preemption=turn_window.global_safety_only_preemption,
        )

        # Small lead-in reduces self-capture while still allowing barge-in.
        time.sleep(0.24)
        answer = self._listen_any_with_interrupt(
            languages,
            prompt=prompt,
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
        )

        request_stop = getattr(self._tts_engine, "request_stop", None)
        if callable(request_stop) and (answer or announce_worker.is_alive()):
            try:
                request_stop()
            except Exception:  # noqa: BLE001
                logger.exception("[RUNTIME] Failed to stop prompt speech during barge-in")

        if announce_worker.is_alive():
            announce_worker.join(timeout=0.3)
        self._emit_turn_taking_window_outcome(
            status=listening_status,
            spoken_text=spoken_prompt_text,
            error_code=None,
            next_runtime_state=RuntimeState.LISTENING.value,
            prompt_surface_id=surface_id,
            prompt_class=turn_window.prompt_class,
            barge_in_allowed=True,
            closed_vocabulary_id=turn_window.closed_vocabulary_id,
            retry_count=turn_window.retry_count,
            global_safety_only_preemption=turn_window.global_safety_only_preemption,
        )
        return answer, spoken_prompt_text

    def _announce_runtime_critical_prompt(
        self,
        surface_id: str,
        *,
        format_kwargs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_runtime_critical_prompt(surface_id, format_kwargs=format_kwargs)
        text = str(resolved.get("text", "") or "").strip()
        if text:
            self._emit_system(text)
        return resolved

    def _infer_session_language(self, text: str) -> str | None:
        normalized = self._normalize_onboarding_text(text)
        if not normalized:
            return None
        explicit_language = self._parse_onboarding_language_choice(normalized)
        return explicit_language


