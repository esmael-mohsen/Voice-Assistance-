import logging
import time

import speech_recognition as sr

logger = logging.getLogger(__name__)


class VoiceListener:
    def __init__(self, default_language="en-US", retries=2):
        self.recognizer = sr.Recognizer()
        # Better UX defaults for conversational commands
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.4
        self.language = default_language
        self.retries = retries
        self.last_error = None

    def set_language(self, language_code):
        """تغيير لغة الاستماع أثناء التشغيل"""
        if not language_code:
            logger.warning("[STT] Missing language_code, keeping %s", self.language)
            return
        self.language = language_code
        logger.info("[STT] Language set to: %s", self.language)

    def get_language(self):
        return self.language

    def listen(self, prompt="[STT] Listening..."):
        """Listen for speech input with retries and logging."""
        for attempt in range(1, self.retries + 2):
            try:
                audio = self.listen_audio(prompt=f"{prompt} (attempt {attempt})")
                if audio is None:
                    time.sleep(0.5)
                    continue

                text = self.recognize_audio(audio, language_code=self.language)
                if not text:
                    time.sleep(0.5)
                    continue
                logger.info("[STT] Recognized: %s", text)
                self.last_error = None
                return text

            except sr.UnknownValueError:
                self.last_error = "unknown_value"
                logger.warning("[STT] Could not understand audio (Attempt %s)", attempt)
            except sr.RequestError as err:
                self.last_error = f"request_error:{err}"
                logger.error("[STT] Request failed; %s (Attempt %s)", err, attempt)
            except sr.WaitTimeoutError:
                self.last_error = "timeout"
                logger.warning("[STT] No speech detected (Attempt %s)", attempt)

            time.sleep(0.5)  # Small delay before retry

        logger.error("[STT] Failed to recognize speech after retries")
        return None

    def listen_audio(self, prompt="[STT] Listening...", timeout=7, phrase_time_limit=10):
        """Capture audio once from the microphone."""
        try:
            with sr.Microphone() as source:
                logger.info("%s", prompt)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                return self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            self.last_error = "timeout"
            logger.warning("[STT] No speech detected")
            return None

    def recognize_audio(self, audio, language_code: str):
        """Recognize previously captured audio using a specific language."""
        try:
            return self.recognizer.recognize_google(audio, language=language_code)
        except sr.UnknownValueError:
            self.last_error = "unknown_value"
            return None
        except sr.RequestError as err:
            self.last_error = f"request_error:{err}"
            logger.error("[STT] Request failed; %s", err)
            return None

    def listen_any(self, languages, prompt="[STT] Listening...", timeout=7, phrase_time_limit=10):
        """Listen once and try recognition with multiple language codes."""
        audio = self.listen_audio(prompt=prompt, timeout=timeout, phrase_time_limit=phrase_time_limit)
        if audio is None:
            return None

        for lang in languages:
            text = self.recognize_audio(audio, language_code=lang)
            if text:
                logger.info("[STT] Recognized (%s): %s", lang, text)
                return text
        logger.warning("[STT] Could not recognize audio in any provided language")
        return None

    def listen_command(self):
        """Capture and normalize a single command phrase."""
        text = self.listen()
        return text.strip() if text else None


if __name__ == "__main__":
    listener = VoiceListener(default_language="ar-EG")  # افتراضي عربي
    while True:
        command_text = listener.listen_command()
        if command_text:
            logger.info("[MAIN] Command to Dispatcher: %s", command_text)
