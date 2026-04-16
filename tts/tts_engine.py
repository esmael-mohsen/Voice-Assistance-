"""High-quality neural TTS powered by Microsoft Edge voices."""

import asyncio
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import edge_tts
from playsound import playsound

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self):
        self.language = "en-US"
        self.gender = "female"
        self.speed = 1.0
        self.voice_id = "en-US-JennyNeural"
        self._rate = "+0%"
        self._pitch = "+2Hz"
        self._volume = "+0%"

    def configure(self, language=None, gender=None, speed=None, voice_id=None, pitch=None, volume=None):
        if language:
            self.language = language
        if gender:
            self.gender = gender
        if voice_id:
            self.voice_id = voice_id
        if speed is not None:
            self.set_speech_speed(speed)
        if pitch is not None:
            self.set_pitch(pitch)
        if volume is not None:
            self.set_volume(volume)
        logger.info(
            "[TTS] Configured (voice=%s, speed=%.2f)",
            self.voice_id,
            self.speed,
        )

    def set_language(self, language):
        self.language = language
        logger.info("[TTS] Language context set to %s", language)

    def set_voice_gender(self, gender):
        self.gender = gender
        logger.info("[TTS] Voice gender context set to %s", gender)

    def set_voice_profile(self, voice_id):
        if voice_id:
            self.voice_id = voice_id
            logger.info("[TTS] Voice profile switched to %s", voice_id)

    def set_speech_speed(self, speed):
        self.speed = speed
        rate_percent = int((speed - 1.0) * 100)
        self._rate = f"{rate_percent:+d}%"
        logger.info("[TTS] Speech speed set to %.2f (%s)", speed, self._rate)

    def set_pitch(self, pitch: str):
        # Edge TTS format: '+0Hz', '-2Hz', '+4Hz'
        if pitch:
            self._pitch = pitch

    def set_volume(self, volume: str):
        # Edge TTS format: '+0%', '+10%', '-5%'
        if volume:
            self._volume = volume

    def speak(self, text):
        if not text:
            return
        try:
            asyncio.run(self._speak_async(text))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._speak_async(text))
            loop.close()

    async def _speak_async(self, text):
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice_id,
            rate=self._rate,
            pitch=self._pitch,
            volume=self._volume,
        )
        with NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            temp_path = Path(tmp_file.name)
        try:
            await communicate.save(str(temp_path))
            playsound(str(temp_path), block=True)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("[TTS] Unable to delete temp file %s", temp_path)
