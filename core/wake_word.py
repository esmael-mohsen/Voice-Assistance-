import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class WakeAction(str, Enum):
    START = "start"
    STOP = "stop"


@dataclass(frozen=True)
class WakeResult:
    action: WakeAction
    phrase: str


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    # Normalize common Arabic variations lightly and remove punctuation.
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class WakeWordDetector:
    """Simple wake-word / stop-phrase detection on recognized text.

    This does not do audio keyword spotting; it works on STT results.
    """

    def __init__(
        self,
        wake_names: Optional[Iterable[str]] = None,
        start_phrases: Optional[Iterable[str]] = None,
        stop_phrases: Optional[Iterable[str]] = None,
    ):
        # Include Arabic phonetic spellings that Google STT often returns.
        default_wake_names = (
            "egb",
            "e g b",
            "egp",
            "e g p",
            "اي جي بي",
            "ايجي بي",
            "اي جي بى",
            "ايچي بي",
            "اي جي پي",
            "ايجي پي",
            "اي جي بيه",
        )
        self.wake_names = [_normalize(x) for x in (wake_names or default_wake_names)]

        # Keep lists for backwards compatibility (not strict-matched anymore).
        self.start_phrases = [_normalize(x) for x in (start_phrases or ())]
        self.stop_phrases = [_normalize(x) for x in (stop_phrases or ())]

        self._greetings = [
            "hi",
            "hello",
            "hey",
            "هاي",
            "هالو",
            "اهلا",
            "اهلا وسهلا",
            "السلام عليكم",
        ]

    def detect(self, text: str) -> Optional[WakeResult]:
        normalized = _normalize(text)
        if not normalized:
            return None

        # Name detection: allow token match or substring (covers "هاي اي جي بي", "اهلا ايجي بي" etc.)
        has_name = any(name and (name in normalized or name in normalized.split()) for name in self.wake_names)

        # START: require name + greeting OR just name.
        if has_name:
            if any(g in normalized for g in self._greetings) or normalized in self.wake_names:
                return WakeResult(action=WakeAction.START, phrase=normalized)

        return None
