"""Unit coverage for readable terminal log compaction."""

from __future__ import annotations

import logging

from core.terminal_logging import VoiceAssistantFormatter


def _format(message: str) -> str:
    record = logging.LogRecord(
        name="core.assistant_runtime",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    return VoiceAssistantFormatter(use_color=False).format(record)


def test_runtime_command_result_payload_is_compacted() -> None:
    line = _format(
        "[RUNTIME] event=system session=abc123 mode=gui payload="
        "{'command_result': {'status': 'success', 'spoken_text': 'Done.', 'intent_id': 'set_voice_gender', "
        "'metadata': {'canonical_command_text': 'switch to female voice', 'dispatch_duration_ms': 4587}}, "
        "'dispatch_duration_ms': 4587, 'intent_id': 'set_voice_gender', 'status': 'success', "
        "'canonical_command_text': 'switch to female voice'}"
    )

    assert "[RUNTIME][RESULT]" in line
    assert "intent=set_voice_gender" in line
    assert 'canonical="switch to female voice"' in line
    assert "payload={" not in line


def test_runtime_recognition_payload_is_compacted() -> None:
    line = _format(
        "[RUNTIME] event=system session=abc123 mode=gui payload="
        "{'command_recognition_telemetry': {'recognition_path': 'local_first', 'confidence_band': 'high', "
        "'fallback_used': False, 'decision_outcome': 'execute', 'latency_ms': 4233, "
        "'profile_id': 'command.default'}}"
    )

    assert "[RUNTIME][RECOGNITION]" in line
    assert "outcome=execute" in line
    assert "latency=4233ms" in line
    assert "payload={" not in line


def test_full_payload_env_keeps_original_runtime_payload(monkeypatch) -> None:
    monkeypatch.setenv("EGB_LOG_FULL_PAYLOADS", "1")
    record = logging.LogRecord(
        name="core.assistant_runtime",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="[RUNTIME] event=assistant session=abc123 mode=gui payload={'text': 'Assistant ready.'}",
        args=(),
        exc_info=None,
    )

    line = VoiceAssistantFormatter(use_color=False).format(record)

    assert "payload={'text': 'Assistant ready.'}" in line
