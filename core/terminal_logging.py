"""Terminal logging setup for readable voice-runtime diagnostics."""

from __future__ import annotations

import ast
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, TextIO

_PREFIX_RE = re.compile(r"^\[(?P<scope>[A-Z][A-Z0-9_ -]*)(?:\]\[[A-Z][A-Z0-9_ -]*)?\]")
_RUNTIME_EVENT_RE = re.compile(
    r"^\[RUNTIME\] event=(?P<event>[a-z_]+) session=(?P<session>[^ ]+) mode=(?P<mode>[^ ]+)"
    r"(?: state=(?P<state>[^ ]+))?"
)
_PAYLOAD_MARKER = " payload="

_SCOPE_BY_LOGGER_PREFIX: tuple[tuple[str, str], ...] = (
    ("core.stt", "STT"),
    ("core.speech.legacy_wake", "WAKE"),
    ("core.wake_word", "WAKE"),
    ("core.assistant_runtime", "RUNTIME"),
    ("settings.", "SETTINGS"),
    ("tts.", "TTS"),
    ("ui.", "GUI"),
)

_LEVEL_COLORS: dict[int, str] = {
    logging.DEBUG: "\x1b[2;37m",
    logging.INFO: "\x1b[37m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}

_SCOPE_COLORS: dict[str, str] = {
    "WAKE": "\x1b[1;96m",
    "STT": "\x1b[1;92m",
    "RUNTIME": "\x1b[1;94m",
    "TTS": "\x1b[1;95m",
    "SETTINGS": "\x1b[1;97m",
    "GUI": "\x1b[1;93m",
    "CONSOLE": "\x1b[1;93m",
    "MAIN": "\x1b[1;93m",
}

_RESET = "\x1b[0m"


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on", "full", "verbose"}


def _stream_supports_color(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except Exception:  # noqa: BLE001
        return False


def _scope_for_record(record: logging.LogRecord, rendered_message: str) -> str:
    match = _PREFIX_RE.match(rendered_message)
    if match is not None:
        return match.group("scope").split()[0].strip()[:10] or "APP"
    logger_name = str(record.name or "")
    for prefix, scope in _SCOPE_BY_LOGGER_PREFIX:
        if logger_name.startswith(prefix):
            return scope
    if logger_name == "root":
        return "APP"
    return logger_name.rsplit(".", 1)[-1].upper()[:10] or "APP"


def _short(value: Any, *, limit: int = 96) -> str:
    text = str(value if value is not None else "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}..."


def _quote(value: Any, *, limit: int = 96) -> str:
    return f'"{_short(value, limit=limit)}"'


def _ms(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{int(float(value))}ms"
    except (TypeError, ValueError):
        return str(value)


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _append(parts: list[str], name: str, value: Any, *, quote: bool = False, limit: int = 96) -> None:
    if value is None or value == "":
        return
    rendered = _quote(value, limit=limit) if quote else _short(value, limit=limit)
    parts.append(f"{name}={rendered}")


def _compact_runtime_payload(event: str, payload: dict[str, Any]) -> str | None:
    if "command_recognition_telemetry" in payload:
        telemetry = payload.get("command_recognition_telemetry") or {}
        parts = ["[RUNTIME][RECOGNITION]"]
        _append(parts, "outcome", telemetry.get("decision_outcome"))
        _append(parts, "band", telemetry.get("confidence_band"))
        _append(parts, "path", telemetry.get("recognition_path"))
        parts.append(f"fallback={_bool_text(telemetry.get('fallback_used'))}")
        _append(parts, "latency", _ms(telemetry.get("latency_ms")))
        _append(parts, "profile", telemetry.get("profile_id"))
        _append(parts, "vocab", telemetry.get("closed_vocabulary_id"))
        return " ".join(parts)

    if "command_result" in payload:
        result = payload.get("command_result") or {}
        metadata = result.get("metadata") if isinstance(result, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        parts = ["[RUNTIME][RESULT]"]
        _append(parts, "intent", payload.get("intent_id") or result.get("intent_id"))
        _append(parts, "status", payload.get("status") or result.get("status"))
        _append(parts, "duration", _ms(payload.get("dispatch_duration_ms") or metadata.get("dispatch_duration_ms")))
        _append(parts, "canonical", payload.get("canonical_command_text") or metadata.get("canonical_command_text"), quote=True)
        _append(parts, "text", result.get("spoken_text"), quote=True)
        return " ".join(parts)

    if "guided_dialog_outcome" in payload:
        outcome = payload.get("guided_dialog_outcome") or {}
        nested = outcome.get("payload") if isinstance(outcome, dict) else {}
        if not isinstance(nested, dict):
            nested = {}
        parts = ["[RUNTIME][DIALOG]"]
        _append(parts, "status", outcome.get("status"))
        _append(parts, "error", outcome.get("error_code"))
        _append(parts, "next", outcome.get("next_runtime_state"))
        _append(parts, "option", nested.get("accepted_option_id"))
        _append(parts, "retry", nested.get("retry_count"))
        _append(parts, "text", outcome.get("spoken_text"), quote=True)
        return " ".join(parts)

    if "turn_taking_window" in payload:
        window = payload.get("turn_taking_window") or {}
        nested = window.get("payload") if isinstance(window, dict) else {}
        if not isinstance(nested, dict):
            nested = {}
        parts = ["[RUNTIME][TURN]"]
        _append(parts, "status", window.get("status"))
        _append(parts, "surface", window.get("prompt_surface_id"))
        _append(parts, "class", window.get("prompt_class"))
        _append(parts, "vocab", window.get("closed_vocabulary_id"))
        _append(parts, "next", window.get("next_runtime_state"))
        _append(parts, "retry", nested.get("retry_count"))
        return " ".join(parts)

    if payload.get("trigger") == "wake_policy":
        parts = ["[RUNTIME][WAKE]"]
        _append(parts, "status", payload.get("status"))
        _append(parts, "mode", payload.get("selected_wake_mode"))
        _append(parts, "source", payload.get("source_classification"))
        _append(parts, "alias", payload.get("canonical_wake_alias"), quote=True)
        parts.append(f"suffix={_bool_text(payload.get('command_suffix_ignored'))}")
        _append(parts, "error", payload.get("error_code"))
        _append(parts, "next", payload.get("next_state") or payload.get("next_runtime_state"))
        return " ".join(parts)

    if payload.get("flow") == "command" or payload.get("event_category") == "offline_policy":
        parts = ["[RUNTIME][OFFLINE]"]
        _append(parts, "decision", payload.get("decision") or payload.get("status_or_decision"))
        _append(parts, "capability", payload.get("capability_id"))
        _append(parts, "provider", payload.get("provider_id"))
        _append(parts, "network", payload.get("effective_network_available"))
        _append(parts, "next", payload.get("next_state"))
        return " ".join(parts)

    if payload.get("status") == "recovered" or payload.get("recovery_trigger"):
        parts = ["[RUNTIME][RECOVERY]"]
        _append(parts, "status", payload.get("status"))
        _append(parts, "error", payload.get("error_code"))
        _append(parts, "duration", _ms(payload.get("duration_ms")))
        _append(parts, "next", payload.get("next_state"))
        _append(parts, "text", payload.get("spoken_text"), quote=True)
        return " ".join(parts)

    if "connectivity_probe_status" in payload:
        parts = ["[RUNTIME][NET]"]
        _append(parts, "source", payload.get("connectivity_probe_source"))
        _append(parts, "status", payload.get("connectivity_probe_status"))
        _append(parts, "latency", _ms(payload.get("connectivity_probe_latency_ms")))
        _append(parts, "effective", payload.get("effective_network_available"))
        _append(parts, "reason", payload.get("connectivity_probe_failure_reason"))
        return " ".join(parts)

    if "wake_mode" in payload:
        parts = ["[RUNTIME][WAKE_POLICY]"]
        _append(parts, "mode", payload.get("wake_mode"))
        _append(parts, "fallback", payload.get("wake_fallback_mode"))
        _append(parts, "dev", payload.get("wake_dev_fallback_mode"))
        _append(parts, "source", payload.get("selection_source"))
        _append(parts, "degraded", payload.get("degraded_mode"))
        _append(parts, "reason", payload.get("wake_fallback_reason") or payload.get("degraded_reason"))
        return " ".join(parts)

    if event == "config" or {"language", "gender", "speech_provider"}.issubset(payload.keys()):
        parts = ["[RUNTIME][CONFIG]"]
        _append(parts, "lang", payload.get("language"))
        _append(parts, "gender", payload.get("gender"))
        _append(parts, "speed", payload.get("speed"))
        _append(parts, "provider", payload.get("speech_provider") or payload.get("provider_id"))
        _append(parts, "wake", payload.get("wake_primary_mode"))
        _append(parts, "rollout", payload.get("stt_rollout_effective_mode"))
        _append(parts, "cloud", payload.get("stt_cloud_primary_enabled"))
        _append(parts, "next", payload.get("next_state"))
        return " ".join(parts)

    if "critical_prompt_surface_id" in payload:
        parts = ["[RUNTIME][PROMPT]"]
        _append(parts, "surface", payload.get("critical_prompt_surface_id"))
        _append(parts, "key", payload.get("prompt_key"))
        _append(parts, "lang", payload.get("language"))
        _append(parts, "integrity", payload.get("integrity_status"))
        return " ".join(parts)

    if "startup_status" in payload:
        parts = ["[RUNTIME][STARTUP]"]
        _append(parts, "status", payload.get("startup_status"))
        _append(parts, "latency", _ms(payload.get("startup_latency_ms")))
        _append(parts, "provider", payload.get("provider_id"))
        _append(parts, "network", payload.get("effective_network_available"))
        return " ".join(parts)

    if "cue_id" in payload:
        return f"[RUNTIME][CUE] id={payload.get('cue_id')} state={payload.get('cue_state')}"

    if event == "user":
        parts = ["[RUNTIME][USER]"]
        _append(parts, "text", payload.get("text"), quote=True)
        _append(parts, "path", payload.get("recognition_path"))
        _append(parts, "profile", payload.get("profile_id"))
        return " ".join(parts)

    if "text" in payload:
        label = "ASSISTANT" if event == "assistant" else "TEXT"
        parts = [f"[RUNTIME][{label}]"]
        _append(parts, "text", payload.get("text"), quote=True)
        _append(parts, "priority", payload.get("priority"))
        return " ".join(parts)

    if payload:
        keys = ",".join(sorted(str(key) for key in payload.keys())[:8])
        return f"[RUNTIME][{event.upper()}] keys={keys}"
    return None


def _compact_runtime_message(message: str) -> str:
    match = _RUNTIME_EVENT_RE.match(message)
    if match is None:
        return message
    event = match.group("event")
    state = match.group("state")
    if state:
        return f"[RUNTIME][STATE] state={state}"
    if _PAYLOAD_MARKER not in message:
        return message
    payload_text = message.split(_PAYLOAD_MARKER, 1)[1].strip()
    if not payload_text.startswith("{"):
        return message
    try:
        payload = ast.literal_eval(payload_text)
    except (SyntaxError, ValueError):
        return message
    if not isinstance(payload, dict):
        return message
    return _compact_runtime_payload(event, payload) or message


class VoiceAssistantFormatter(logging.Formatter):
    """Compact, aligned formatter tuned for speech-loop debugging."""

    default_msec_format = "%s.%03d"

    def __init__(self, *, use_color: bool = False, compact_payloads: bool = True) -> None:
        super().__init__()
        self.use_color = bool(use_color)
        self.compact_payloads = bool(compact_payloads) and not _env_truthy("EGB_LOG_FULL_PAYLOADS")

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        created = datetime.fromtimestamp(record.created)
        if datefmt:
            return created.strftime(datefmt)
        return f"{created:%H:%M:%S}.{int(record.msecs):03d}"

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.compact_payloads:
            message = _compact_runtime_message(message)
        scope = _scope_for_record(record, message)
        timestamp = self.formatTime(record)
        level = record.levelname.ljust(7)
        scope_text = scope.ljust(10)
        if self.use_color:
            level_color = _LEVEL_COLORS.get(record.levelno, "")
            scope_color = _SCOPE_COLORS.get(scope, "")
            level = f"{level_color}{level}{_RESET}"
            scope_text = f"{scope_color}{scope_text}{_RESET}"
        line = f"{timestamp} | {level} | {scope_text} | {message}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def configure_terminal_logging(*, level: int = logging.INFO) -> None:
    """Configure root logging once with readable terminal output."""
    stream = sys.stderr
    handler = logging.StreamHandler(stream)
    handler.setFormatter(VoiceAssistantFormatter(use_color=_stream_supports_color(stream)))
    logging.basicConfig(level=level, handlers=[handler], force=True)
