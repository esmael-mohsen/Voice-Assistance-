"""Unit tests validating legacy adapter parity with existing components."""

from __future__ import annotations

import threading
import time

import core.stt as stt_module
from core.command_models import CommandRecognitionResult
from core.speech.legacy_stt import LegacySpeechToTextAdapter
from core.speech.legacy_tts import LegacyTextToSpeechAdapter
from core.speech.legacy_wake import LegacyWakeService
from core.stt import VoiceListener
from core.wake_word import WakeAction, WakeResult, WakeWordDetector


def test_legacy_stt_adapter_delegates_listener_calls(listener_factory) -> None:
    listener = listener_factory(any_responses=["hello"], command_responses=["run command"])
    adapter = LegacySpeechToTextAdapter(listener=listener, default_language="en-US")

    assert adapter.listen_any(["en-US"]) == "hello"
    assert adapter.listen_command() == "run command"
    adapter.set_language("ar-EG")
    assert listener.language == "ar-EG"


def test_legacy_stt_adapter_passes_multilingual_candidates_to_command_window() -> None:
    captured: dict[str, object] = {}

    class _Listener:
        def __init__(self) -> None:
            self.language = "ar-EG"

        def listen_command_window(self, **kwargs):
            captured.update(kwargs)
            return "done"

        def listen_command(self):
            return None

    adapter = LegacySpeechToTextAdapter(listener=_Listener(), default_language="ar-EG")
    result = adapter.listen_command(timeout=8, phrase_time_limit=6)
    assert result == "done"
    assert captured.get("languages") == ["ar-EG", "en-US"]


def test_legacy_tts_adapter_delegates_engine_calls(tts_engine_factory) -> None:
    engine = tts_engine_factory()
    adapter = LegacyTextToSpeechAdapter(tts_engine=engine)
    adapter.configure(language="en-US", gender="female", speed=1.1, voice_id="voice")
    adapter.set_language("en-US")
    adapter.set_voice_gender("female")
    adapter.set_speech_speed(1.2)
    adapter.speak("hello")

    assert engine.language == "en-US"
    assert engine.gender == "female"
    assert engine.speed == 1.2
    assert engine.spoken_texts[-1] == "hello"


def test_legacy_stt_adapter_request_stop_delegates_to_listener() -> None:
    class _Listener:
        def __init__(self) -> None:
            self.stop_calls = 0

        def listen_command(self):
            return None

        def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0):  # noqa: ARG002
            return None

        def set_language(self, _language_code):  # noqa: ARG002
            return None

        def request_stop(self) -> None:
            self.stop_calls += 1

    listener = _Listener()
    adapter = LegacySpeechToTextAdapter(listener=listener, default_language="en-US")
    adapter.request_stop()
    assert listener.stop_calls == 1


def test_legacy_tts_adapter_request_stop_delegates_to_engine() -> None:
    class _Engine:
        def __init__(self) -> None:
            self.stop_calls = 0

        def speak(self, _text):
            return None

        def set_language(self, _language_code):
            return None

        def set_voice_gender(self, _gender):
            return None

        def set_speech_speed(self, _speed):
            return None

        def request_stop(self) -> None:
            self.stop_calls += 1

    engine = _Engine()
    adapter = LegacyTextToSpeechAdapter(tts_engine=engine)
    adapter.request_stop()
    assert engine.stop_calls == 1


def test_legacy_wake_adapter_delegates_detection(wake_detector_factory) -> None:
    wake = wake_detector_factory(responses=[WakeResult(action=WakeAction.START, phrase="hi egb")])
    adapter = LegacyWakeService(detector=wake)
    result = adapter.detect("hi egb")
    assert result is not None
    assert result.action == WakeAction.START


def test_legacy_wake_wait_for_wake_uses_listener_phrase_fallback(listener_factory) -> None:
    listener = listener_factory(any_responses=["hi egb"])
    adapter = LegacyWakeService(
        detector=WakeWordDetector(),
        listener=listener,
    )
    result = adapter.wait_for_wake(timeout_s=1.0, wake_mode="keyword_low_power")
    assert result is not None
    assert result.action == WakeAction.START


def test_legacy_wake_wait_for_wake_uses_structured_listener_fallback_when_listen_any_misses() -> None:
    class _Listener:
        language = "en-US"

        def listen_any(self, _languages, prompt="", timeout=0, phrase_time_limit=0, interrupt_event=None):  # noqa: ARG002
            return None

        def listen_command_result(self, **_kwargs):
            return CommandRecognitionResult(
                session_id="wake-fallback-session",
                recognition_path="local_first",
                provider_id="legacy",
                primary_transcript="high e g b",
                confidence_score=0.72,
                confidence_available=True,
                alternative_transcripts=("high e g b",),
                detected_language="en-US",
                language_candidates=("en-US", "ar-EG"),
                latency_ms=120,
                error_code=None,
            )

    adapter = LegacyWakeService(
        detector=WakeWordDetector(),
        listener=_Listener(),
    )
    result = adapter.wait_for_wake(timeout_s=1.0, wake_mode="keyword_low_power")
    assert result is not None
    assert result.action == WakeAction.START


def test_legacy_wake_wait_for_wake_accepts_hardware_signal_supplier() -> None:
    signal_state = {"emitted": False}

    def _supplier():
        if signal_state["emitted"]:
            return None
        signal_state["emitted"] = True
        return True

    adapter = LegacyWakeService(
        detector=WakeWordDetector(),
        hardware_signal_supplier=_supplier,
    )
    result = adapter.wait_for_wake(timeout_s=0.2, wake_mode="hardware_trigger")
    assert result is not None
    assert result.action == WakeAction.START


def test_voice_listener_prefers_local_offline_recognition_before_cloud() -> None:
    class _Recognizer:
        def recognize_sphinx(self, _audio, language="en-US"):  # noqa: ARG002
            return "local result"

        def recognize_google(self, _audio, language="en-US"):  # noqa: ARG002
            raise AssertionError("cloud recognition should not be used when local succeeds")

    listener = VoiceListener(default_language="en-US", allow_cloud_fallback=False)
    listener.recognizer = _Recognizer()
    assert listener.recognize_audio(object(), "en-US") == "local result"


def test_voice_listener_uses_cloud_fallback_only_when_local_fails() -> None:
    class _Recognizer:
        def recognize_sphinx(self, _audio, language="en-US"):  # noqa: ARG002
            return ""

        def recognize_google(self, _audio, language="en-US"):  # noqa: ARG002
            return "cloud fallback"

    listener = VoiceListener(default_language="en-US", allow_cloud_fallback=True)
    listener.recognizer = _Recognizer()
    assert listener.recognize_audio(object(), "en-US") == "cloud fallback"


def test_voice_listener_cloud_preferred_mode_prioritizes_cloud_candidate() -> None:
    class _Recognizer:
        def recognize_sphinx(self, _audio, language="en-US"):  # noqa: ARG002
            return "local result"

        def recognize_google(self, _audio, language="en-US", show_all=False):  # noqa: ARG002
            if show_all:
                return {"alternative": [{"transcript": "cloud result", "confidence": 0.92}]}
            return "cloud result"

    listener = VoiceListener(default_language="en-US", prefer_offline=False, allow_cloud_fallback=True)
    listener.recognizer = _Recognizer()
    assert listener.recognize_audio(object(), "en-US") == "cloud result"


def test_voice_listener_clipped_command_triggers_followup_relisten() -> None:
    listener = VoiceListener(default_language="en-US", retries=1)
    listener._command_followup_relisten_gap_s = 0.0
    calls = {"listen_audio": 0}

    def _fake_listen_audio(*args, **kwargs):  # noqa: ANN002, ANN003
        calls["listen_audio"] += 1
        return object()

    captures = [
        ("switch to", "en-US", ("switch to", "switch to english"), 0.44),
        ("switch to english", "en-US", ("switch to english",), 0.9),
    ]

    def _fake_recognize_candidates(*args, **kwargs):  # noqa: ANN002, ANN003
        return captures.pop(0)

    listener.listen_audio = _fake_listen_audio  # type: ignore[method-assign]
    listener._recognize_candidates = _fake_recognize_candidates  # type: ignore[method-assign]
    result = listener.listen_command_result(
        timeout_s=4,
        phrase_time_limit_s=4,
        session_id="session-clipped",
    )

    assert result is not None
    assert result.error_code is None
    assert result.primary_transcript == "switch to english"
    assert calls["listen_audio"] == 2


def test_voice_listener_clear_command_does_not_relisten() -> None:
    listener = VoiceListener(default_language="en-US", retries=1)
    calls = {"listen_audio": 0}

    def _fake_listen_audio(*args, **kwargs):  # noqa: ANN002, ANN003
        calls["listen_audio"] += 1
        return object()

    def _fake_recognize_candidates(*args, **kwargs):  # noqa: ANN002, ANN003
        return ("start obstacle detection", "en-US", ("start obstacle detection",), 0.93)

    listener.listen_audio = _fake_listen_audio  # type: ignore[method-assign]
    listener._recognize_candidates = _fake_recognize_candidates  # type: ignore[method-assign]
    result = listener.listen_command_result(
        timeout_s=4,
        phrase_time_limit_s=4,
        session_id="session-clear",
    )

    assert result is not None
    assert result.error_code is None
    assert result.primary_transcript == "start obstacle detection"
    assert calls["listen_audio"] == 1


def test_voice_listener_cancellation_serializes_microphone_reads(monkeypatch) -> None:
    listener = VoiceListener(default_language="en-US", retries=1)

    class _FakeStream:
        def stop_stream(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _FakeMicrophone:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self.stream = _FakeStream()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001, ANN002, ANN003
            return None

    started_first_read = threading.Event()
    release_first_read = threading.Event()
    lock = threading.Lock()
    active_reads = 0
    max_active_reads = 0
    call_count = 0

    class _FakeRecognizer:
        def adjust_for_ambient_noise(self, source, duration=0.35):  # noqa: ARG002
            return None

        def listen(self, source, timeout=7, phrase_time_limit=10):  # noqa: ARG002
            nonlocal active_reads, max_active_reads, call_count
            with lock:
                call_count += 1
                active_reads += 1
                max_active_reads = max(max_active_reads, active_reads)
                current_call = call_count

            if current_call == 1:
                started_first_read.set()
                release_first_read.wait(timeout=2.0)

            with lock:
                active_reads -= 1

            raise stt_module.sr.WaitTimeoutError("timeout")

    listener.recognizer = _FakeRecognizer()
    monkeypatch.setattr(stt_module.sr, "Microphone", _FakeMicrophone)

    interrupt_event = threading.Event()
    results: dict[str, object] = {}

    def _first_call() -> None:
        results["first"] = listener.listen_audio(
            timeout=1,
            phrase_time_limit=1,
            interrupt_event=interrupt_event,
            hard_timeout_s=0.1,
        )

    def _second_call() -> None:
        results["second"] = listener.listen_audio(
            timeout=1,
            phrase_time_limit=1,
            hard_timeout_s=0.3,
        )

    first_worker = threading.Thread(target=_first_call)
    second_worker = threading.Thread(target=_second_call)
    first_worker.start()

    assert started_first_read.wait(timeout=1.0)
    interrupt_event.set()
    second_worker.start()
    time.sleep(0.08)
    with lock:
        assert call_count == 1

    release_first_read.set()
    first_worker.join(timeout=2.0)
    second_worker.join(timeout=2.0)

    assert not first_worker.is_alive()
    assert not second_worker.is_alive()
    assert max_active_reads == 1
    assert results["first"] is None
    assert results["second"] is None


def test_voice_listener_command_path_prefers_vosk_candidates_when_enabled() -> None:
    listener = VoiceListener(default_language="en-US")
    listener._stt_engine_preference = "vosk"
    listener._command_vosk_only = True
    listener._recognize_vosk_candidates = (  # type: ignore[method-assign]
        lambda audio, language_code, for_command=False, closed_vocabulary_choices=None: [  # noqa: ARG005
            ("start obstacle detection", 0.86)
        ]
    )
    listener._recognize_sphinx_candidate = lambda audio, language_code: "local fallback"  # type: ignore[method-assign]
    listener._recognize_google_candidates = lambda audio, language_code: [("cloud fallback", 0.92)]  # type: ignore[method-assign]

    candidates = listener._recognize_audio_candidates(  # noqa: SLF001
        object(),
        language_code="en-US",
        for_command=True,
    )

    assert candidates
    assert candidates[0][0] == "start obstacle detection"
    assert candidates[0][2] == "local_vosk"
    assert len(candidates) == 1


def test_voice_listener_vad_profile_marks_boundary_clipping() -> None:
    listener = VoiceListener(default_language="en-US")

    class _FakeVad:
        def is_speech(self, frame: bytes, sample_rate: int) -> bool:  # noqa: ARG002
            return bool(frame and frame[0] == 1)

    class _FakeAudio:
        def __init__(self, raw_bytes: bytes) -> None:
            self._raw_bytes = raw_bytes

        def get_raw_data(self, convert_rate=16000, convert_width=2):  # noqa: ARG002
            return self._raw_bytes

    listener._vad = _FakeVad()
    frame_size = int(listener._vad_sample_rate_hz * (listener._vad_frame_ms / 1000.0) * 2)
    speech_frame = bytes([1]) + bytes(frame_size - 1)
    silence_frame = bytes(frame_size)
    # Immediate speech start with very short trailing silence => likely clipped boundaries.
    raw_audio = (speech_frame * 6) + (silence_frame * 1)
    profile = listener._analyze_vad_profile(_FakeAudio(raw_audio))  # noqa: SLF001

    assert profile is not None
    assert profile["speech_ratio"] > 0.5
    assert profile["leading_silence_ms"] == 0
    assert profile["boundary_clipped"] is True
