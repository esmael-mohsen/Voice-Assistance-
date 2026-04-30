"""Integration coverage for runtime critical prompt localization."""

from __future__ import annotations

from core.assistant_runtime import AssistantRuntime, RuntimeEventType, RuntimeMode
from core.critical_prompts import emergency_fallback_text
from core.speech.interfaces import LEGACY_PROVIDER_ID, SPEAKKIT_PROVIDER_ID, SpeechProviderProfile
from core.speech.provider_registry import ProviderBundle, ProviderRegistry
from core.speech.provider_resolver import NetworkProbeResult
from core.wake_word import WakeAction, WakeResult


def _event_collector():
    events = []

    def _observer(event) -> None:
        events.append(event)

    return events, _observer


class _ProviderService:
    def __init__(
        self,
        *,
        any_responses: list[str | None] | None = None,
        command_responses: list[str | None] | None = None,
        wake_responses: list[WakeResult] | None = None,
        available: bool = True,
    ) -> None:
        self._any_responses = list(any_responses or [])
        self._command_responses = list(command_responses or [])
        self._wake_responses = list(wake_responses or [])
        self._available = available
        self.spoken_texts: list[str] = []

    def is_available(self) -> bool:
        return self._available

    def detect(self, _text):
        if not self._wake_responses:
            return None
        return self._wake_responses.pop(0)

    def set_language(self, _language):
        return None

    def set_voice_gender(self, _gender):
        return None

    def set_speech_speed(self, _speed):
        return None

    def set_voice_profile(self, _voice):
        return None

    def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):
        if not self._any_responses:
            return None
        return self._any_responses.pop(0)

    def listen_command(self, *args, **kwargs):
        if not self._command_responses:
            return None
        return self._command_responses.pop(0)

    def configure(self, **_kwargs):
        return None

    def speak(self, text, **_kwargs):
        self.spoken_texts.append(text)
        return text


class _Probe:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = list(statuses)
        self._index = 0

    def probe(self, *, source: str = "background") -> NetworkProbeResult:
        status = self._statuses[min(self._index, len(self._statuses) - 1)]
        self._index += 1
        return NetworkProbeResult(
            source=source,
            target_label="prompt_probe",
            status=status,
            latency_ms=5,
            checked_at=float(self._index),
            failure_reason=None if status == "online" else "prompt_status",
        )


def _network_runtime_registry(*, command_responses: list[str | None]) -> tuple[ProviderRegistry, _ProviderService]:
    registry = ProviderRegistry()
    legacy_tts = _ProviderService()
    legacy = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=LEGACY_PROVIDER_ID, display_name="legacy", requires_network=True),
        wake_service=_ProviderService(),
        stt_service=_ProviderService(),
        tts_service=legacy_tts,
    )
    speakkit_tts = _ProviderService()
    speakkit = ProviderBundle(
        profile=SpeechProviderProfile(provider_id=SPEAKKIT_PROVIDER_ID, display_name="speakkit", requires_network=True),
        wake_service=_ProviderService(wake_responses=[WakeResult(action=WakeAction.START, phrase="مرحبا")]),
        stt_service=_ProviderService(any_responses=["مرحبا"], command_responses=command_responses),
        tts_service=speakkit_tts,
    )
    registry.register(legacy)
    registry.register(speakkit)
    return registry, speakkit_tts


def test_runtime_uses_catalog_backed_arabic_startup_and_offline_guidance(
    isolated_settings_manager,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {
            "username": "Tester",
            "language": "ar-EG",
            "speech_provider": SPEAKKIT_PROVIDER_ID,
            "network_available": False,
            "offline_allowlisted_capabilities": ["system_status"],
        },
        persist=False,
    )
    events, observer = _event_collector()
    dispatch = dispatch_spy_factory()
    registry, tts = _network_runtime_registry(command_responses=["start ocr", None])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        provider_registry_obj=registry,
        dispatcher=dispatch,
        network_probe=_Probe(["offline", "offline", "offline"]),
    )

    runtime.run_forever(max_cycles=3)

    assert not any(text == "المساعد جاهز." for text in tts.spoken_texts)
    assert any("لا يوجد اتصال" in text for text in tts.spoken_texts)
    assert not any("ط§ظ" in text for text in tts.spoken_texts)
    assert dispatch.calls == []

    critical_surfaces = {
        event.payload["critical_prompt_surface_id"]
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("critical_prompt_surface_id")
    }
    assert {"runtime.startup.degraded", "runtime.offline.safe_refusal"}.issubset(critical_surfaces)


def test_runtime_arabic_onboarding_prompts_are_readable_and_bound_to_catalog(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
    dispatch_spy_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "", "language": "ar-EG"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(
        any_responses=["مرحبا", "عربي", "أنثى", "1.0", "سارة", "نعم"],
        command_responses=[None],
    )
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="مرحبا")])
    dispatch = dispatch_spy_factory()

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=dispatch,
        network_probe=_Probe(["online", "online", "online"]),
    )

    runtime.run_forever(max_cycles=2)

    spoken = " ".join(tts.spoken_texts)
    assert "هذه أول مرة للتشغيل" in spoken
    assert "هل تفضل العربية أم الإنجليزية" in spoken
    assert "اختر نوع الصوت" in spoken
    assert "قل اسمك." in spoken
    assert "هل اسمك سارة" in spoken
    assert "ط§ظ" not in spoken

    catalog_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("critical_prompt_surface_id")
    ]
    assert any(payload["critical_prompt_surface_id"] == "runtime.onboarding.language" for payload in catalog_events)
    assert any(payload["critical_prompt_surface_id"] == "runtime.onboarding.name_confirm" for payload in catalog_events)


def test_runtime_emits_integrity_signal_when_interrupt_prompt_falls_back(
    isolated_settings_manager,
    listener_factory,
    tts_engine_factory,
    wake_detector_factory,
) -> None:
    isolated_settings_manager.apply_settings_snapshot(
        {"username": "Tester", "language": "ar-EG"},
        persist=False,
    )
    events, observer = _event_collector()
    listener = listener_factory(any_responses=["مرحبا"], command_responses=[None])
    tts = tts_engine_factory()
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="مرحبا")])

    runtime = AssistantRuntime(
        mode=RuntimeMode.CONSOLE,
        observer=observer,
        settings_manager_obj=isolated_settings_manager,
        listener_factory=lambda default_language: listener,
        tts_engine_factory=lambda: tts,
        wake_detector_factory=lambda: wake,
        dispatcher=lambda _text: None,
        network_probe=_Probe(["online", "online"]),
    )

    runtime._initialize_runtime()
    isolated_settings_manager._critical_prompt_catalog["interrupt_stop"]["ar"] = ""
    isolated_settings_manager._repaired_prompt_keys = set()
    runtime._handle_interrupt_signal("stop")

    assert emergency_fallback_text("interrupt_stop", "ar-EG") in tts.spoken_texts
    critical_events = [
        event.payload
        for event in events
        if event.type == RuntimeEventType.SYSTEM and event.payload.get("critical_prompt_surface_id") == "runtime.interrupt.stop"
    ]
    assert critical_events
    assert critical_events[-1]["integrity_status"] == "fallback_used"


def test_resolver_clarification_surfaces_stay_localized_and_catalog_backed(
    isolated_settings_manager,
) -> None:
    isolated_settings_manager.apply_settings_snapshot({"language": "en-US"}, persist=False)
    en_language = isolated_settings_manager.resolve_critical_surface("resolver.clarification.language.required")
    en_voice = isolated_settings_manager.resolve_critical_surface("resolver.clarification.voice.required")
    en_failed = isolated_settings_manager.resolve_critical_surface("resolver.clarification.failed")

    assert en_language["prompt_key"] == "clarification_language_required"
    assert en_voice["prompt_key"] == "clarification_voice_required"
    assert en_failed["prompt_key"] == "clarification_failed"
    assert "Arabic or English" in en_language["text"]
    assert "male or female" in en_voice["text"]

    isolated_settings_manager.apply_settings_snapshot({"language": "ar-EG"}, persist=False)
    ar_language = isolated_settings_manager.resolve_critical_surface("resolver.clarification.language.required")
    ar_voice = isolated_settings_manager.resolve_critical_surface("resolver.clarification.voice.required")
    ar_failed = isolated_settings_manager.resolve_critical_surface("resolver.clarification.failed")

    assert ar_language["language"].startswith("ar")
    assert ar_voice["language"].startswith("ar")
    assert ar_failed["language"].startswith("ar")
    assert "ط·آ§ط¸" not in ar_language["text"]
    assert "ط·آ§ط¸" not in ar_voice["text"]
    assert "ط·آ§ط¸" not in ar_failed["text"]
