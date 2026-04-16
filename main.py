"""Application entry point."""

import argparse
import logging

from ui.gui_app import run_gui
from core.dispatcher import dispatch
from core.stt import VoiceListener
from settings.settings_manager import settings_manager
from tts.tts_engine import TTSEngine

logging.basicConfig( 
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_console() -> None:
    logging.info("[MAIN] Console mode started. Press Ctrl+C to exit.")
    listener = VoiceListener(default_language=settings_manager.language)
    settings_manager.attach_listener(listener)
    tts_engine = TTSEngine()
    settings_manager.attach_tts_engine(tts_engine)

    settings_manager.speak_localized("تم تشغيل المساعد الصوتي", "Voice assistant is now online")

    try:
        while True:
            recognized_text = listener.listen_command()
            if not recognized_text:
                continue
            dispatch(recognized_text)
    except KeyboardInterrupt:
        logging.info("[MAIN] Exiting...")
        settings_manager.speak_localized("أغلق الآن، إلى اللقاء", "Shutting down, talk soon")


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
