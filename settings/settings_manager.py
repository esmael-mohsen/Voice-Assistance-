"""Centralized runtime settings for STT and TTS layers."""

import logging
from typing import Optional

from settings.profile_store import UserProfile, load_profile, save_profile

logger = logging.getLogger(__name__)


class SettingsManager:
    def __init__(self):
        self.username = ""
        self.language = "ar-EG"
        self.voice_gender = "female"
        self.default_speech_speed = 1.0
        self.speech_speed = self.default_speech_speed
        self.min_speech_speed = 0.6
        self.max_speech_speed = 1.6
        self._listener = None
        self._tts_engine = None
        self._voice_profiles = {
            ("ar-EG", "female"): "ar-EG-SalmaNeural",
            ("ar-EG", "male"): "ar-EG-ShakirNeural",
            # More human-sounding defaults
            ("en-US", "female"): "en-US-EmmaMultilingualNeural",
            ("en-US", "male"): "en-US-AndrewMultilingualNeural",
        }
        self._default_voice = "en-US-EmmaNeural"
        self._profile_loaded = False

    def load_user_profile(self) -> bool:
        """Load persisted profile if present. Returns True when loaded."""
        if self._profile_loaded:
            return bool(self.username)

        profile = load_profile()
        self._profile_loaded = True
        if not profile:
            return False

        if profile.username:
            self.username = profile.username
        if profile.language:
            self.language = profile.language
        if profile.voice_gender:
            self.voice_gender = profile.voice_gender
        if profile.speech_speed:
            self.speech_speed = profile.speech_speed

        logger.info("[SETTINGS] Loaded user profile (%s)", self.username or "no-name")
        return True

    def is_configured(self) -> bool:
        # First-run setup considered complete when a username exists.
        return bool(self.username)

    def _persist_profile(self) -> None:
        try:
            save_profile(
                UserProfile(
                    username=self.username,
                    language=self.language,
                    voice_gender=self.voice_gender,
                    speech_speed=self.speech_speed,
                )
            )
        except Exception:  # noqa: BLE001
            logger.exception("[SETTINGS] Failed to persist profile")

    def set_username(self, username: str):
        username = (username or "").strip()
        if not username:
            logger.warning("[SETTINGS] Missing username")
            return self.username
        self.username = username
        self._persist_profile()
        return self.username

    def attach_listener(self, listener):
        self._listener = listener
        self._listener.set_language(self.language)
        logger.info("[SETTINGS] Listener attached with language %s", self.language)

    def attach_tts_engine(self, tts_engine):
        self._tts_engine = tts_engine
        self._tts_engine.configure(
            language=self.language,
            gender=self.voice_gender,
            speed=self.speech_speed,
            voice_id=self._current_voice_id(),
            pitch="+0Hz",
            volume="+0%",
        )
        logger.info("[SETTINGS] TTS engine attached")

    def set_language(self, language_code: str):
        if not language_code:
            logger.warning("[SETTINGS] Missing language code")
            return self.language
        self.language = language_code
        if self._listener:
            self._listener.set_language(language_code)
        if self._tts_engine:
            self._tts_engine.set_language(language_code)
            self._apply_voice_profile()
        logger.info("[SETTINGS] Language switched to %s", language_code)
        self._persist_profile()
        return self.language

    def set_voice_gender(self, gender: Optional[str]):
        if not gender:
            logger.warning("[SETTINGS] Missing gender value")
            return self.voice_gender
        self.voice_gender = gender
        if self._tts_engine:
            self._tts_engine.set_voice_gender(gender)
            self._apply_voice_profile()
        logger.info("[SETTINGS] Voice gender set to %s", gender)
        self._persist_profile()
        return self.voice_gender

    def set_speech_speed(self, speed: float):
        speed = self._clamp_speed(speed)
        self.speech_speed = speed
        if self._tts_engine:
            self._tts_engine.set_speech_speed(speed)
        logger.info("[SETTINGS] Speech speed set to %.2f", speed)
        self._persist_profile()
        return self.speech_speed

    def adjust_speech_speed(self, delta: float):
        return self.set_speech_speed(self.speech_speed + delta)

    def _clamp_speed(self, speed: float) -> float:
        return max(self.min_speech_speed, min(speed, self.max_speech_speed))

    def speak(self, text: str):
        if not text:
            return None
        if not self._tts_engine:
            logger.warning("[SETTINGS] TTS engine is not attached; cannot speak")
            return None
        try:
            self._tts_engine.speak(text)
        except KeyboardInterrupt:
            logger.info("[SETTINGS] Speech interrupted")
        except Exception:  # noqa: BLE001
            logger.exception("[SETTINGS] Failed to synthesize speech")
        return text

    def speak_localized(self, ar_text: str, en_text: str):
        text = ar_text if self.language.startswith("ar") else en_text
        self.speak(text)
        return text

    def _current_voice_id(self) -> str:
        return self._voice_profiles.get((self.language, self.voice_gender), self._default_voice)

    def _apply_voice_profile(self):
        if self._tts_engine:
            self._tts_engine.set_voice_profile(self._current_voice_id())


settings_manager = SettingsManager()
