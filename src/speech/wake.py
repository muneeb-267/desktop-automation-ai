"""Wake-word helpers for the DAI always-on listener (no network)."""

from __future__ import annotations

import re
from typing import Literal, Tuple

Kind = Literal["ignore", "wake", "command", "close"]

# "DAI" is often heard as die / dye. Do not treat bare "day" as a wake word.
_WAKE = r"(?:hey\s+|ok\s+|okay\s+)?(?:d\.?\s*a\.?\s*i\.?|dai|die|dye)"
_CLOSE = rf"(?:{_WAKE}\s+)?(?:close\s+now|stop\s+(?:now|listening)|go\s+to\s+sleep|quit\s+now)"


def normalize(text: str) -> str:
    t = " ".join((text or "").lower().split())
    t = t.replace("d a i", "dai").replace("d.a.i", "dai")
    return t.strip(" .,!?")


def is_close_phrase(text: str, *, session_active: bool = False) -> bool:
    t = normalize(text)
    if not t:
        return False
    if re.search(rf"^{_WAKE}\s+(close(\s+now)?|stop(\s+now)?|quit)$", t):
        return True
    if re.search(r"\bclose\s+now\b", t) and re.search(rf"\b{_WAKE}\b", t):
        return True
    if session_active and re.search(r"^(close\s+now|stop\s+listening|stop\s+now)$", t):
        return True
    return False


def is_wake_phrase(text: str) -> bool:
    t = normalize(text)
    return bool(re.search(rf"\b{_WAKE}\b", t))


def strip_wake(text: str) -> str:
    t = normalize(text)
    t = re.sub(rf"^{_WAKE}\s*", "", t).strip(" .,!?")
    return t


def classify_utterance(text: str, *, session_active: bool) -> Tuple[Kind, str]:
    """
    Return (kind, command_text).
    kind: ignore | wake | command | close
    """
    raw = normalize(text)
    if not raw:
        return "ignore", ""
    if is_close_phrase(raw, session_active=session_active):
        return "close", ""
    if is_wake_phrase(raw):
        rest = strip_wake(raw)
        return "wake", rest
    if session_active:
        return "command", raw
    return "ignore", ""
