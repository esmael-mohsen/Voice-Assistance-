"""Smoke validations for configured and first-run parity scenarios."""

from queue import Queue
import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.release_metrics import build_pilot_voice_ux_summary
from core.wake_word import WakeAction, WakeResult
from ui.assistant_worker import AssistantWorker

SMOKE_SCENARIOS = [
    {
        "name": "gui_configured_profile",
        "mode": "gui",
        "configured_profile": True,
        "expects_onboarding": False,
    },
    {
        "name": "console_configured_profile",
        "mode": "console",
        "configured_profile": True,
        "expects_onboarding": False,
    },
    {
        "name": "gui_first_run_onboarding",
        "mode": "gui",
        "configured_profile": False,
        "expects_onboarding": True,
    },
    {
        "name": "console_first_run_onboarding",
        "mode": "console",
        "configured_profile": False,
        "expects_onboarding": True,
    },
]


def test_smoke_scenarios_cover_both_modes_and_profile_states() -> None:
    modes = {scenario["mode"] for scenario in SMOKE_SCENARIOS}
    profile_states = {scenario["configured_profile"] for scenario in SMOKE_SCENARIOS}

    assert modes == {"gui", "console"}
    assert profile_states == {True, False}


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=[s["name"] for s in SMOKE_SCENARIOS])
def test_smoke_scenario_shape(scenario: dict[str, object]) -> None:
    required_fields = {"name", "mode", "configured_profile", "expects_onboarding"}
    assert required_fields.issubset(scenario.keys())


def _run_smoke_scenario(
    scenario: dict[str, object],
    *,
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
):
    isolated_settings_manager.username = "Tester" if scenario["configured_profile"] else ""
    isolated_settings_manager.language = "en-US"
    isolated_settings_manager.voice_gender = "female"
    isolated_settings_manager.speech_speed = 1.0

    events = []
    if scenario["configured_profile"]:
        any_responses = ["hi egb"]
        command_responses = ["status update", None]
        dispatch_responses = ["System healthy"]
        max_cycles = 3
    else:
        any_responses = ["hi egb", "english", "female", "1.0", "First User", "yes"]
        command_responses = [None]
        dispatch_responses = []
        max_cycles = 2

    listener = listener_factory(any_responses=any_responses, command_responses=command_responses)
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    dispatch = dispatch_spy_factory(responses=dispatch_responses)

    runtime = AssistantRuntime(
        mode=RuntimeMode(scenario["mode"]),
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=max_cycles)
    return events


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=[s["name"] for s in SMOKE_SCENARIOS])
def test_smoke_runtime_parity_scenarios(
    scenario: dict[str, object],
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    events = _run_smoke_scenario(
        scenario,
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
    )

    states = [event.payload["state"] for event in events if event.type == RuntimeEventType.STATUS]
    assert "standby" in states
    assert "wake" in states

    if scenario["expects_onboarding"]:
        assert "setup" in states
    else:
        assert "setup" not in states


class _GuiBridgeSmokeRuntime:
    def __init__(self, *, mode, observer, default_language=None):  # noqa: ARG002
        self.mode = mode
        self.observer = observer
        self.running = False
        self.start_calls = 0
        self.stop_calls = 0
        self.shutdown_calls = 0

    def start_in_background(self) -> None:
        self.start_calls += 1
        self.running = True
        from core.assistant_runtime import RuntimeEvent, RuntimeEventType

        sequence = [
            RuntimeEvent(RuntimeEventType.STATUS, "gui-session", {"state": "standby"}, "2026-01-01T00:00:00+00:00"),
            RuntimeEvent(RuntimeEventType.CONFIG, "gui-session", {"language": "en-US", "gender": "female", "speed": 1.0}, "2026-01-01T00:00:01+00:00"),
            RuntimeEvent(RuntimeEventType.STATUS, "gui-session", {"state": "wake"}, "2026-01-01T00:00:02+00:00"),
            RuntimeEvent(RuntimeEventType.STATUS, "gui-session", {"state": "listening"}, "2026-01-01T00:00:03+00:00"),
        ]
        for event in sequence:
            self.observer(event)

    def request_stop(self) -> None:
        self.stop_calls += 1
        self.running = False

    def shutdown(self, join_timeout_s: float = 2.0) -> None:  # noqa: ARG002
        self.shutdown_calls += 1
        self.running = False


def test_smoke_gui_observer_only_bridge_behavior() -> None:
    queue = Queue()
    created_runtimes = []

    def runtime_factory(*, mode, observer, default_language=None):
        runtime = _GuiBridgeSmokeRuntime(mode=mode, observer=observer, default_language=default_language)
        created_runtimes.append(runtime)
        return runtime

    worker = AssistantWorker(event_queue=queue, runtime_factory=runtime_factory)
    worker.start()
    worker.stop()
    worker.shutdown()

    assert created_runtimes
    runtime = created_runtimes[-1]
    assert runtime.mode == RuntimeMode.GUI
    assert runtime.start_calls == 1
    assert runtime.stop_calls == 1
    assert runtime.shutdown_calls == 1

    drained = []
    while not queue.empty():
        drained.append(queue.get_nowait())

    states = [event.payload.get("state") for event in drained if event.type == "status"]
    assert states[:3] == ["standby", "wake", "listening"]
    assert any(event.type == "config" for event in drained)


def test_smoke_first_run_arabic_onboarding_remains_readable(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.language = "ar-EG"
    isolated_settings_manager.username = ""
    listener = listener_factory(
        any_responses=["مرحبا", "عربي", "أنثى", "1.0", "سارة", "نعم"],
        command_responses=[None],
    )
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="مرحبا")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=lambda _event: None,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
    )
    runtime.run_forever(max_cycles=2)

    spoken = " ".join(tts.spoken_texts)
    assert "هذه أول مرة للتشغيل" in spoken
    assert "قل اسمك." in spoken
    assert "هل اسمك سارة" in spoken
    assert "ط§ظ" not in spoken


def test_smoke_runtime_config_includes_phase14_audio_profile_fields(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "command_capture_profile_id": "command.default",
            "speech_qualification_profile": "default",
        },
        persist=False,
    )
    events = _run_smoke_scenario(
        {
            "name": "console_configured_profile",
            "mode": "console",
            "configured_profile": True,
            "expects_onboarding": False,
        },
        isolated_settings_manager=isolated_settings_manager,
        listener_factory=listener_factory,
        tts_engine_factory=tts_engine_factory,
        wake_detector_factory=wake_detector_factory,
        dispatch_spy_factory=dispatch_spy_factory,
    )
    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    assert config_payloads[-1]["command_capture_profile_id"] == "command.default"


def test_smoke_phase16_turn_taking_window_events_are_emitted_for_guided_prompts(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    events = []
    listener = listener_factory(any_responses=["english"])
    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts_engine_factory(),
        wake_detector_factory=lambda: wake_detector_factory(),
        dispatcher=lambda _text: None,
    )
    runtime._initialize_runtime()
    runtime._announce_and_listen_with_barge_in(
        "runtime.onboarding.language",
        ["en-US", "ar-EG"],
        prompt="[SETUP] Language",
        timeout=8,
        phrase_time_limit=6,
    )

    turn_taking_payloads = [
        event.payload["turn_taking_window"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and "turn_taking_window" in event.payload
    ]
    assert turn_taking_payloads
    assert turn_taking_payloads[0]["status"] in {"speaking_with_barge_in", "speaking_only"}


def test_smoke_phase16_pilot_voice_ux_summary_remains_field_safe() -> None:
    payload = build_pilot_voice_ux_summary(
        run_id="pilot-ux-smoke-01",
        scenario_label="quickstart-smoke",
        journey_type="onboarding",
        completion_status="completed",
        retries_used=1,
        accepted_barge_in_count=1,
        prompt_echo_suppression_count=0,
        out_of_domain_rejection_count=0,
        fallback_or_exit_reason=None,
        artifact_path="artifacts/pilot-ux-smoke-01/voice-ux-summary.json",
    )
    assert payload["raw_utterance_present"] is False
    assert payload["accepted_barge_in_count"] == 1
