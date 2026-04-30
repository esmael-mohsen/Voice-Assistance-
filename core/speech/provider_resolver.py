"""Provider selection and fallback-policy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.speech.interfaces import (
    LEGACY_PROVIDER_ID,
    SPEAKKIT_PROVIDER_ID,
    WAKE_MODE_HARDWARE_TRIGGER,
    WAKE_MODE_KEYWORD_LOW_POWER,
    WAKE_MODE_STT_BASED,
    normalize_provider_id,
)
from core.speech.provider_registry import ProviderRegistry

STARTUP_UNAVAILABLE_REASON = "provider_unavailable_at_startup"
DUAL_PROVIDER_UNAVAILABLE_REASON = "dual_provider_unavailable"
SPEAKKIT_FALLBACK_REASON = "speakkit_fallback_to_legacy"
LEGACY_NO_AUTOSWITCH_REASON = "legacy_no_auto_switch"
NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON = "network_required_provider_offline"
PROVIDER_UNAVAILABLE_REASON = "provider_unavailable"
OFFLINE_NOT_ALLOWLISTED = "offline_not_allowlisted"
OFFLINE_ALLOWLISTED_FALLBACK = "offline_allowlisted_fallback"
OVERRIDE_MODES: frozenset[str] = frozenset({"auto", "force_offline", "force_online"})
DETECTED_STATUSES: frozenset[str] = frozenset({"online", "offline", "uncertain"})
CONFIRMED_STATUSES: frozenset[str] = frozenset({"online", "offline", "unknown"})
PROVIDER_AVAILABILITIES: frozenset[str] = frozenset({"ready", "degraded", "unavailable"})
DEFAULT_CONNECTIVITY_GRACE_S = 2.0


def normalize_override_mode(mode: str | None) -> str:
    candidate = str(mode or "auto").strip().lower()
    if candidate not in OVERRIDE_MODES:
        return "auto"
    return candidate


def normalize_detected_status(status: str | None) -> str:
    candidate = str(status or "online").strip().lower()
    if candidate not in DETECTED_STATUSES:
        return "online"
    return candidate


def normalize_confirmed_status(status: str | None) -> str:
    candidate = str(status or "unknown").strip().lower()
    if candidate not in CONFIRMED_STATUSES:
        return "unknown"
    return candidate


def normalize_provider_availability(status: str | None) -> str:
    candidate = str(status or "ready").strip().lower()
    if candidate not in PROVIDER_AVAILABILITIES:
        return "ready"
    return candidate


def normalize_offline_allowlist(
    offline_allowlist: set[str] | list[str] | tuple[str, ...] | None,
) -> set[str]:
    if not offline_allowlist:
        return set()
    return {str(item).strip().lower() for item in offline_allowlist if str(item).strip()}


@dataclass(frozen=True)
class ConnectivityState:
    override_mode: str = "auto"
    detected_status: str = "online"
    effective_network_available: bool = True
    last_confirmed_status: str = "online"
    last_confirmed_at: float | None = None
    grace_window_active: bool = False
    grace_window_deadline_at: float | None = None
    probe_generation: int = 0
    startup_reset_applied: bool = False

    def to_dict(self) -> dict[str, str | bool | float | int | None]:
        return {
            "override_mode": self.override_mode,
            "detected_status": self.detected_status,
            "effective_network_available": self.effective_network_available,
            "last_confirmed_status": self.last_confirmed_status,
            "last_confirmed_at": self.last_confirmed_at,
            "grace_window_active": self.grace_window_active,
            "grace_window_deadline_at": self.grace_window_deadline_at,
            "probe_generation": self.probe_generation,
            "startup_reset_applied": self.startup_reset_applied,
            # Compatibility alias for existing runtime context consumers.
            "network_available": self.effective_network_available,
        }


@dataclass(frozen=True)
class NetworkProbeResult:
    source: str
    target_label: str
    status: str
    latency_ms: int
    checked_at: float
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, str | int | float | None]:
        return {
            "source": self.source,
            "target_label": self.target_label,
            "status": self.status,
            "latency_ms": max(0, int(self.latency_ms)),
            "checked_at": float(self.checked_at),
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True)
class StartupResolution:
    persisted_provider: str
    session_provider: str
    selection_source: str
    degraded_mode: bool = False
    degraded_reason: str | None = None
    persisted_provider_unchanged: bool = True
    offline_required: bool = False
    provider_availability: str = "unavailable"
    requires_network: bool = False
    override_mode: str = "auto"
    detected_status: str = "online"
    effective_network_available: bool = True


@dataclass(frozen=True)
class ProviderSwitchDecision:
    active_provider: str
    requested_provider: str
    applied_provider: str
    pending_provider: str | None
    deferred_until_restart: bool


@dataclass(frozen=True)
class FailureResolution:
    active_provider: str
    stage: str
    recoverable: bool
    fallback_provider: str | None
    fallback_applied: bool
    next_state: str
    manual_restart_required: bool
    reason_code: str


@dataclass(frozen=True)
class OfflineExecutionDecision:
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
    spoken_surface_id: str | None
    spoken_text: str

    @property
    def network_available(self) -> bool:
        # Compatibility accessor retained for existing callers.
        return self.effective_network_available

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "flow": self.flow,
            "capability_id": self.capability_id,
            "provider_id": self.provider_id,
            "override_mode": self.override_mode,
            "detected_status": self.detected_status,
            "effective_network_available": self.effective_network_available,
            "provider_availability": self.provider_availability,
            "requires_network": self.requires_network,
            "offline_allowlisted": self.offline_allowlisted,
            "decision": self.decision,
            "error_code": self.error_code,
            "spoken_surface_id": self.spoken_surface_id,
            "spoken_text": self.spoken_text,
            # Compatibility alias for existing consumers/tests.
            "network_available": self.effective_network_available,
        }


@dataclass(frozen=True)
class WakeModeSelection:
    selected_mode: str
    fallback_mode: str
    dev_fallback_mode: str
    selection_source: str = "configured"
    degraded_mode: bool = False
    degraded_reason: str | None = None
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "selected_mode": self.selected_mode,
            "fallback_mode": self.fallback_mode,
            "dev_fallback_mode": self.dev_fallback_mode,
            "selection_source": self.selection_source,
            "degraded_mode": self.degraded_mode,
            "degraded_reason": self.degraded_reason,
            "fallback_reason": self.fallback_reason,
        }


def build_connectivity_state(
    *,
    override_mode: str = "auto",
    detected_status: str = "online",
    last_confirmed_status: str = "online",
    last_confirmed_at: float | None = None,
    grace_window_deadline_at: float | None = None,
    probe_generation: int = 0,
    startup_reset_applied: bool = False,
    now_s: float | None = None,
) -> ConnectivityState:
    mode = normalize_override_mode(override_mode)
    detected = normalize_detected_status(detected_status)
    confirmed = normalize_confirmed_status(last_confirmed_status)
    now_value = float(now_s) if now_s is not None else None

    grace_active = (
        detected == "uncertain"
        and grace_window_deadline_at is not None
        and (now_value is None or now_value <= grace_window_deadline_at)
    )

    effective = False
    if mode == "force_online":
        effective = True
    elif mode == "force_offline":
        effective = False
    elif detected == "online":
        effective = True
    elif detected == "offline":
        effective = False
    elif grace_active and confirmed == "online":
        effective = True

    return ConnectivityState(
        override_mode=mode,
        detected_status=detected,
        effective_network_available=effective,
        last_confirmed_status=confirmed,
        last_confirmed_at=last_confirmed_at,
        grace_window_active=grace_active,
        grace_window_deadline_at=grace_window_deadline_at,
        probe_generation=max(0, int(probe_generation)),
        startup_reset_applied=bool(startup_reset_applied),
    )


def connectivity_state_from_snapshot(
    snapshot: ConnectivityState | dict[str, Any] | None,
    *,
    now_s: float | None = None,
) -> ConnectivityState:
    if isinstance(snapshot, ConnectivityState):
        return build_connectivity_state(
            override_mode=snapshot.override_mode,
            detected_status=snapshot.detected_status,
            last_confirmed_status=snapshot.last_confirmed_status,
            last_confirmed_at=snapshot.last_confirmed_at,
            grace_window_deadline_at=snapshot.grace_window_deadline_at,
            probe_generation=snapshot.probe_generation,
            startup_reset_applied=snapshot.startup_reset_applied,
            now_s=now_s,
        )
    snapshot_map = dict(snapshot or {})
    return build_connectivity_state(
        override_mode=str(snapshot_map.get("override_mode", "auto")),
        detected_status=str(snapshot_map.get("detected_status", "online")),
        last_confirmed_status=str(snapshot_map.get("last_confirmed_status", "unknown")),
        last_confirmed_at=snapshot_map.get("last_confirmed_at"),
        grace_window_deadline_at=snapshot_map.get("grace_window_deadline_at"),
        probe_generation=int(snapshot_map.get("probe_generation", 0) or 0),
        startup_reset_applied=bool(snapshot_map.get("startup_reset_applied", False)),
        now_s=now_s,
    )


def resolve_startup_provider(
    persisted_provider: str | None,
    registry: ProviderRegistry,
    *,
    connectivity_state: ConnectivityState | dict[str, Any] | None = None,
) -> StartupResolution:
    persisted = normalize_provider_id(persisted_provider)
    connectivity = connectivity_state_from_snapshot(connectivity_state, now_s=None)

    if registry.is_available(persisted):
        session_provider = persisted
        selection_source = "persisted"
        degraded_mode = False
        degraded_reason = None
    elif persisted == SPEAKKIT_PROVIDER_ID and registry.is_available(LEGACY_PROVIDER_ID):
        session_provider = LEGACY_PROVIDER_ID
        selection_source = "startup_fallback"
        degraded_mode = True
        degraded_reason = STARTUP_UNAVAILABLE_REASON
    elif persisted != LEGACY_PROVIDER_ID and registry.is_available(LEGACY_PROVIDER_ID):
        session_provider = LEGACY_PROVIDER_ID
        selection_source = "default"
        degraded_mode = True
        degraded_reason = "unknown_provider"
    else:
        return StartupResolution(
            persisted_provider=persisted,
            session_provider=persisted,
            selection_source="persisted",
            degraded_mode=True,
            degraded_reason=DUAL_PROVIDER_UNAVAILABLE_REASON,
            persisted_provider_unchanged=True,
            offline_required=True,
            provider_availability="unavailable",
            requires_network=False,
            override_mode=connectivity.override_mode,
            detected_status=connectivity.detected_status,
            effective_network_available=connectivity.effective_network_available,
        )

    provider_availability = registry.get_availability(session_provider).value
    requires_network = registry.requires_network(session_provider)
    offline_required = False

    if provider_availability == "unavailable":
        degraded_mode = True
        degraded_reason = degraded_reason or DUAL_PROVIDER_UNAVAILABLE_REASON
        offline_required = True
    elif requires_network and not connectivity.effective_network_available:
        degraded_mode = True
        degraded_reason = degraded_reason or NETWORK_REQUIRED_PROVIDER_OFFLINE_REASON

    return StartupResolution(
        persisted_provider=persisted,
        session_provider=session_provider,
        selection_source=selection_source,
        degraded_mode=degraded_mode,
        degraded_reason=degraded_reason,
        persisted_provider_unchanged=True,
        offline_required=offline_required,
        provider_availability=provider_availability,
        requires_network=requires_network,
        override_mode=connectivity.override_mode,
        detected_status=connectivity.detected_status,
        effective_network_available=connectivity.effective_network_available,
    )


def evaluate_offline_execution_policy(
    *,
    flow: str = "command",
    capability_id: str | None,
    provider_id: str,
    requires_network: bool,
    effective_network_available: bool | None = None,
    network_available: bool | None = None,
    override_mode: str = "auto",
    detected_status: str = "online",
    provider_availability: str = "ready",
    offline_allowlist: set[str] | list[str] | tuple[str, ...] | None,
) -> OfflineExecutionDecision:
    normalized_flow = "startup" if str(flow).strip().lower() == "startup" else "command"
    normalized_provider = normalize_provider_id(provider_id)
    normalized_capability = str(capability_id or "").strip().lower() or None
    allowlist = normalize_offline_allowlist(offline_allowlist)
    allowlisted = bool(normalized_capability and normalized_capability in allowlist)
    availability = normalize_provider_availability(provider_availability)
    resolved_network = bool(
        effective_network_available
        if effective_network_available is not None
        else (network_available if network_available is not None else True)
    )
    normalized_override = normalize_override_mode(override_mode)
    normalized_detected = normalize_detected_status(detected_status)

    if availability == "unavailable":
        decision = "offline_startup" if normalized_flow == "startup" else "provider_degraded"
        return OfflineExecutionDecision(
            flow=normalized_flow,
            capability_id=normalized_capability,
            provider_id=normalized_provider,
            override_mode=normalized_override,
            detected_status=normalized_detected,
            effective_network_available=resolved_network,
            provider_availability=availability,
            requires_network=requires_network,
            offline_allowlisted=allowlisted,
            decision=decision,
            error_code=PROVIDER_UNAVAILABLE_REASON,
            spoken_surface_id=(
                "runtime.startup.provider_unavailable"
                if normalized_flow == "startup"
                else "runtime.offline.safe_refusal"
            ),
            spoken_text="Provider unavailable. Try again when services recover.",
        )

    if resolved_network or not requires_network:
        return OfflineExecutionDecision(
            flow=normalized_flow,
            capability_id=normalized_capability,
            provider_id=normalized_provider,
            override_mode=normalized_override,
            detected_status=normalized_detected,
            effective_network_available=resolved_network,
            provider_availability=availability,
            requires_network=requires_network,
            offline_allowlisted=allowlisted,
            decision="allow_execution",
            error_code=None,
            spoken_surface_id=None,
            spoken_text="",
        )

    if allowlisted:
        return OfflineExecutionDecision(
            flow=normalized_flow,
            capability_id=normalized_capability,
            provider_id=normalized_provider,
            override_mode=normalized_override,
            detected_status=normalized_detected,
            effective_network_available=resolved_network,
            provider_availability=availability,
            requires_network=requires_network,
            offline_allowlisted=True,
            decision="on_device_fallback",
            error_code=OFFLINE_ALLOWLISTED_FALLBACK,
            spoken_surface_id="runtime.offline.safe_refusal",
            spoken_text="Network unavailable. Using local fallback.",
        )

    return OfflineExecutionDecision(
        flow=normalized_flow,
        capability_id=normalized_capability,
        provider_id=normalized_provider,
        override_mode=normalized_override,
        detected_status=normalized_detected,
        effective_network_available=resolved_network,
        provider_availability=availability,
        requires_network=requires_network,
        offline_allowlisted=False,
        decision="safe_refusal",
        error_code=OFFLINE_NOT_ALLOWLISTED,
        spoken_surface_id="runtime.offline.safe_refusal",
        spoken_text="Network unavailable. Try again when connected.",
    )


def resolve_wake_mode(
    *,
    prefer_low_power: bool | None = None,
    hardware_trigger_available: bool = True,
    allow_stt_dev_fallback: bool | None = None,
    wake_primary_mode: str | None = None,
    wake_fallback_mode: str | None = None,
    wake_dev_fallback_mode: str | None = None,
    stt_wake_allowed_in_production: bool | None = None,
    runtime_environment: str = "production_like",
    keyword_wake_available: bool | None = None,
    stt_wake_available: bool = True,
    strict_local_wake_fallback_available: bool = False,
    provider_availability: str = "ready",
    effective_network_available: bool = True,
) -> WakeModeSelection:
    normalized_availability = normalize_provider_availability(provider_availability)

    if wake_primary_mode is None:
        wake_primary_mode = (
            WAKE_MODE_KEYWORD_LOW_POWER if bool(prefer_low_power) else WAKE_MODE_HARDWARE_TRIGGER
        )
    if wake_fallback_mode is None:
        wake_fallback_mode = WAKE_MODE_HARDWARE_TRIGGER
    if wake_dev_fallback_mode is None:
        wake_dev_fallback_mode = WAKE_MODE_STT_BASED
    if stt_wake_allowed_in_production is None:
        stt_wake_allowed_in_production = bool(allow_stt_dev_fallback)
    if keyword_wake_available is None:
        keyword_wake_available = bool(hardware_trigger_available)

    supported_modes = {
        WAKE_MODE_KEYWORD_LOW_POWER,
        WAKE_MODE_HARDWARE_TRIGGER,
        WAKE_MODE_STT_BASED,
    }
    primary_mode = (
        wake_primary_mode
        if wake_primary_mode in supported_modes
        else WAKE_MODE_KEYWORD_LOW_POWER
    )
    fallback_mode = (
        wake_fallback_mode
        if wake_fallback_mode in supported_modes
        else WAKE_MODE_HARDWARE_TRIGGER
    )
    dev_mode = (
        wake_dev_fallback_mode
        if wake_dev_fallback_mode in supported_modes
        else WAKE_MODE_STT_BASED
    )
    runtime_env = str(runtime_environment or "production_like").strip().lower()

    def _mode_allowed(mode: str) -> bool:
        if mode != WAKE_MODE_STT_BASED:
            return True
        if runtime_env == "development":
            return True
        return bool(stt_wake_allowed_in_production)

    def _mode_available(mode: str) -> bool:
        if normalized_availability == "unavailable":
            return False
        if mode == WAKE_MODE_KEYWORD_LOW_POWER:
            return bool(keyword_wake_available)
        if mode == WAKE_MODE_HARDWARE_TRIGGER:
            return bool(hardware_trigger_available)
        if mode == WAKE_MODE_STT_BASED:
            if not bool(stt_wake_available):
                return False
            if bool(effective_network_available):
                return True
            return bool(strict_local_wake_fallback_available)
        return False

    if _mode_allowed(primary_mode) and _mode_available(primary_mode):
        return WakeModeSelection(
            selected_mode=primary_mode,
            fallback_mode=fallback_mode,
            dev_fallback_mode=dev_mode,
            selection_source="configured",
        )

    if _mode_allowed(fallback_mode) and _mode_available(fallback_mode):
        return WakeModeSelection(
            selected_mode=fallback_mode,
            fallback_mode=fallback_mode,
            dev_fallback_mode=dev_mode,
            selection_source="fallback",
            fallback_reason="primary_unavailable",
        )

    if _mode_allowed(dev_mode) and _mode_available(dev_mode):
        return WakeModeSelection(
            selected_mode=dev_mode,
            fallback_mode=fallback_mode,
            dev_fallback_mode=dev_mode,
            selection_source="dev_fallback",
            fallback_reason="dev_fallback",
        )

    local_mode_candidates = (
        mode
        for mode in (primary_mode, fallback_mode)
        if mode in {WAKE_MODE_KEYWORD_LOW_POWER, WAKE_MODE_HARDWARE_TRIGGER}
    )
    local_mode = next(
        (
            mode
            for mode in local_mode_candidates
            if _mode_allowed(mode) and _mode_available(mode)
        ),
        None,
    )
    if local_mode:
        return WakeModeSelection(
            selected_mode=local_mode,
            fallback_mode=fallback_mode,
            dev_fallback_mode=dev_mode,
            selection_source="fallback",
            fallback_reason="local_wake_preserved",
        )

    degraded_reason = "no_permitted_wake_source"
    if (
        not effective_network_available
        and normalized_availability in {"ready", "degraded"}
        and any(
            mode == WAKE_MODE_STT_BASED and _mode_allowed(mode)
            for mode in (primary_mode, fallback_mode, dev_mode)
        )
    ):
        degraded_reason = "weak_network_provider_wake"

    degraded_selected = (
        primary_mode if _mode_allowed(primary_mode) else fallback_mode
    )
    return WakeModeSelection(
        selected_mode=degraded_selected,
        fallback_mode=fallback_mode,
        dev_fallback_mode=dev_mode,
        selection_source="degraded",
        degraded_mode=True,
        degraded_reason=degraded_reason,
        fallback_reason="no_permitted_wake_source",
    )


def resolve_provider_switch_request(
    *,
    active_provider: str,
    requested_provider: str,
    runtime_active: bool,
) -> ProviderSwitchDecision:
    active = normalize_provider_id(active_provider)
    requested = normalize_provider_id(requested_provider)
    if runtime_active:
        return ProviderSwitchDecision(
            active_provider=active,
            requested_provider=requested,
            applied_provider=active,
            pending_provider=requested,
            deferred_until_restart=True,
        )
    return ProviderSwitchDecision(
        active_provider=active,
        requested_provider=requested,
        applied_provider=requested,
        pending_provider=None,
        deferred_until_restart=False,
    )


def resolve_runtime_failure(
    *,
    active_provider: str,
    recoverable: bool,
    stage: str,
    registry: ProviderRegistry,
) -> FailureResolution:
    provider = normalize_provider_id(active_provider)

    if not recoverable:
        return FailureResolution(
            active_provider=provider,
            stage=stage,
            recoverable=False,
            fallback_provider=None,
            fallback_applied=False,
            next_state="offline",
            manual_restart_required=True,
            reason_code="unrecoverable_failure",
        )

    if provider == SPEAKKIT_PROVIDER_ID:
        if registry.is_available(LEGACY_PROVIDER_ID):
            return FailureResolution(
                active_provider=provider,
                stage=stage,
                recoverable=True,
                fallback_provider=LEGACY_PROVIDER_ID,
                fallback_applied=True,
                next_state="standby",
                manual_restart_required=False,
                reason_code=SPEAKKIT_FALLBACK_REASON,
            )

        return FailureResolution(
            active_provider=provider,
            stage=stage,
            recoverable=True,
            fallback_provider=None,
            fallback_applied=False,
            next_state="offline",
            manual_restart_required=True,
            reason_code=DUAL_PROVIDER_UNAVAILABLE_REASON,
        )

    if provider == LEGACY_PROVIDER_ID:
        if not registry.is_available(LEGACY_PROVIDER_ID) and not registry.is_available(SPEAKKIT_PROVIDER_ID):
            return FailureResolution(
                active_provider=provider,
                stage=stage,
                recoverable=True,
                fallback_provider=None,
                fallback_applied=False,
                next_state="offline",
                manual_restart_required=True,
                reason_code=DUAL_PROVIDER_UNAVAILABLE_REASON,
            )

        return FailureResolution(
            active_provider=provider,
            stage=stage,
            recoverable=True,
            fallback_provider=None,
            fallback_applied=False,
            next_state="standby",
            manual_restart_required=False,
            reason_code=LEGACY_NO_AUTOSWITCH_REASON,
        )

    return FailureResolution(
        active_provider=provider,
        stage=stage,
        recoverable=True,
        fallback_provider=None,
        fallback_applied=False,
        next_state="offline",
        manual_restart_required=True,
        reason_code=DUAL_PROVIDER_UNAVAILABLE_REASON,
    )
