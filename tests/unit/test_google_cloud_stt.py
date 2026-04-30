"""Unit coverage for Google Cloud STT foundation behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.speech.google_cloud_stt import GoogleCloudSTTRecognizer


class _Audio:
    def get_raw_data(self, *, convert_rate: int, convert_width: int) -> bytes:  # noqa: ARG002
        return b"\x00\x01\x02\x03"


class _Client:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def recognize(self, *, request, timeout):  # noqa: ARG002
        self.calls += 1
        if not self._responses:
            return {}
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _with_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    creds = tmp_path / "fake-google-creds.json"
    creds.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))


def test_availability_is_startup_safe_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    recognizer = GoogleCloudSTTRecognizer(client_factory=lambda: _Client([{}]))
    state = recognizer.availability_state()
    assert state["availability"] == "unavailable"
    assert state["reason_code"] == "cloud_credentials_missing"
    assert state["startup_safe"] is True


def test_recognize_short_utterance_parses_transcript_alternatives_and_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _with_credentials(monkeypatch, tmp_path)
    client = _Client(
        [
            {
                "alternatives": [
                    {"transcript": "start obstacle detection", "confidence": 0.91},
                    {"transcript": "start obstacles"},
                ],
                "detected_language": "en-US",
            }
        ]
    )
    recognizer = GoogleCloudSTTRecognizer(client_factory=lambda: client)
    candidate = recognizer.recognize_short_utterance(
        audio=_Audio(),
        selected_language="en-US",
        phrase_hints=("start obstacle detection",),
    )
    assert candidate.status == "recognized"
    assert candidate.primary_transcript == "start obstacle detection"
    assert candidate.alternative_transcripts == ("start obstacle detection", "start obstacles")
    assert candidate.confidence_available is True
    assert candidate.confidence_score == pytest.approx(0.91)
    assert candidate.selected_language == "en-US"
    assert candidate.detected_language == "en-US"


def test_recognize_short_utterance_retries_once_for_transient_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _with_credentials(monkeypatch, tmp_path)
    client = _Client(
        [
            TimeoutError("timeout"),
            {"alternatives": [{"transcript": "read text", "confidence": 0.8}]},
        ]
    )
    recognizer = GoogleCloudSTTRecognizer(client_factory=lambda: client)
    candidate = recognizer.recognize_short_utterance(
        audio=_Audio(),
        selected_language="en-US",
        phrase_hints=("read text",),
    )
    assert client.calls == 2
    assert candidate.status == "recognized"
    assert candidate.primary_transcript == "read text"


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (TimeoutError("deadline exceeded"), "cloud_network_timeout"),
        (RuntimeError("permission denied"), "cloud_auth_error"),
        (RuntimeError("quota exceeded"), "cloud_quota_error"),
        (RuntimeError("service unavailable"), "cloud_service_unavailable"),
        (RuntimeError("unexpected"), "cloud_unknown_failure"),
    ],
)
def test_recognize_short_utterance_maps_failure_reason_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: Exception,
    expected_reason: str,
) -> None:
    _with_credentials(monkeypatch, tmp_path)
    recognizer = GoogleCloudSTTRecognizer(client_factory=lambda: _Client([error, error]))
    candidate = recognizer.recognize_short_utterance(
        audio=_Audio(),
        selected_language="en-US",
        phrase_hints=("test",),
    )
    assert candidate.status == "failed"
    assert candidate.failure_reason_code == expected_reason


def test_recognize_short_utterance_maps_empty_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _with_credentials(monkeypatch, tmp_path)
    recognizer = GoogleCloudSTTRecognizer(client_factory=lambda: _Client([{}]))
    candidate = recognizer.recognize_short_utterance(
        audio=_Audio(),
        selected_language="en-US",
        phrase_hints=("anything",),
    )
    assert candidate.status == "empty_result"
    assert candidate.failure_reason_code == "cloud_empty_result"
