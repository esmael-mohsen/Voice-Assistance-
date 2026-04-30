"""Shared command models for parser, resolver, dispatcher, and runtime contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PRIORITY_ORDER: dict[str, int] = {
    "warning": 0,
    "action_confirmation": 1,
    "error": 2,
    "info": 3,
}
VALID_PRIORITIES: frozenset[str] = frozenset(PRIORITY_ORDER.keys())
RECOGNITION_PATHS: frozenset[str] = frozenset({"local_first", "rescue", "fallback"})
CONFIDENCE_BANDS: frozenset[str] = frozenset({"high", "medium", "low", "missing_confidence"})
DECISION_ACTIONS: frozenset[str] = frozenset({"execute", "fallback", "confirm", "retry", "defer", "refuse"})
CAPTURE_USAGE_MODES: frozenset[str] = frozenset({"standby_wake", "onboarding", "command", "confirmation"})
DICTIONARY_BIAS_MODES: frozenset[str] = frozenset({"none", "command_inventory", "closed_choice"})
RECOGNITION_SOURCE_LABELS: frozenset[str] = frozenset(
    {
        "cloud_primary",
        "strict_vosk_fallback",
        "wake_strict_vosk_fallback",
        "rescue_strict_vosk",
        "cloud_unavailable",
        "noncanonical_rejected",
        "keyword_low_power",
        "hardware_trigger",
        "local_vosk",
        "sphinx_compat",
        "legacy_local",
    }
)
CLOUD_FAILURE_REASON_CODES: frozenset[str] = frozenset(
    {
        "cloud_credentials_missing",
        "cloud_network_timeout",
        "cloud_auth_error",
        "cloud_quota_error",
        "cloud_service_unavailable",
        "cloud_empty_result",
        "cloud_unknown_failure",
    }
)
STRICT_FALLBACK_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "strict_grammar_no_match",
        "strict_vosk_unavailable",
        "strict_vosk_failed",
    }
)
STT_CONFIG_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "cloud_primary_enabled",
    "strict_vosk_fallback_enabled",
    "sphinx_compat_enabled",
    "cloud_timeout_s",
    "cloud_max_alternatives",
    "selected_profile_language",
    "configured_from_environment",
    "field_safe",
    "credential_material_present",
)
QUALIFICATION_PROFILE_LABELS: frozenset[str] = frozenset({"default", "simplified"})
QUALIFICATION_STATUSES: frozenset[str] = frozenset({"candidate", "qualified", "demoted"})
WAKE_RELIABILITY_STATUSES: frozenset[str] = frozenset(
    {"wake_accepted", "wake_rejected", "wake_missed", "confirmation_required", "degraded_standby"}
)
SPEECH_LOOP_RECOVERY_STATUSES: frozenset[str] = frozenset(
    {"retry_allowed", "recovered_to_standby", "degraded_recovery"}
)
TURN_TAKING_WINDOW_STATUSES: frozenset[str] = frozenset(
    {
        "speaking_only",
        "speaking_with_barge_in",
        "listening",
        "closed_vocabulary_listening",
        "waiting_confirmation",
        "recovering",
    }
)
GUIDED_DIALOG_STATUSES: frozenset[str] = frozenset(
    {
        "accepted",
        "retry_required",
        "prompt_echo_suppressed",
        "rejected",
        "safe_default_applied",
        "graceful_exit",
    }
)
NAME_CANDIDATE_STATUSES: frozenset[str] = frozenset({"pending", "accepted", "rejected", "discarded"})
PILOT_COMPLETION_STATUSES: frozenset[str] = frozenset(
    {"completed", "safe_default_continuation", "graceful_exit", "failed"}
)


def normalize_failure_reason_code(reason_code: str | None) -> str | None:
    cleaned = str(reason_code or "").strip().lower()
    if not cleaned:
        return None
    if cleaned in CLOUD_FAILURE_REASON_CODES or cleaned in STRICT_FALLBACK_FAILURE_CODES:
        return cleaned
    return None


def latency_category(latency_ms: int) -> str:
    value = max(0, int(latency_ms))
    if value < 500:
        return "fast"
    if value < 1500:
        return "normal"
    if value < 3000:
        return "slow"
    return "timeout_bound"


def build_stt_configuration_snapshot(
    *,
    cloud_primary_enabled: bool,
    strict_vosk_fallback_enabled: bool,
    sphinx_compat_enabled: bool,
    cloud_timeout_s: float,
    cloud_max_alternatives: int,
    selected_profile_language: str,
    configured_from_environment: bool = True,
) -> dict[str, Any]:
    timeout_value = float(cloud_timeout_s)
    alternatives_value = int(cloud_max_alternatives)
    if timeout_value <= 0:
        timeout_value = 3.0
    if alternatives_value < 1:
        alternatives_value = 1
    return {
        "cloud_primary_enabled": bool(cloud_primary_enabled),
        "strict_vosk_fallback_enabled": bool(strict_vosk_fallback_enabled),
        "sphinx_compat_enabled": bool(sphinx_compat_enabled),
        "cloud_timeout_s": timeout_value,
        "cloud_max_alternatives": alternatives_value,
        "selected_profile_language": str(selected_profile_language or "en-US"),
        "configured_from_environment": bool(configured_from_environment),
        "field_safe": True,
        "credential_material_present": False,
    }


def build_command_fallback_decision(
    *,
    status_or_decision: str,
    trigger: str,
    recognition_source: str,
    fallback_enabled: bool,
    fallback_attempted: bool,
    fallback_mode: str | None,
    reason_code: str | None,
    confidence_band: str,
    selected_language: str | None,
    detected_language: str | None,
    latency_ms: int,
) -> dict[str, Any]:
    normalized_source = str(recognition_source or "").strip().lower()
    if normalized_source and normalized_source not in RECOGNITION_SOURCE_LABELS:
        normalized_source = "legacy_local"
    band = str(confidence_band or "").strip().lower()
    if band not in CONFIDENCE_BANDS:
        band = "missing_confidence"
    return {
        "status_or_decision": str(status_or_decision or "").strip().lower(),
        "trigger": str(trigger or "").strip().lower(),
        "recognition_source": normalized_source or "legacy_local",
        "fallback_enabled": bool(fallback_enabled),
        "fallback_attempted": bool(fallback_attempted),
        "fallback_mode": str(fallback_mode or "").strip().lower() or None,
        "reason_code": normalize_failure_reason_code(reason_code) or str(reason_code or "").strip().lower() or None,
        "confidence_band": band,
        "selected_language": str(selected_language or "").strip() or None,
        "detected_language": str(detected_language or "").strip() or None,
        "latency_ms": max(0, int(latency_ms)),
        "field_safe": True,
        "raw_user_content_present": False,
    }


@dataclass(frozen=True)
class CommandCatalogEntry:
    intent_id: str
    category: str
    risk_level: str
    keywords: tuple[str, ...]
    base_threshold: float
    ambiguity_margin: float
    requires_parameters: bool = False
    requires_confirmation: bool = False
    follow_up_source: bool = False
    follow_up_target: str | None = None
    route_target: str = "controller"


@dataclass(frozen=True)
class ParsedCommandIntent:
    raw_text: str
    normalized_text: str
    intent_id: str | None
    category: str | None
    risk_level: str | None
    matched_keyword: str | None
    score: float
    threshold: float
    runner_up_intent: str | None = None
    runner_up_score: float | None = None
    accepted: bool = False
    rejection_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandResolution:
    intent_id: str | None
    category: str | None
    route_target: str | None
    validation_status: str
    params: dict[str, Any] = field(default_factory=dict)
    used_session_context: bool = False
    session_context_updates: dict[str, Any] = field(default_factory=dict)
    spoken_text: str = ""
    error_code: str | None = None
    controller_result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandExecutionResult:
    status: str
    spoken_text: str
    intent_id: str | None = None
    category: str | None = None
    payload: dict[str, Any] | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioCaptureProfile:
    profile_id: str
    usage_mode: str
    sample_rate_hz: int = 16_000
    mono_required: bool = True
    high_pass_hz: int = 120
    target_loudness_dbfs: float = -20.0
    vad_enabled: bool = True
    pre_roll_ms: int = 180
    post_roll_ms: int = 220
    trailing_silence_ms: int = 650
    max_utterance_ms: int = 8_000
    allow_noise_suppression: bool = False
    dictionary_bias_mode: str = "command_inventory"
    closed_vocabulary_id: str | None = None

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id is required")
        if self.usage_mode not in CAPTURE_USAGE_MODES:
            raise ValueError("usage_mode must be standby_wake, onboarding, command, or confirmation")
        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        for field_name in ("pre_roll_ms", "post_roll_ms", "trailing_silence_ms"):
            value = int(getattr(self, field_name))
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.max_utterance_ms <= 0:
            raise ValueError("max_utterance_ms must be positive")
        if self.dictionary_bias_mode not in DICTIONARY_BIAS_MODES:
            raise ValueError("dictionary_bias_mode must be none, command_inventory, or closed_choice")
        if self.dictionary_bias_mode == "closed_choice" and not self.closed_vocabulary_id:
            raise ValueError("closed_vocabulary_id is required when dictionary_bias_mode is closed_choice")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioCaptureAttempt:
    capture_attempt_id: str
    session_id: str
    profile_id: str
    attempt_index: int
    started_at_ms: int
    ended_at_ms: int
    raw_duration_ms: int
    processed_duration_ms: int
    speech_started_at_ms: int | None = None
    speech_ended_at_ms: int | None = None
    utterance_duration_ms: int = 0
    clipping_start_suspected: bool = False
    clipping_end_suspected: bool = False
    endpoint_quality_hints: tuple[str, ...] = ()
    relisten_triggered: bool = False
    recovery_prompt_surface: str | None = None

    def __post_init__(self) -> None:
        if not self.capture_attempt_id:
            raise ValueError("capture_attempt_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.profile_id:
            raise ValueError("profile_id is required")
        if self.attempt_index < 0 or self.attempt_index > 1:
            raise ValueError("attempt_index must be between 0 and 1 in this phase")
        if self.ended_at_ms < self.started_at_ms:
            raise ValueError("ended_at_ms must be >= started_at_ms")
        if self.raw_duration_ms < 0 or self.processed_duration_ms < 0:
            raise ValueError("capture durations must be non-negative")
        if self.utterance_duration_ms < 0:
            raise ValueError("utterance_duration_ms must be non-negative")
        if self.relisten_triggered and not (
            self.clipping_start_suspected or self.clipping_end_suspected or self.endpoint_quality_hints
        ):
            raise ValueError("relisten_triggered requires clipping flags or endpoint_quality_hints")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HybridRecognitionResult:
    session_id: str
    capture_attempt_id: str
    recognition_path: str
    provider_id: str
    profile_id: str
    primary_transcript: str
    alternative_transcripts: tuple[str, ...] = ()
    confidence_score: float | None = None
    confidence_available: bool = False
    detected_language: str | None = None
    language_candidates: tuple[str, ...] = ()
    latency_ms: int = 0
    dictionary_bias_applied: bool = False
    closed_vocabulary_id: str | None = None
    endpoint_quality_hints: tuple[str, ...] = ()
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.capture_attempt_id:
            raise ValueError("capture_attempt_id is required")
        if self.recognition_path not in RECOGNITION_PATHS:
            raise ValueError("recognition_path must be local_first, rescue, or fallback")
        if not self.provider_id:
            raise ValueError("provider_id is required")
        if not self.profile_id:
            raise ValueError("profile_id is required")
        if self.error_code is None and not self.primary_transcript.strip():
            raise ValueError("primary_transcript is required for successful recognition")
        if not self.confidence_available and self.confidence_score is not None:
            raise ValueError("confidence_score must be None when confidence_available is False")
        if self.confidence_available and self.confidence_score is not None:
            if self.confidence_score < 0 or self.confidence_score > 1:
                raise ValueError("confidence_score must be between 0 and 1")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.dictionary_bias_applied and not self.profile_id:
            raise ValueError("dictionary_bias_applied requires profile_id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpeechQualificationProfile:
    qualification_profile_id: str
    profile_label: str
    enable_noise_suppression: bool
    enable_rescue_recognition: bool
    enable_dictionary_bias: bool
    enable_capture_relisten: bool
    qualification_status: str = "candidate"
    demotion_reason: str | None = None
    evidence_bundle_id: str | None = None

    def __post_init__(self) -> None:
        if not self.qualification_profile_id:
            raise ValueError("qualification_profile_id is required")
        if self.profile_label not in QUALIFICATION_PROFILE_LABELS:
            raise ValueError("profile_label must be default or simplified")
        if self.qualification_status not in QUALIFICATION_STATUSES:
            raise ValueError("qualification_status must be candidate, qualified, or demoted")
        if self.qualification_status == "demoted" and not str(self.demotion_reason or "").strip():
            raise ValueError("demotion_reason is required when qualification_status is demoted")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandRecognitionResult:
    session_id: str
    recognition_path: str
    provider_id: str
    primary_transcript: str
    confidence_score: float | None = None
    confidence_available: bool = False
    alternative_transcripts: tuple[str, ...] = ()
    detected_language: str | None = None
    language_candidates: tuple[str, ...] = ()
    capture_attempt_id: str | None = None
    profile_id: str | None = None
    dictionary_bias_applied: bool = False
    dictionary_bias_mode: str | None = None
    closed_vocabulary_id: str | None = None
    endpoint_quality_hints: tuple[str, ...] = ()
    capture_attempt: AudioCaptureAttempt | None = None
    qualification_profile_id: str | None = None
    latency_ms: int = 0
    error_code: str | None = None
    recognition_source: str | None = None
    failure_reason_code: str | None = None
    selected_language: str | None = None
    profile_mutation_allowed: bool = False
    field_safe: bool = True
    raw_user_content_present: bool = False

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.recognition_path not in RECOGNITION_PATHS:
            raise ValueError("recognition_path must be local_first, rescue, or fallback")
        if not self.provider_id:
            raise ValueError("provider_id is required")
        if self.error_code is None and not self.primary_transcript.strip():
            raise ValueError("primary_transcript is required for successful recognition")
        if not self.confidence_available and self.confidence_score is not None:
            raise ValueError("confidence_score must be None when confidence_available is False")
        if self.confidence_available and self.confidence_score is not None:
            if self.confidence_score < 0 or self.confidence_score > 1:
                raise ValueError("confidence_score must be between 0 and 1")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.dictionary_bias_mode is not None and self.dictionary_bias_mode not in DICTIONARY_BIAS_MODES:
            raise ValueError("dictionary_bias_mode must be none, command_inventory, or closed_choice")
        if self.dictionary_bias_mode == "closed_choice" and not self.closed_vocabulary_id:
            raise ValueError("closed_vocabulary_id is required for closed_choice recognition")
        if self.dictionary_bias_applied and not self.profile_id:
            raise ValueError("profile_id is required when dictionary_bias_applied is True")
        if self.capture_attempt is not None:
            if self.capture_attempt_id is None:
                object.__setattr__(self, "capture_attempt_id", self.capture_attempt.capture_attempt_id)
            if self.profile_id is None:
                object.__setattr__(self, "profile_id", self.capture_attempt.profile_id)
            if not self.endpoint_quality_hints:
                object.__setattr__(self, "endpoint_quality_hints", self.capture_attempt.endpoint_quality_hints)
        if self.closed_vocabulary_id and not self.dictionary_bias_applied:
            object.__setattr__(self, "dictionary_bias_applied", True)
        if self.detected_language and self.detected_language not in self.language_candidates:
            object.__setattr__(
                self,
                "language_candidates",
                tuple((self.detected_language, *tuple(self.language_candidates))),
            )
        if self.selected_language and self.selected_language not in self.language_candidates:
            object.__setattr__(
                self,
                "language_candidates",
                tuple((self.selected_language, *tuple(self.language_candidates))),
            )
        if self.recognition_source is not None:
            source = str(self.recognition_source).strip().lower()
            if source and source not in RECOGNITION_SOURCE_LABELS:
                raise ValueError(f"Unsupported recognition_source: {self.recognition_source}")
            object.__setattr__(self, "recognition_source", source or None)
        normalized_failure = normalize_failure_reason_code(self.failure_reason_code)
        if self.failure_reason_code is not None and normalized_failure is None:
            raise ValueError(f"Unsupported failure_reason_code: {self.failure_reason_code}")
        object.__setattr__(self, "failure_reason_code", normalized_failure)
        if self.field_safe and self.raw_user_content_present:
            raise ValueError("field_safe recognition result must not include raw user content")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandPostProcessingOutcome:
    source_transcript: str
    normalized_transcript: str
    canonical_command_text: str
    substitution_ids: tuple[str, ...] = ()
    language_hints: tuple[str, ...] = ()
    dictionary_mode: str = "command_inventory"
    closed_vocabulary_id: str | None = None
    confusion_pair_id: str | None = None
    ambiguity_flags: tuple[str, ...] = ()
    post_processing_status: str = "unchanged"

    def __post_init__(self) -> None:
        if self.dictionary_mode not in DICTIONARY_BIAS_MODES:
            raise ValueError("dictionary_mode must be none, command_inventory, or closed_choice")
        if self.dictionary_mode == "closed_choice" and not self.closed_vocabulary_id:
            raise ValueError("closed_vocabulary_id is required when dictionary_mode is closed_choice")
        if self.post_processing_status not in {"normalized", "unchanged", "rejected", "constrained_retry"}:
            raise ValueError(
                "post_processing_status must be normalized, unchanged, constrained_retry, or rejected"
            )
        if self.post_processing_status in {"normalized", "unchanged"}:
            if not self.normalized_transcript.strip():
                raise ValueError("normalized_transcript is required when outcome is usable")
            if not self.canonical_command_text.strip():
                raise ValueError("canonical_command_text is required when outcome is usable")
        if self.post_processing_status == "constrained_retry" and self.dictionary_mode != "closed_choice":
            raise ValueError("constrained_retry is only valid in closed_choice mode")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["canonicalization_status"] = self.post_processing_status
        return payload

    @property
    def canonicalization_status(self) -> str:
        return self.post_processing_status


@dataclass(frozen=True)
class ConfidenceDecisionPolicy:
    high_confidence_threshold: float = 0.82
    medium_confidence_threshold: float = 0.55
    protected_command_threshold: float = 0.9
    allow_missing_confidence_for_unprotected: bool = True
    max_retry_cycles: int = 1
    fallback_enabled: bool = True
    offline_local_allowed: bool = True

    def __post_init__(self) -> None:
        if self.high_confidence_threshold < self.medium_confidence_threshold:
            raise ValueError("high_confidence_threshold must be >= medium_confidence_threshold")
        if self.protected_command_threshold < self.high_confidence_threshold:
            raise ValueError("protected_command_threshold must be >= high_confidence_threshold")
        if self.max_retry_cycles < 0:
            raise ValueError("max_retry_cycles must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def rescue_enabled(self) -> bool:
        """Phase 14 alias: rescue recognition maps to the legacy fallback flag."""
        return self.fallback_enabled


@dataclass(frozen=True)
class RecognitionTelemetrySample:
    session_id: str
    event_id: str
    recognition_path: str
    confidence_band: str
    fallback_used: bool
    decision_outcome: str
    protected_command: bool
    latency_ms: int
    profile_id: str | None = None
    closed_vocabulary_id: str | None = None
    qualification_profile_id: str | None = None
    field_safe: bool = True
    raw_utterance_present: bool = False

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.event_id:
            raise ValueError("event_id is required")
        if self.recognition_path not in RECOGNITION_PATHS:
            raise ValueError("recognition_path must be local_first, rescue, or fallback")
        if self.confidence_band not in CONFIDENCE_BANDS:
            raise ValueError("confidence_band must be a supported band")
        if self.decision_outcome not in DECISION_ACTIONS:
            raise ValueError("decision_outcome must be a supported action")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.field_safe and self.raw_utterance_present:
            raise ValueError("field_safe telemetry must not include raw utterances")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceDecisionOutcome:
    intent_id: str | None
    decision_band: str
    decision_action: str
    protected_command: bool
    fallback_attempted: bool
    confirmation_required: bool
    retry_count: int
    spoken_guidance_surface: str
    reason_code: str
    telemetry: RecognitionTelemetrySample

    def __post_init__(self) -> None:
        if self.decision_band not in CONFIDENCE_BANDS:
            raise ValueError("decision_band must be high, medium, low, or missing_confidence")
        if self.decision_action not in DECISION_ACTIONS:
            raise ValueError("decision_action must be supported")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TurnTakingWindowOutcome:
    trigger: str
    status: str
    spoken_text: str
    error_code: str | None
    next_runtime_state: str
    prompt_surface_id: str
    prompt_class: str
    barge_in_allowed: bool
    closed_vocabulary_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trigger != "turn_taking":
            raise ValueError("trigger must be turn_taking")
        if self.status not in TURN_TAKING_WINDOW_STATUSES:
            raise ValueError("status must be a supported turn-taking state")
        if not self.prompt_surface_id:
            raise ValueError("prompt_surface_id is required")
        if not self.prompt_class:
            raise ValueError("prompt_class is required")
        if self.status == "closed_vocabulary_listening" and not self.closed_vocabulary_id:
            raise ValueError("closed_vocabulary_id is required for closed_vocabulary_listening")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GuidedDialogOutcome:
    trigger: str
    status: str
    spoken_text: str
    error_code: str | None
    next_runtime_state: str
    closed_vocabulary_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trigger != "guided_dialog":
            raise ValueError("trigger must be guided_dialog")
        if self.status not in GUIDED_DIALOG_STATUSES:
            raise ValueError("status must be a supported guided dialog status")
        if self.status == "accepted" and not self.payload.get("accepted_option_id"):
            raise ValueError("accepted status requires payload.accepted_option_id")
        if self.status == "graceful_exit" and not self.payload.get("fallback_or_exit_reason"):
            raise ValueError("graceful_exit requires payload.fallback_or_exit_reason")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NameCandidate:
    candidate_id: str
    session_id: str
    normalized_candidate_text: str
    capture_quality: str
    confirmation_status: str = "pending"
    confirmed_at_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.confirmation_status not in NAME_CANDIDATE_STATUSES:
            raise ValueError("confirmation_status must be pending, accepted, rejected, or discarded")
        if self.confirmation_status == "accepted" and self.confirmed_at_ms is None:
            raise ValueError("accepted name candidate requires confirmed_at_ms")
        if self.confirmed_at_ms is not None and self.confirmed_at_ms < 0:
            raise ValueError("confirmed_at_ms must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotVoiceUXEvaluationRun:
    run_id: str
    scenario_label: str
    journey_type: str
    completion_status: str
    retries_used: int
    accepted_barge_in_count: int
    prompt_echo_suppression_count: int
    out_of_domain_rejection_count: int
    fallback_or_exit_reason: str | None
    raw_utterance_present: bool
    artifact_path: str

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.scenario_label:
            raise ValueError("scenario_label is required")
        if self.completion_status not in PILOT_COMPLETION_STATUSES:
            raise ValueError("completion_status must be supported")
        if self.retries_used < 0:
            raise ValueError("retries_used must be non-negative")
        if self.accepted_barge_in_count < 0:
            raise ValueError("accepted_barge_in_count must be non-negative")
        if self.prompt_echo_suppression_count < 0:
            raise ValueError("prompt_echo_suppression_count must be non-negative")
        if self.out_of_domain_rejection_count < 0:
            raise ValueError("out_of_domain_rejection_count must be non-negative")
        if self.raw_utterance_present:
            raise ValueError("raw_utterance_present must be false for field-safe evidence")
        if self.completion_status != "completed" and not str(self.fallback_or_exit_reason or "").strip():
            raise ValueError("non-completed runs require fallback_or_exit_reason")
        if not self.artifact_path:
            raise ValueError("artifact_path is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConnectivityStateSnapshot:
    override_mode: str
    detected_status: str
    effective_network_available: bool
    last_confirmed_status: str
    last_confirmed_at: float | None = None
    grace_window_active: bool = False
    grace_window_deadline_at: float | None = None
    probe_generation: int = 0
    startup_reset_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePolicyEvidence:
    flow: str
    capability_id: str | None
    provider_id: str
    override_mode: str
    detected_status: str
    effective_network_available: bool
    provider_availability: str
    requires_network: bool
    offline_allowlisted: bool
    decision: str
    error_code: str | None
    spoken_surface_id: str | None = None
    spoken_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionCommandContext:
    last_face_id: str | None = None
    follow_up_source_intent: str | None = None
    follow_up_target_intent: str | None = None
    remaining_follow_ups: int = 0
    pending_confirmation_intent: str | None = None
    pending_confirmation_payload: dict[str, Any] | None = None
    pending_confirmation_attempts: int = 0
    pending_clarification_intent: str | None = None
    clarification_attempts: int = 0
    clarification_max_attempts: int = 3

    def clear_follow_up(self) -> None:
        self.follow_up_source_intent = None
        self.follow_up_target_intent = None
        self.remaining_follow_ups = 0

    def clear_confirmation(self) -> None:
        self.pending_confirmation_intent = None
        self.pending_confirmation_payload = None
        self.pending_confirmation_attempts = 0

    def clear_clarification(self) -> None:
        self.pending_clarification_intent = None
        self.clarification_attempts = 0


@dataclass(frozen=True)
class InteractionPriorityEvent:
    event_id: str
    priority: str
    message_text: str
    message_key: str
    created_at_s: float
    source: str
    coalescing_group: str | None = None
    requires_immediate_delivery: bool = False
    expires_at_s: float | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"Unsupported priority '{self.priority}'")
        if not self.message_text.strip():
            raise ValueError("message_text is required")
        if not self.message_key:
            raise ValueError("message_key is required")

    def sort_key(self) -> tuple[int, float]:
        return (PRIORITY_ORDER[self.priority], self.created_at_s)


@dataclass(frozen=True)
class SpeechSessionWindow:
    session_window_id: str
    mode: str
    started_at_s: float
    max_duration_s: float
    interrupted: bool = False
    interrupt_reason: str = "none"
    completion_status: str = "success"
    ended_at_s: float | None = None
    output_event_id: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"listening", "speaking"}:
            raise ValueError("mode must be listening or speaking")
        if self.max_duration_s <= 0:
            raise ValueError("max_duration_s must be positive")


@dataclass(frozen=True)
class InterruptDetectionResult:
    raw_utterance: str
    normalized_utterance: str
    matched_vocabulary_ids: tuple[str, ...] = ()
    signal_type: str = "none"
    accepted: bool = False
    active_runtime_state: str | None = None
    active_language: str | None = None
    runtime_load_profile: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InFlightOperationContext:
    operation_id: str
    intent_id: str | None = None
    capability_id: str | None = None
    runtime_state: str = "idle"
    reversible: bool = True
    cancellation_state: str = "idle"
    follow_on_work_suppressed: bool = False
    provider_id: str | None = None
    requires_network: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeRecoveryOutcome:
    trigger: str
    status: str
    spoken_text: str
    error_code: str | None
    duration_ms: int
    next_runtime_state: str
    completion_status: str
    interrupt_signal_type: str | None = None
    offline_policy_decision: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    preemption_latency_ms: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    matched_vocabulary_ids: tuple[str, ...] = ()
    follow_on_work_suppressed: bool = False
    cancellation_state: str | None = None
    degraded_mode: bool = False
    degraded_reason: str | None = None
    runtime_load_profile: str | None = None

    def __post_init__(self) -> None:
        if not self.spoken_text.strip():
            raise ValueError("spoken_text is required")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WakeReliabilityOutcome:
    trigger: str
    status: str
    spoken_text: str
    next_runtime_state: str
    selected_wake_mode: str
    canonical_wake_alias: str | None = None
    weak_detection: bool = False
    confirmation_required: bool = False
    error_code: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in WAKE_RELIABILITY_STATUSES:
            raise ValueError("status must be a supported wake reliability status")
        if self.status == "wake_accepted" and self.next_runtime_state != "listening":
            raise ValueError("wake_accepted requires next_runtime_state=listening")
        if self.status == "confirmation_required" and not self.confirmation_required:
            raise ValueError("confirmation_required status requires confirmation_required=True")
        if self.status in {"wake_rejected", "wake_missed", "degraded_standby"} and self.next_runtime_state != "standby":
            raise ValueError("wake_rejected, wake_missed, and degraded_standby must return to standby")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpeechLoopRecoveryResult:
    trigger: str
    status: str
    spoken_text: str
    returned_state: str
    fault_sequence_count: int
    last_fault_type: str
    degraded_mode: bool = False
    error_code: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in SPEECH_LOOP_RECOVERY_STATUSES:
            raise ValueError("status must be a supported speech-loop recovery status")
        if not self.spoken_text.strip():
            raise ValueError("spoken_text is required")
        if self.fault_sequence_count < 1:
            raise ValueError("fault_sequence_count must be >= 1")
        if self.fault_sequence_count >= 3 and self.returned_state != "standby":
            raise ValueError("fault_sequence_count >= 3 requires returned_state=standby")
        if self.status == "degraded_recovery" and not self.degraded_mode:
            raise ValueError("degraded_recovery requires degraded_mode=True")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WakePolicySelection:
    selected_mode: str
    fallback_mode: str
    dev_fallback_mode: str
    selection_source: str
    degraded_mode: bool = False
    degraded_reason: str | None = None
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StandbyWakeOutcome:
    trigger: str
    status: str
    spoken_text: str
    next_runtime_state: str
    selected_wake_mode: str
    attempt_source_mode: str | None = None
    source_classification: str | None = None
    canonical_wake_alias: str | None = None
    command_suffix_ignored: bool = False
    error_code: str | None = None
    degraded_mode: bool = False
    degraded_reason: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"wake_accepted", "wake_rejected", "wake_missed", "degraded_standby"}:
            raise ValueError("status must be wake_accepted, wake_rejected, wake_missed, or degraded_standby")
        if self.status == "wake_accepted" and self.next_runtime_state not in {"wake", "listening"}:
            raise ValueError("wake_accepted requires next_runtime_state to be wake or listening")
        if self.status in {"wake_rejected", "wake_missed", "degraded_standby"} and self.next_runtime_state != "standby":
            raise ValueError("wake_rejected, wake_missed, and degraded_standby must return to standby")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def coalesce_priority_events(
    events: list[InteractionPriorityEvent],
    *,
    coalescing_window_s: float = 2.0,
) -> list[InteractionPriorityEvent]:
    """Sort by priority and drop duplicate same-priority events in time window."""
    if coalescing_window_s <= 0:
        raise ValueError("coalescing_window_s must be positive")

    ordered = sorted(events, key=lambda event: event.sort_key())
    result: list[InteractionPriorityEvent] = []
    latest_by_group: dict[tuple[str, str], float] = {}

    for event in ordered:
        group = event.coalescing_group or event.message_key
        group_key = (event.priority, group)
        previous_ts = latest_by_group.get(group_key)
        if previous_ts is not None and (event.created_at_s - previous_ts) <= coalescing_window_s:
            continue
        latest_by_group[group_key] = event.created_at_s
        result.append(event)

    return result
