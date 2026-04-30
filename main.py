"""Application entry point."""

import argparse
import logging

from core.assistant_runtime import (
    AssistantRuntime,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeMode,
    canonical_runtime_state,
)
from core.terminal_logging import configure_terminal_logging
from ui.gui_app import run_gui

configure_terminal_logging(level=logging.INFO)


def _console_observer(event: RuntimeEvent) -> None:
    if event.type == RuntimeEventType.STATUS:
        canonical_state_raw = event.payload.get("state", "unknown")
        compatibility_raw = event.payload.get("raw_state", canonical_state_raw)
        try:
            canonical_state = canonical_runtime_state(canonical_state_raw).value
        except Exception:
            canonical_state = str(canonical_state_raw)

        raw_state = str(compatibility_raw)
        if raw_state != canonical_state:
            logging.info("[CONSOLE][status] %s (raw=%s)", canonical_state, raw_state)
        else:
            logging.info("[CONSOLE][status] %s", canonical_state)
        return
    if event.type in (RuntimeEventType.SYSTEM, RuntimeEventType.ASSISTANT):
        text = event.payload.get("text", "")
        if text:
            logging.info("[CONSOLE][%s] %s", event.type.value, text)
        return
    if event.type == RuntimeEventType.USER:
        logging.info("[CONSOLE][user] %s", event.payload.get("text", ""))
        return
    if event.type == RuntimeEventType.ERROR:
        logging.error(
            "[CONSOLE][error] %s | provider=%s stage=%s recoverable=%s fallback=%s next=%s",
            event.payload.get("message", ""),
            event.payload.get("provider"),
            event.payload.get("stage"),
            event.payload.get("recoverable"),
            event.payload.get("fallback_to"),
            event.payload.get("next_state"),
        )
        return
    if event.type == RuntimeEventType.CONFIG:
        logging.info(
            "[CONSOLE][config] lang=%s gender=%s speed=%s provider=%s persisted=%s degraded=%s",
            event.payload.get("language"),
            event.payload.get("gender"),
            event.payload.get("speed"),
            event.payload.get("speech_provider"),
            event.payload.get("persisted_speech_provider"),
            bool(event.payload.get("degraded_mode", False)),
        )


def run_console() -> None:
    logging.info("[MAIN] Console mode started. Press Ctrl+C to exit.")
    runtime = AssistantRuntime(mode=RuntimeMode.CONSOLE, observer=_console_observer)

    try:
        runtime.run_forever()
    except KeyboardInterrupt:
        logging.info("[MAIN] Exiting...")
        runtime.request_stop()
    finally:
        runtime.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice assistant")
    parser.add_argument("--console", action="store_true", help="Run without GUI")
    args = parser.parse_args()

    if args.console:
        run_console()
    else:
        run_gui()


if __name__ == "__main__":
    main()
