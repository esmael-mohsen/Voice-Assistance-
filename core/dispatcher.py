import logging

from core import parser, resolver
from settings.settings_manager import settings_manager

logger = logging.getLogger(__name__)


def dispatch(text_input):
    match = parser.parse_command(text_input)
    if not match:
        logger.warning("[DISPATCHER] Command not recognized for input: %s", text_input)
        message = settings_manager.speak_localized(
            "معذرة، لم أفهم هذا الأمر",
            "Sorry, I didn't understand that command."
        )
        return message

    logger.info(
        "[DISPATCHER] Dispatching command '%s' (score %.1f via '%s')",
        match.key,
        match.score,
        match.keyword,
    )
    result = resolver.resolve_command(
        command_key=match.key,
        command_text=text_input,
        metadata={"score": match.score, "keyword": match.keyword},
    )
    logger.info("[DISPATCHER] Command executed: %s", match.key)
    return result
