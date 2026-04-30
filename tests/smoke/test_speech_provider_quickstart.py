"""Smoke validation matrix for speech-provider quickstart scenarios."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.release_gates import evaluate_pi_qualification_run, evaluate_speech_release_gate
from core.release_models import PiQualificationMetrics
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import NetworkProbeResult, resolve_runtime_failure


class _Wake:
    def __init__(self, *, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def detect(self, _text):
        return None


class _Stt:
    def __init__(self, *, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def set_language(self, _language):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        return None

    def listen_command(self):
        return None


class _Tts:
    def __init__(self, *, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def configure(self, **_kwargs):
        return None

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def set_voice_profile(self, _voice):
        return None

    def speak(self, _text):
        return None


class _Probe:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = list(statuses)
        self._index = 0

    def probe(self, *, source: str = "background") -> NetworkProbeResult:
        status = self._statuses[min(self._index, len(self._statuses) - 1)]
        self._index += 1
        return NetworkProbeResult(
            source=source,
            target_label="smoke_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "smoke_status",
        )


def _bundle(provider_id: str, *, available: bool) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(provider_id=provider_id, display_name=provider_id, requires_network=True),
        wake_service=_Wake(available=available),
        stt_service=_Stt(available=available),
        tts_service=_Tts(available=available),
    )


def _registry(*, legacy_available: bool, speakkit_available: bool) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(_bundle(LEGACY_PROVIDER_ID, available=legacy_available))
    registry.register(_bundle(SPEAKKIT_PROVIDER_ID, available=speakkit_available))
    return registry


SMOKE_SCENARIOS = [
    {
        "name": "persisted_legacy_available",
        "persisted_provider": LEGACY_PROVIDER_ID,
        "legacy_available": True,
        "speakkit_available": False,
        "expected_provider": LEGACY_PROVIDER_ID,
        "expect_offline": False,
    },
    {
        "name": "persisted_speakkit_available",
        "persisted_provider": SPEAKKIT_PROVIDER_ID,
        "legacy_available": True,
        "speakkit_available": True,
        "expected_provider": SPEAKKIT_PROVIDER_ID,
        "expect_offline": False,
    },
    {
        "name": "persisted_speakkit_unavailable_degrades",
        "persisted_provider": SPEAKKIT_PROVIDER_ID,
        "legacy_available": True,
        "speakkit_available": False,
        "expected_provider": LEGACY_PROVIDER_ID,
        "expect_offline": False,
    },
    {
        "name": "dual_unavailable_offline",
        "persisted_provider": SPEAKKIT_PROVIDER_ID,
        "legacy_available": False,
        "speakkit_available": False,
        "expected_provider": None,
        "expect_offline": True,
    },
]


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=[s["name"] for s in SMOKE_SCENARIOS])
def test_provider_quickstart_matrix(scenario, isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "speech_provider": scenario["persisted_provider"]},
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(
            legacy_available=scenario["legacy_available"],
            speakkit_available=scenario["speakkit_available"],
        ),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    if scenario["expect_offline"]:
        assert states == ["offline"]
        return

    config_events = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_events
    assert config_events[-1]["speech_provider"] == scenario["expected_provider"]


def test_restart_only_switch_is_applied_on_next_startup_smoke(isolated_settings_manager) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "speech_provider": LEGACY_PROVIDER_ID},
        persist=False,
    )
    isolated_settings_manager.request_speech_provider(SPEAKKIT_PROVIDER_ID, runtime_active=True)

    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_registry(legacy_available=True, speakkit_available=True),
        network_probe=_Probe(["online", "online"]),
    )
    runtime.run_forever(max_cycles=1)

    config_events = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_events
    assert config_events[-1]["speech_provider"] == SPEAKKIT_PROVIDER_ID
    assert isolated_settings_manager.pending_speech_provider is None
    assert isolated_settings_manager.deferred_provider_switch is False


def test_failure_policy_matrix_smoke() -> None:
    registry = _registry(legacy_available=True, speakkit_available=True)
    speakkit_failure = resolve_runtime_failure(
        active_provider=SPEAKKIT_PROVIDER_ID,
        recoverable=True,
        stage="listening",
        registry=registry,
    )
    legacy_failure = resolve_runtime_failure(
        active_provider=LEGACY_PROVIDER_ID,
        recoverable=True,
        stage="listening",
        registry=registry,
    )
    dual_failure = resolve_runtime_failure(
        active_provider=SPEAKKIT_PROVIDER_ID,
        recoverable=True,
        stage="startup",
        registry=_registry(legacy_available=False, speakkit_available=False),
    )

    assert speakkit_failure.fallback_applied is True
    assert speakkit_failure.fallback_provider == LEGACY_PROVIDER_ID
    assert legacy_failure.fallback_applied is False
    assert dual_failure.next_state == "offline"


def test_release_gate_quickstart_blocks_without_pi_evidence() -> None:
    gate = evaluate_speech_release_gate(
        candidate_build_id="smoke-candidate-01",
        ci_replay_status="passed",
        pi_qualification_run=None,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json"],
    )

    assert gate.gate_status == "blocked"
    assert "missing_pi4_qualification" in gate.blocked_reasons


def test_release_gate_quickstart_allows_candidate_with_passing_pi_run() -> None:
    pi_run = evaluate_pi_qualification_run(
        run_id="smoke-pi-run-01",
        candidate_build_id="smoke-candidate-02",
        qualification_profile_id="wake.default",
        metrics=PiQualificationMetrics(
            duration_minutes=30,
            standby_cpu_median_pct=18.0,
            wake_cpu_peak_pct=43.0,
            listen_cpu_peak_pct=39.0,
            listen_memory_mb=214.0,
            speak_cpu_peak_pct=36.0,
            speak_memory_mb=220.0,
            startup_latency_ms=3900,
            peak_temp_c=72.0,
            repeated_wake_cycles=120,
            unexpected_shutdown_count=0,
            telemetry_completeness_ratio=0.99,
        ),
        threshold_policy={
            "standby_cpu_budget_pct": 25.0,
            "wake_cpu_peak_pct_max": 55.0,
            "listen_cpu_peak_pct_max": 60.0,
            "speak_cpu_peak_pct_max": 60.0,
            "startup_latency_ms_max": 5000.0,
            "peak_temp_c_max": 80.0,
            "unexpected_shutdown_count_max": 0.0,
            "telemetry_completeness_ratio_min": 0.95,
            "repeated_wake_cycles_min": 60.0,
        },
    )
    gate = evaluate_speech_release_gate(
        candidate_build_id="smoke-candidate-02",
        ci_replay_status="passed",
        pi_qualification_run=pi_run,
        required_artifacts=["telemetry-summary.json", "pi-qualification.json"],
        available_artifacts=["telemetry-summary.json", "pi-qualification.json"],
    )

    assert gate.gate_status == "approved"
    assert gate.approved_for_pilot is True
