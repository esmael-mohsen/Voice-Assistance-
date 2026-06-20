"""Unit tests for shared assistant runtime behavior."""

import threading
import time

import pytest

from core import parser
from core.assistant_runtime import (
    AssistantRuntime,
    OnboardingState,
    ProviderSelectionState,
    RuntimeEventType,
    RuntimeMode,
    RuntimeObserverModel,
    RuntimeSession,
    RuntimeState,
    SettingsSnapshot,
    UnrecoverableRuntimeError,
    build_event,
    config_event,
    error_event,
    status_event,
)
from core.command_models import CommandExecutionResult
from core.command_models import CommandRecognitionResult
from core.command_post_processing import process_command_transcript
from core.speech.interfaces import LEGACY_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult


def test_runtime_session_defaults_and_bootstrap_transition() -> None:
    session = RuntimeSession(mode=RuntimeMode.GUI)
    assert session.state == RuntimeState.OFFLINE
    assert session.can_transition_to(RuntimeState.STANDBY)

    session.transition_to(RuntimeState.STANDBY)
    assert session.state == RuntimeState.STANDBY
    assert session.active is False


def test_runtime_session_rejects_invalid_transition() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    with pytest.raises(ValueError):
        session.transition_to(RuntimeState.LISTENING)


def test_runtime_event_builder_uses_contract_envelope() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    event = build_event(
        RuntimeEventType.SYSTEM,
        session_id=session.session_id,
        payload={"text": "ready"},
    )
    assert event.type == RuntimeEventType.SYSTEM
    assert event.session_id == session.session_id
    assert isinstance(event.timestamp, str)
    assert "T" in event.timestamp


def test_status_and_config_event_shapes_match_contract() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    snapshot = SettingsSnapshot(language="ar-EG", voice_gender="female", speech_speed=1.0, username="")

    state_event = status_event(session, RuntimeState.STANDBY)
    cfg_event = config_event(session, snapshot)

    assert state_event.payload == {"state": "standby"}
    assert cfg_event.payload["language"] == "ar-EG"
    assert cfg_event.payload["gender"] == "female"
    assert cfg_event.payload["speed"] == 1.0
    assert "max_listen_seconds" in cfg_event.payload
    assert "max_speak_seconds" in cfg_event.payload


def test_provider_config_extensions_preserve_baseline_payload_keys() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    snapshot = SettingsSnapshot(language="en-US", voice_gender="female", speech_speed=1.1, username="Tester")
    provider_state = ProviderSelectionState(
        persisted_provider="speakkit",
        session_provider="legacy",
        degraded_mode=True,
        degraded_reason="provider_unavailable_at_startup",
    )

    cfg_event = config_event(session, snapshot, provider_state=provider_state)
    assert cfg_event.payload["language"] == "en-US"
    assert cfg_event.payload["gender"] == "female"
    assert cfg_event.payload["speed"] == 1.1
    assert cfg_event.payload["speech_provider"] == "legacy"
    assert cfg_event.payload["persisted_speech_provider"] == "speakkit"
    assert cfg_event.payload["degraded_mode"] is True


def test_config_event_includes_wearable_policy_fields() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    snapshot = SettingsSnapshot(
        language="en-US",
        voice_gender="female",
        speech_speed=1.0,
        username="Tester",
        max_listen_seconds=6.0,
        max_speak_seconds=5.0,
        priority_coalescing_window_s=2.0,
        wake_primary_mode="keyword_low_power",
        wake_fallback_mode="hardware_trigger",
    )
    cfg_event = config_event(session, snapshot)
    assert cfg_event.payload["max_listen_seconds"] == 6.0
    assert cfg_event.payload["max_speak_seconds"] == 5.0
    assert cfg_event.payload["coalescing_window_s"] == 2.0
    assert cfg_event.payload["wake_primary_mode"] == "keyword_low_power"
    assert cfg_event.payload["wake_fallback_mode"] == "hardware_trigger"


def test_error_event_supports_provider_metadata_extensions() -> None:
    session = RuntimeSession(mode=RuntimeMode.CONSOLE)
    event = error_event(
        session,
        message="temporary provider issue",
        recoverable=True,
        next_state=RuntimeState.STANDBY,
        provider="speakkit",
        stage="listening",
        fallback_applied=True,
        fallback_to="legacy",
        manual_restart_required=False,
        reason_code="speakkit_fallback_to_legacy",
    )
    assert event.payload["message"] == "temporary provider issue"
    assert event.payload["provider"] == "speakkit"
    assert event.payload["stage"] == "listening"
    assert event.payload["fallback_applied"] is True
    assert event.payload["fallback_to"] == "legacy"


def test_runtime_observer_model_accepts_configured_types() -> None:
    observer = RuntimeObserverModel(
        observer_id="gui-bridge",
        mode=RuntimeMode.GUI,
        supported_event_types=frozenset({RuntimeEventType.STATUS, RuntimeEventType.CONFIG}),
    )
    assert observer.accepts(RuntimeEventType.STATUS)
    assert observer.accepts(RuntimeEventType.USER) is False


def test_onboarding_state_can_complete() -> None:
    onboarding = OnboardingState(required=True)
    completed = onboarding.mark_complete("EGB User")
    assert completed.required is False
    assert completed.confirmed_username == "EGB User"
    assert completed.step.value == "complete"


def test_settings_manager_snapshot_helpers(isolated_settings_manager) -> None:
    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["language"] == "ar-EG"
    assert snapshot["voice_gender"] == "female"

    onboarding = isolated_settings_manager.persist_onboarding_configuration(
        language="en-US",
        voice_gender="male",
        speech_speed=1.25,
        username="Tester",
    )
    current = isolated_settings_manager.get_settings_snapshot()

    assert current["language"] == "en-US"
    assert current["voice_gender"] == "male"
    assert current["speech_speed"] == 1.25
    assert current["username"] == "Tester"
    assert onboarding["required"] is False


def _event_collector():
    events = []

    def _observer(event) -> None:
        events.append(event)

    return events, _observer


def test_runtime_lifecycle_flow_for_configured_user(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "voice_gender": "female", "speech_speed": 1.0},
        persist=False,
    )

    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start obstacle detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=["Calendar opened"])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert "wake" in status_states
    assert "thinking" in status_states
    assert "speaking" in status_states
    assert dispatch.calls == ["start obstacle detection"]


def test_runtime_protected_close_intent_does_not_dispatch(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["close app", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    assistant_texts = [event.payload["text"] for event in events if event.type == RuntimeEventType.ASSISTANT]
    assert dispatch.calls == []
    assert any("won't close" in text.lower() for text in assistant_texts)


def test_runtime_recoverable_failure_emits_error_then_standby(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )

    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start obstacle detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=[RuntimeError("temporary error")])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    error_events = [event for event in events if event.type == RuntimeEventType.ERROR]
    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]

    assert error_events
    assert error_events[-1].payload["recoverable"] is True
    assert error_events[-1].payload["next_state"] == "standby"
    assert "error" in status_states
    assert "standby" in status_states


def test_runtime_first_run_onboarding_through_shared_runtime(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events, observer = _event_collector()
    listener = listener_factory(
        any_responses=["hi egb", "english", "female", "1.2", "Alice", "yes"],
        command_responses=[None],
    )
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    snapshot = isolated_settings_manager.get_settings_snapshot()

    assert "setup" in status_states
    assert snapshot["username"] == "Alice"
    assert snapshot["language"] == "en-US"
    assert snapshot["voice_gender"] == "female"
    assert snapshot["speech_speed"] == pytest.approx(1.2)


def test_runtime_first_run_onboarding_accepts_switch_to_arab_phrase(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events, observer = _event_collector()
    listener = listener_factory(
        any_responses=["hi egb", "switch to Arab", "female", "normal", "Mina", "yes"],
        command_responses=[None],
    )
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["username"] == "Mina"
    assert snapshot["language"] == "ar-EG"
    assert snapshot["voice_gender"] == "female"
    assert snapshot["speech_speed"] == pytest.approx(isolated_settings_manager.default_speech_speed)


def test_runtime_onboarding_retries_name_confirmation_before_recapturing_name(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events, observer = _event_collector()
    listener = listener_factory(
        any_responses=["hi egb", "english", "male", "normal", "Ismail", None, "yes"],
        command_responses=[None],
    )
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )

    runtime.run_forever(max_cycles=2)

    snapshot = isolated_settings_manager.get_settings_snapshot()
    assert snapshot["username"] == "Ismail"
    assert [call["prompt"] for call in listener.listen_any_calls].count("[SETUP] Confirm") == 2


def test_runtime_onboarding_language_and_voice_parsers_handle_mixed_inputs(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )

    assert runtime._parse_onboarding_language_choice("switch to Arab") == "ar-EG"
    assert runtime._parse_onboarding_language_choice("please use english") == "en-US"
    assert runtime._parse_onboarding_language_choice("arabic or english") is None
    assert runtime._parse_onboarding_language_choice("english or arabic") is None
    assert runtime._parse_onboarding_voice_choice("I want female voice") == "female"
    assert runtime._parse_onboarding_voice_choice("male voice") == "male"
    assert runtime._parse_onboarding_voice_choice("his voice") == "male"
    assert runtime._parse_onboarding_voice_choice("her voice") == "female"
    assert runtime._parse_onboarding_voice_choice("في ميل") == "female"
    assert runtime._parse_onboarding_voice_choice("mail") == "male"
    assert runtime._parse_onboarding_voice_choice("ميل") == "male"
    assert runtime._parse_onboarding_voice_choice("مين") == "male"
    assert runtime._is_onboarding_noise_response("هاي ايجي بي") is True
    assert runtime._is_onboarding_noise_response("Mina") is False
    assert runtime._is_plausible_username("Mina") is True
    assert runtime._is_plausible_username("what a fool") is False
    assert runtime._parse_onboarding_speed_choice("normal speed") == pytest.approx(
        isolated_settings_manager.default_speech_speed
    )
    assert runtime._parse_onboarding_speed_choice("Norman") == pytest.approx(
        isolated_settings_manager.default_speech_speed
    )
    assert runtime._resolve_canonical_wake_details("\u0647\u0627\u064a \u0627\u064a \u062c\u064a \u0628\u064a") == (
        "hi egb",
        False,
    )
    assert runtime._resolve_canonical_wake_details("\u0647\u0627\u064a \u062c\u064a \u0628\u064a") == (
        "hi egb",
        False,
    )
    assert runtime._resolve_canonical_wake_details("hi egb open navigation") == ("hi egb", True)
    assert runtime._resolve_canonical_wake_details("\u0645\u0631\u062d\u0628\u0627") == (
        "\u0645\u0631\u062d\u0628\u0627",
        False,
    )
    follow_up_calls = {"count": 0}

    def _fake_follow_up(*_args, **_kwargs):
        follow_up_calls["count"] += 1
        return "english"

    runtime._listen_any_with_interrupt = _fake_follow_up  # type: ignore[method-assign]
    assert (
        runtime._resolve_onboarding_prompt_echo(
            answer="you prefer here agree english",
            prompt_text="Do you prefer Arabic or English? Say: Arabic or English.",
            languages=["en-US", "ar-EG"],
            prompt="[SETUP] Language",
            timeout=8,
            phrase_time_limit=6,
            accept_answer=lambda candidate: runtime._parse_onboarding_language_choice(candidate) is not None,
        )
        == "english"
    )
    assert follow_up_calls["count"] == 1
    assert (
        runtime._resolve_onboarding_prompt_echo(
            answer="his voice",
            prompt_text="Choose voice: male or female?",
            languages=["en-US", "ar-EG"],
            prompt="[SETUP] Gender",
            timeout=8,
            phrase_time_limit=6,
            accept_answer=lambda candidate: runtime._parse_onboarding_voice_choice(candidate) is not None,
        )
        == "his voice"
    )
    assert (
        runtime._resolve_onboarding_prompt_echo(
            answer="male voice",
            prompt_text="Choose voice: male or female?",
            languages=["en-US", "ar-EG"],
            prompt="[SETUP] Gender",
            timeout=8,
            phrase_time_limit=6,
            accept_answer=lambda candidate: runtime._parse_onboarding_voice_choice(candidate) is not None,
        )
        == "male voice"
    )


def test_runtime_rerank_keeps_primary_when_same_intent_alternative_is_noisier(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    recognition = CommandRecognitionResult(
        session_id="rerank",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="obstacle detection please",
        confidence_score=0.95,
        confidence_available=True,
        alternative_transcripts=(
            "obstacle detection please",
            "obstacle collection please",
            "obstacle fiction please",
        ),
        detected_language="en-US",
        latency_ms=10,
        error_code=None,
    )

    reranked = runtime._rerank_command_recognition(recognition)

    assert reranked.primary_transcript == "obstacle detection please"


def test_runtime_onboarding_prompt_allows_barge_in_without_waiting_for_tts_completion(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    listener = listener_factory(any_responses=["male"])
    tts = tts_engine_factory(speech_delay_s=0.8)
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()

    started_at = time.perf_counter()
    answer, prompt_text = runtime._announce_and_listen_with_barge_in(
        "runtime.onboarding.voice",
        ["en-US", "ar-EG"],
        prompt="[SETUP] Gender",
        timeout=8,
        phrase_time_limit=6,
    )
    elapsed = time.perf_counter() - started_at

    assert answer == "male"
    assert prompt_text
    assert elapsed < 0.55


def test_runtime_onboarding_prompt_can_wait_until_prompt_finishes_before_listening(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    listener = listener_factory(any_responses=["english"])
    tts = tts_engine_factory(speech_delay_s=0.35)
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()

    started_at = time.perf_counter()
    answer, prompt_text = runtime._announce_and_listen_with_barge_in(
        "runtime.onboarding.language",
        ["en-US", "ar-EG"],
        prompt="[SETUP] Language",
        timeout=12,
        phrase_time_limit=8,
        allow_barge_in=False,
    )
    elapsed = time.perf_counter() - started_at

    assert answer == "english"
    assert prompt_text
    assert elapsed >= 0.30
    turn_payloads = [
        event.payload["turn_taking_window"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "turn_taking_window" in event.payload
    ]
    assert turn_payloads[0]["status"] == "speaking_only"
    assert turn_payloads[0]["barge_in_allowed"] is False


def test_runtime_unrecoverable_failure_transitions_to_offline(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start obstacle detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=[UnrecoverableRuntimeError("fatal failure")])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    error_events = [event for event in events if event.type == RuntimeEventType.ERROR]

    assert "error" in status_states
    assert "offline" in status_states
    assert error_events[-1].payload["recoverable"] is False
    assert error_events[-1].payload["next_state"] == "offline"


def test_runtime_shutdown_finishes_with_offline_without_stopping_status(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=[None], command_responses=[None])
    tts = tts_engine_factory()
    wake = wake_detector_factory()
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.GUI,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=1)

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert status_states[-1] == "offline"
    assert "stopping" not in status_states


def test_runtime_normalizes_structured_dispatch_result_to_spoken_text(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    structured_result = CommandExecutionResult(
        status="success",
        spoken_text="Structured speech",
        intent_id="enable_obstacle_detection",
    )
    assert runtime._normalize_dispatch_result(structured_result) == "Structured speech"


def test_runtime_emits_system_event_with_structured_dispatch_payload(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start obstacle detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    structured_result = CommandExecutionResult(
        status="success",
        spoken_text="Obstacle detection enabled",
        intent_id="enable_obstacle_detection",
        category="capability",
    )
    dispatch = dispatch_spy_factory(responses=[structured_result])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=3)

    system_events = [event for event in events if event.type == RuntimeEventType.SYSTEM]
    assert system_events
    assert any("command_result" in event.payload for event in system_events)


def test_runtime_successful_enable_command_hands_off_to_wake_mode(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=["hi egb"], command_responses=["start money detection", None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    structured_result = CommandExecutionResult(
        status="success",
        spoken_text="Money detection enabled.",
        intent_id="enable_money_detection",
        category="capability",
        metadata={"capability_id": "money_detection"},
    )
    dispatch = dispatch_spy_factory(responses=[structured_result])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=2)

    assistant_texts = [
        event.payload["text"]
        for event in events
        if event.type == RuntimeEventType.ASSISTANT and isinstance(event.payload.get("text"), str)
    ]
    assert any("money detection is running now" in text.lower() for text in assistant_texts)

    guided_payloads = [
        event.payload["guided_dialog_outcome"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "guided_dialog_outcome" in event.payload
    ]
    assert guided_payloads
    assert guided_payloads[-1]["next_runtime_state"] == "standby"

    status_states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert "standby" in status_states
    speaking_index = status_states.index("speaking")
    assert "listening" not in status_states[speaking_index + 1 :]


def test_runtime_emits_startup_readiness_observability(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"username": "Tester", "language": "en-US"}, persist=False)
    events, observer = _event_collector()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=dispatch_spy_factory(),
    )
    runtime.run_forever(max_cycles=1)

    startup_payloads = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("startup_status")
    ]
    assert startup_payloads
    assert startup_payloads[-1]["startup_status"] in {"ready", "degraded", "offline"}


def test_runtime_yes_interpreter_reuses_shared_dialog_policy(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )

    assert runtime._is_yes("yes please") is True
    assert runtime._is_yes("ايوه") is True
    assert runtime._is_yes("yes cancel") is False
    assert runtime._is_yes("not sure") is False


def test_runtime_confidence_policy_uses_settings_snapshot_values(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "command_confidence_high_threshold": 0.9,
            "command_confidence_medium_threshold": 0.7,
            "command_protected_threshold": 0.95,
            "command_max_retry_cycles": 1,
        },
        persist=False,
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text, **_kwargs: None,
    )
    policy = runtime._command_confidence_policy()
    assert policy.high_confidence_threshold == pytest.approx(0.9)
    assert policy.medium_confidence_threshold == pytest.approx(0.7)
    assert policy.protected_command_threshold == pytest.approx(0.95)
    assert policy.max_retry_cycles == 1


def test_runtime_emits_command_recognition_telemetry_in_system_event(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events, observer = _event_collector()
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text, **_kwargs: None,
    )
    sample = CommandRecognitionResult(
        session_id="session-telemetry",
        recognition_path="local_first",
        provider_id="legacy",
        primary_transcript="switch to english",
        confidence_score=0.9,
        confidence_available=True,
        alternative_transcripts=("switch to english",),
        detected_language="en-US",
        latency_ms=11,
        error_code=None,
    )
    decision = runtime._evaluate_confidence_decision(
        recognition_result=sample,
        post_processing=process_command_transcript(sample.primary_transcript),
        parsed_intent=parser.parse_command("switch to english"),
        policy=runtime._command_confidence_policy(),
        retry_count=0,
    )
    runtime._emit_recognition_telemetry(decision.telemetry)
    telemetry_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "command_recognition_telemetry" in event.payload
    ]
    assert telemetry_events


def test_runtime_request_stop_propagates_to_active_speech_components(
    isolated_settings_manager,
) -> None:
    class _StopAwareListener:
        def __init__(self) -> None:
            self.stop_calls = 0
            self.language = "en-US"

        def set_language(self, language_code: str) -> None:
            self.language = language_code

        def request_stop(self) -> None:
            self.stop_calls += 1

        def listen_command(self):
            return None

        def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):  # noqa: ARG002
            return None

    class _StopAwareTTS:
        def __init__(self) -> None:
            self.stop_calls = 0

        def configure(self, **_kwargs):
            return None

        def set_language(self, _language_code):
            return None

        def set_voice_gender(self, _gender):
            return None

        def set_speech_speed(self, _speed):
            return None

        def request_stop(self) -> None:
            self.stop_calls += 1

        def speak(self, _text, **_kwargs):
            return {"completion_status": "success", "duration_ms": 0, "interrupted": False}

    class _StopAwareWake:
        def __init__(self) -> None:
            self.stop_calls = 0

        def detect(self, _text):
            return None

        def wait_for_wake(self, *, timeout_s=1.0, wake_mode=None):  # noqa: ARG002
            return None

        def supports_mode(self, _wake_mode: str) -> bool:
            return True

        def request_stop(self) -> None:
            self.stop_calls += 1

    listener = _StopAwareListener()
    tts = _StopAwareTTS()
    wake = _StopAwareWake()
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy"),
            wake_service=wake,
            stt_service=listener,
            tts_service=tts,
        )
    )

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=registry,
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()
    runtime.request_stop()

    assert wake.stop_calls == 1
    assert listener.stop_calls == 1
    assert tts.stop_calls == 1


def test_runtime_wait_for_provider_wake_respects_interrupt_cancellation(
    isolated_settings_manager,
) -> None:
    class _BlockingWake:
        def __init__(self) -> None:
            self.stop_calls = 0
            self._stop_event = threading.Event()

        def detect(self, _text):
            return None

        def supports_mode(self, _wake_mode: str) -> bool:
            return True

        def wait_for_wake(self, *, timeout_s=1.0, wake_mode=None, interrupt_event=None):  # noqa: ARG002
            self._stop_event.wait(timeout=max(0.1, float(timeout_s) * 2))
            return None

        def request_stop(self) -> None:
            self.stop_calls += 1
            self._stop_event.set()

    class _Listener:
        def __init__(self) -> None:
            self.stop_calls = 0
            self.language = "en-US"

        def set_language(self, language_code: str) -> None:
            self.language = language_code

        def request_stop(self) -> None:
            self.stop_calls += 1

        def listen_command(self):
            return None

        def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):  # noqa: ARG002
            return None

    class _TTS:
        def configure(self, **_kwargs):
            return None

        def set_language(self, _language_code):
            return None

        def set_voice_gender(self, _gender):
            return None

        def set_speech_speed(self, _speed):
            return None

        def speak(self, _text, **_kwargs):
            return {"completion_status": "success", "duration_ms": 0, "interrupted": False}

    listener = _Listener()
    wake = _BlockingWake()
    registry = ProviderRegistry()
    registry.register(
        ProviderBundle(
            profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy"),
            wake_service=wake,
            stt_service=listener,
            tts_service=_TTS(),
        )
    )

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=registry,
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()
    runtime._interrupt_event.set()
    started = time.perf_counter()
    result = runtime._wait_for_provider_wake("keyword_low_power")
    duration_s = time.perf_counter() - started

    assert result is None
    assert wake.stop_calls >= 1
    assert listener.stop_calls >= 1
    assert duration_s < 0.5


def test_runtime_protected_prompt_waits_for_initial_prompt_before_listening(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    listener = listener_factory(any_responses=["yes"])
    tts = tts_engine_factory(speech_delay_s=0.45)
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()

    started = time.perf_counter()
    answer, _prompt = runtime._announce_and_listen_with_barge_in(
        "resolver.confirmation.required",
        ["en-US", "ar-EG"],
        prompt="[SETUP] Confirm",
        timeout=8,
        phrase_time_limit=4,
    )
    elapsed = time.perf_counter() - started

    assert answer == "yes"
    assert elapsed >= 0.35
    turn_taking_payloads = [
        event.payload["turn_taking_window"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "turn_taking_window" in event.payload
    ]
    assert turn_taking_payloads
    assert turn_taking_payloads[0]["status"] == "speaking_only"
    assert turn_taking_payloads[0]["barge_in_allowed"] is False


def test_runtime_prompt_echo_suppression_emits_structured_outcome_without_retry_increment(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener_factory(default_language=default_language),
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._confidence_retry_cycles = 0
    runtime._listen_any_with_interrupt = lambda *_args, **_kwargs: "english"  # type: ignore[method-assign]

    resolved = runtime._resolve_onboarding_prompt_echo(
        answer="Do you prefer Arabic or English",
        prompt_text="Do you prefer Arabic or English? Say: Arabic or English.",
        languages=["en-US", "ar-EG"],
        prompt="[SETUP] Language",
        timeout=8,
        phrase_time_limit=6,
        accept_answer=lambda _candidate: False,
    )
    assert resolved == "english"
    assert runtime._confidence_retry_cycles == 0

    guided_payloads = [
        event.payload["guided_dialog_outcome"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "guided_dialog_outcome" in event.payload
    ]
    assert guided_payloads
    assert any(payload["status"] == "prompt_echo_suppressed" for payload in guided_payloads)


def test_runtime_standby_wake_repeated_misses_remain_stable(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events, observer = _event_collector()
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    listener = listener_factory(
        command_result_responses=[
            {
                "primary_transcript": "",
                "recognition_source": "wake_strict_vosk_fallback",
                "failure_reason_code": "strict_grammar_no_match",
                "error_code": "strict_grammar_no_match",
            }
            for _ in range(5)
        ],
        command_responses=[None],
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=5)

    missed = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_missed"
    ]
    assert len(missed) == 5
    assert missed[-1]["payload"]["wake_miss_streak"] >= 5
    assert all(item["next_state"] == "standby" for item in missed)


def test_runtime_standby_wake_miss_streak_resets_after_acceptance(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events, observer = _event_collector()
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "en-US",
            "wake_primary_mode": "stt_based_wake",
            "wake_fallback_mode": "hardware_trigger",
            "wake_dev_fallback_mode": "stt_based_wake",
            "stt_wake_allowed_in_production": True,
        },
        persist=False,
    )
    listener = listener_factory(
        command_result_responses=[
            {
                "primary_transcript": "",
                "recognition_source": "wake_strict_vosk_fallback",
                "failure_reason_code": "strict_grammar_no_match",
                "error_code": "strict_grammar_no_match",
            },
            {
                "primary_transcript": "",
                "recognition_source": "wake_strict_vosk_fallback",
                "failure_reason_code": "strict_grammar_no_match",
                "error_code": "strict_grammar_no_match",
            },
            {
                "primary_transcript": "hi egb",
                "alternative_transcripts": ("hi egb",),
                "recognition_source": "cloud_primary",
                "failure_reason_code": None,
                "error_code": None,
            },
        ],
        command_responses=[None],
    )
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime.run_forever(max_cycles=3)

    accepted = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("status") == "wake_accepted"
    ]
    assert accepted
    assert accepted[-1]["payload"]["wake_miss_streak"] == 0
