"""Unicode and Arabic text integrity helpers used across runtime validators."""

from __future__ import annotations

import re
import unicodedata

ARABIC_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF]")
LATIN_CHAR_PATTERN = re.compile(r"[A-Za-z]")

# Stable mojibake fragments observed in corrupted Arabic text paths.
ARABIC_MOJIBAKE_MARKERS: tuple[str, ...] = (
    "\u0637\u00b7\u0622\u00a7",
    "\u0637\u00b7\u0622\u00b9",
    "\u0637\u00b7\u0622\u00b1",
    "\u0637\u00b7\u0622\u00a8",
    "\u0637\u00b7\u0622\u00ae",
    "\u0637\u00a7",
    "\u0638\u201e",
    "\u0638\u2020",
    "\u0637\u00b5",
    "\u00d8\u00a7",
    "\u00d9\u201e",
    "\u00d9\u2020",
)

_MOJIBAKE_SYMBOL_CHARS = frozenset(
    {
        "\u00a6",
        "\u00a7",
        "\u00ab",
        "\u00b4",
        "\u00b5",
        "\u00b6",
        "\u00b7",
        "\u00b8",
        "\u00b9",
        "\u00ba",
        "\u00bb",
        "\u00bc",
        "\u00be",
        "\u00bf",
        "\u201a",
        "\u201e",
        "\u2020",
        "\u2021",
        "\u2026",
        "\u20ac",
        "\u2030",
        "\u2039",
        "\u203a",
    }
)

_LATIN_MOJIBAKE_CHARS = frozenset({"\u00c2", "\u00c3", "\u00d8", "\u00d9", "\u00da", "\u00db"})

_ALLOWED_CONTROLS = {"\n", "\r", "\t"}
_ALLOWED_FORMAT_CHARS = {"\u200c", "\u200d"}  # ZWNJ / ZWJ


def normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or ""))


def contains_replacement_character(text: str) -> bool:
    return "\ufffd" in str(text or "")


def contains_arabic_mojibake(text: str) -> bool:
    candidate = str(text or "")
    if not candidate:
        return False
    if any(token in candidate for token in ARABIC_MOJIBAKE_MARKERS):
        return True
    if has_arabic(candidate):
        symbol_hits = sum(1 for char in candidate if char in _MOJIBAKE_SYMBOL_CHARS)
        if symbol_hits >= 2:
            return True
    latin_mojibake_hits = sum(1 for char in candidate if char in _LATIN_MOJIBAKE_CHARS)
    if latin_mojibake_hits >= 2 and (" " in candidate or has_arabic(candidate)):
        return True
    return False


def contains_unexpected_unicode(text: str) -> bool:
    for char in str(text or ""):
        if char in _ALLOWED_CONTROLS:
            continue
        codepoint = ord(char)
        category = unicodedata.category(char)
        if category in {"Cc", "Cs", "Co"}:
            return True
        if category == "Cf" and char not in _ALLOWED_FORMAT_CHARS:
            return True
        # Unicode non-characters.
        if 0xFDD0 <= codepoint <= 0xFDEF:
            return True
        if (codepoint & 0xFFFE) == 0xFFFE:
            return True
    return False


def has_arabic(text: str) -> bool:
    return bool(ARABIC_CHAR_PATTERN.search(str(text or "")))


def has_latin(text: str) -> bool:
    return bool(LATIN_CHAR_PATTERN.search(str(text or "")))


def arabic_integrity_failure(text: str, *, require_arabic: bool = False) -> str | None:
    candidate = str(text or "").strip()
    if not candidate:
        return "missing"
    if contains_replacement_character(candidate):
        return "replacement_character"
    if contains_unexpected_unicode(candidate):
        return "unexpected_unicode"
    if contains_arabic_mojibake(candidate):
        return "mojibake_pattern"
    normalized = normalize_nfc(candidate)
    if normalized != candidate:
        return "not_normalized"
    if require_arabic and not has_arabic(candidate):
        return "language_mismatch"
    return None
