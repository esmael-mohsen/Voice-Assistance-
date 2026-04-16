import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class UserProfile:
    username: str = ""
    language: str = "ar-EG"
    voice_gender: str = "female"
    speech_speed: float = 1.0

    @property
    def configured(self) -> bool:
        return bool(self.username and self.language and self.voice_gender)


def _profile_path() -> Path:
    # Store under settings/ so it's easy to find, and keep it local to the app folder.
    return Path(__file__).resolve().parent / "user_profile.json"


def profile_exists() -> bool:
    return _profile_path().exists()


def load_profile() -> Optional[UserProfile]:
    path = _profile_path()
    if not path.exists():
        return None

    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return UserProfile(
        username=str(data.get("username", "") or ""),
        language=str(data.get("language", "ar-EG") or "ar-EG"),
        voice_gender=str(data.get("voice_gender", "female") or "female"),
        speech_speed=float(data.get("speech_speed", 1.0) or 1.0),
    )


def save_profile(profile: UserProfile) -> None:
    path = _profile_path()
    payload = {
        "username": profile.username,
        "language": profile.language,
        "voice_gender": profile.voice_gender,
        "speech_speed": profile.speech_speed,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
