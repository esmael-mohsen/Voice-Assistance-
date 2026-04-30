"""Integration coverage for SpeakKit provider selection/runtime behavior."""

from __future__ import annotations

import pytest

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.wake_word import WakeAction, WakeResult


class _WakeService:
    def __init__(self, responses=None, *, available=True) -> None:
        self._responses = list(responses or [])
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        if not self._responses:
            return None
        return self._responses.pop(0)


class _SttService:
    def __init__(self, *, any_responses=None, command_responses=None, available=True) -> None:
        self.any_responses = list(any_responses or [])
        self.command_responses = list(command_responses or [])
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def set_language(self, _language):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self.any_responses:
            return None
        return self.any_responses.pop(0)

    def listen_command(self):
        if not self.command_responses:
            return None
        return self.command_responses.pop(0)


class _TtsService:
    def __init__(self, *, available=True) -> None:
        self._available = available
        self.spoken: list[str] = []

    def is_available(self) -> bool:
        return self._available

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

    def speak(self, text):
        self.spoken.append(text)
        return text


def _bundle(provider_id: str, *, wake, stt, tts) -> ProviderBundle:
    return ProviderBundle(
        profile=SpeechProviderProfile(provider_id=provider_id, display_name=provider_id),
        wake_service=wake,
        stt_service=stt,
        tts_service=tts,
    )


def _speakkit_ready_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    legacy = _bundle(
        LEGACY_PROVIDER_ID,
        wake=_WakeService(available=True),
        stt=_SttService(available=True),
        tts=_TtsService(available=True),
    )
    speakkit = _bundle(
        SPEAKKIT_PROVIDER_ID,
        wake=_WakeService(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")], available=True),
        stt=_SttService(any_responses=["hi egb"], command_responses=["status", None], available=True),
        tts=_TtsService(available=True),
    )
    registry.register(legacy)
    registry.register(speakkit)
    return registry


@pytest.mark.parametrize("mode", [RuntimeMode.GUI, RuntimeMode.CONSOLE])
def test_speakkit_provider_is_used_when_selected(mode, isolated_settings_manager, dispatch_spy_factory) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "en-US", "speech_provider": SPEAKKIT_PROVIDER_ID},
        persist=False,
    )
    events = []
    runtime = AssistantRuntime(
        mode=mode,
        observer=events.append,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=_speakkit_ready_registry(),
        dispatcher=dispatch_spy_factory(responses=["All good"]),
    )
    runtime.run_forever(max_cycles=3)

    config_payloads = [event.payload for event in events if event.type == RuntimeEventType.CONFIG]
    assert config_payloads
    assert config_payloads[-1]["speech_provider"] == SPEAKKIT_PROVIDER_ID
    assert any(event.type == RuntimeEventType.ASSISTANT for event in events)
