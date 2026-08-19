"""Wake-word helpers for the DAI always-on listener (no network)."""

from __future__ import annotations

import json
import re
from typing import Literal, Tuple

Kind = Literal["ignore", "wake", "command", "close", "minimize", "restore", "repeat"]

# "DAI" is often heard as die / dye / they. Do not treat bare "day" as a wake word.
# Bare "they" is only a wake word as the whole utterance (Vosk grammar), not mid-sentence.
_WAKE_CORE = r"(?:d\.?\s*a\.?\s*i\.?|dai|die|dye)"
_WAKE = rf"(?:hey\s+|ok\s+|okay\s+|yo\s+)?{_WAKE_CORE}"
_WAKE_CLOSE = (
    r"(?:hey\s+|ok\s+|okay\s+|yo\s+)?"
    r"(?:d\.?\s*a\.?\s*i\.?|dai|die|dye|they)"
)

WAKE_GRAMMAR = json.dumps(
    [
        "dai",
        "hey dai",
        "ok dai",
        "okay dai",
        "die",
        "dye",
        "they",
        "dai close now",
        "die close now",
        "they close now",
        "[unk]",
    ]
)


def normalize(text: str) -> str:
    t = " ".join((text or "").lower().split())
    t = t.replace("d a i", "dai").replace("d.a.i", "dai")
    t = t.replace("d.i", "dai")
    return t.strip(" .,!?")


def clean_spoken_command(text: str) -> str:
    """Strip politeness / STT fillers so NLP hits more often."""
    t = normalize(text)
    t = re.sub(
        r"^(please|pls|just|now|um|uh|so|okay|ok|can you|could you|would you|"
        r"i want you to|i need you to|go ahead and|kindly)\s+",
        "",
        t,
    )
    t = re.sub(r"^(please|can you|could you)\s+", "", t)
    t = re.sub(r"\b(for me|please)\b", "", t)
    t = re.sub(r"^(execute|run command|do this|do that)\s+", "", t)
    return " ".join(t.split()).strip(" .,!?")


def is_close_phrase(text: str, *, session_active: bool = False) -> bool:
    t = normalize(text)
    if not t:
        return False
    if re.search(rf"^{_WAKE_CLOSE}\s+(close(\s+now)?|stop(\s+now)?|quit)$", t):
        return True
    if re.search(r"\bclose\s+now\b", t) and re.search(rf"^{_WAKE_CLOSE}\b", t):
        return True
    if session_active and re.search(
        r"^(close\s+now|stop\s+listening|stop\s+now|go\s+to\s+sleep)$", t
    ):
        return True
    return False


def is_wake_phrase(text: str) -> bool:
    t = normalize(text)
    if not t:
        return False
    if t in ("they", "hey they", "ok they", "okay they", "yo they"):
        return True
    return bool(re.match(rf"^{_WAKE}\b", t))


def is_minimize_phrase(text: str) -> bool:
    t = clean_spoken_command(text)
    if re.search(r"\b(minimize|minimise)\b", t):
        return True
    if re.search(r"\bhide\s+(the\s+)?(screen|window|app|this)\b", t):
        return True
    if t in ("hide", "go to tray", "make it small", "minimise", "minimize"):
        return True
    return False


def is_restore_phrase(text: str) -> bool:
    t = clean_spoken_command(text)
    return bool(
        re.search(r"\b(restore|maximize|maximise|unminimize|show window|bring back)\b", t)
        or re.search(r"^(show|restore)(\s+the)?(\s+app|\s+window)?$", t)
    )


def strip_wake(text: str) -> str:
    t = normalize(text)
    t = re.sub(rf"^{_WAKE_CLOSE}\s*", "", t).strip(" .,!?")
    return clean_spoken_command(t)


def looks_complete_command(text: str) -> bool:
    """True when a partial transcript is already a runnable command (faster than waiting for silence)."""
    t = clean_spoken_command(strip_wake(text) if is_wake_phrase(text) else text)
    if not t or len(t.split()) < 1:
        return False
    if is_close_phrase(t, session_active=True) or is_minimize_phrase(t) or is_restore_phrase(t):
        return True
    if re.match(
        r"^(click|tap|open|launch|type|write|press|scroll|copy|move|run|search|fill|wait)\b.+$",
        t,
    ):
        return True
    if re.match(r"^(again|repeat)$", t):
        return True
    return False


def classify_utterance(text: str, *, session_active: bool) -> Tuple[Kind, str]:
    raw = normalize(text)
    if not raw:
        return "ignore", ""
    if is_close_phrase(raw, session_active=session_active):
        return "close", ""
    cleaned = clean_spoken_command(strip_wake(raw) if is_wake_phrase(raw) else raw)
    if is_minimize_phrase(raw) or is_minimize_phrase(cleaned):
        if session_active or is_wake_phrase(raw):
            return "minimize", cleaned
    if is_restore_phrase(raw) or is_restore_phrase(cleaned):
        if session_active or is_wake_phrase(raw):
            return "restore", cleaned
    if session_active and re.match(r"^(again|repeat|do it again|execute that|do that)$", cleaned):
        return "repeat", ""
    if is_wake_phrase(raw):
        return "wake", cleaned
    if session_active:
        return "command", cleaned
    return "ignore", ""
