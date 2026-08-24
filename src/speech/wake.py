"""Wake-word helpers for the always-on listener (no network)."""

from __future__ import annotations

import json
import re
from typing import List, Literal, Tuple

Kind = Literal["ignore", "wake", "command", "close", "minimize", "restore", "repeat"]

DEFAULT_AGENT_NAME = "DAI"
_BLOCKED_NAMES = {
    "open",
    "click",
    "stop",
    "sleep",
    "type",
    "search",
    "google",
    "chrome",
    "close",
    "cancel",
}

# "DAI" is often heard as die / dye / they / day / guy.
_DAI_CORE = r"(?:d\.?\s*a\.?\s*i\.?|dai|die|dye)"
_DAI_LOOSE = r"(?:d\.?\s*a\.?\s*i\.?|dai|die|dye|they|day|guy)"
_WAKEUP_TAIL = r"(?:wake\s*up|wakeup|wake)"
_PREFIX = r"(?:hey\s+|ok\s+|okay\s+|yo\s+)?"

_agent_name = DEFAULT_AGENT_NAME
_WAKE_CORE = _DAI_CORE
_WAKE = rf"{_PREFIX}{_WAKE_CORE}"
_WAKE_CLOSE = rf"{_PREFIX}{_DAI_LOOSE}"
WAKE_GRAMMAR = "[]"


def agent_name() -> str:
    return _agent_name


def sanitize_agent_name(name: str) -> str:
    raw = " ".join((name or "").split())
    raw = re.sub(r"[^A-Za-z0-9 ]+", "", raw).strip()
    if not raw or raw.lower() in _BLOCKED_NAMES:
        return DEFAULT_AGENT_NAME
    if len(raw) > 24:
        raw = raw[:24].strip()
    if len(raw) < 2:
        return DEFAULT_AGENT_NAME
    return raw


def _name_pattern(name: str) -> str:
    parts = [re.escape(p) for p in name.lower().split() if p]
    if not parts:
        return _DAI_CORE
    spaced = r"\s+".join(parts)
    compact = re.escape("".join(name.lower().split()))
    cores = [spaced]
    if compact != spaced:
        cores.append(compact)
    if name.lower() != "dai":
        cores.append(_DAI_CORE)
    else:
        return _DAI_CORE
    return "(?:" + "|".join(cores) + ")"


def _grammar_phrases(name: str) -> List[str]:
    n = name.lower()
    phrases = [
        n,
        f"hey {n}",
        f"ok {n}",
        f"okay {n}",
        f"yo {n}",
        f"{n} wakeup",
        f"{n} wake up",
        f"{n} wake",
        f"wake up {n}",
        f"wakeup {n}",
        f"hey {n} wakeup",
        f"hey {n} wake up",
        f"{n} sleep",
        f"{n} close now",
        "[unk]",
    ]
    if n != "dai":
        phrases.extend(
            [
                "dai",
                "hey dai",
                "dai wakeup",
                "dai wake up",
                "wake up dai",
                "dai sleep",
                "dai close now",
            ]
        )
    else:
        phrases.extend(
            [
                "die",
                "dye",
                "they",
                "day",
                "guy",
                "die wakeup",
                "die wake up",
                "day wakeup",
                "they wakeup",
                "die close now",
                "they close now",
                "hey dai close now",
            ]
        )
    # unique, keep order
    out, seen = [], set()
    for p in phrases:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def set_agent_name(name: str) -> str:
    """Apply a user-chosen wake name. DAI remains a backup wake word."""
    global _agent_name, _WAKE_CORE, _WAKE, _WAKE_CLOSE, WAKE_GRAMMAR
    cleaned = sanitize_agent_name(name)
    _agent_name = cleaned
    _WAKE_CORE = _name_pattern(cleaned)
    _WAKE = rf"{_PREFIX}{_WAKE_CORE}"
    if cleaned.lower() == "dai":
        _WAKE_CLOSE = rf"{_PREFIX}{_DAI_LOOSE}"
    else:
        _WAKE_CLOSE = rf"{_PREFIX}(?:{_WAKE_CORE}|{_DAI_LOOSE})"
    WAKE_GRAMMAR = json.dumps(_grammar_phrases(cleaned))
    return _agent_name


set_agent_name(DEFAULT_AGENT_NAME)


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
        r"i want you to|i need you to|you should|i am saying|i'm saying|"
        r"go ahead and|kindly|basically)\s+",
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
    if re.search(rf"^{_WAKE_CLOSE}\s+(close(\s+now)?|quit|sleep)$", t):
        return True
    if re.search(r"\bclose\s+now\b", t) and re.search(rf"^{_WAKE_CLOSE}\b", t):
        return True
    named = re.escape(_agent_name.lower())
    if session_active and re.search(
        rf"^(close\s+now|stop\s+listening|go\s+to\s+sleep|sleep(\s+now)?|dai sleep|{named} sleep)$",
        t,
    ):
        return True
    return False


def is_sleep_phrase(text: str, *, session_active: bool = False) -> bool:
    """Put DAI back to sleep until the next “DAI wakeup”."""
    t = normalize(text)
    if not t:
        return False
    if is_close_phrase(t, session_active=session_active):
        return True
    if re.search(rf"^{_WAKE_CLOSE}\s+(sleep|standby|rest)$", t):
        return True
    if session_active and re.search(
        r"^(sleep|go\s+to\s+sleep|go\s+sleep|sleep\s+now|standby)$", t
    ):
        return True
    return False


def is_wakeup_phrase(text: str) -> bool:
    """True only for “DAI wakeup” (not bare DAI). Google often hears die/day/they."""
    t = normalize(text)
    if not t:
        return False
    if re.search(rf"{_WAKE_CLOSE}\s+{_WAKEUP_TAIL}\b", t):
        return True
    if re.search(rf"\b{_WAKEUP_TAIL}\s+{_WAKE_CORE}\b", t):
        return True
    if _agent_name.lower() == "dai" and re.search(rf"\b{_WAKEUP_TAIL}\s+(?:they|day|guy)\b", t):
        return True
    compact = t.replace(" ", "")
    if "wakeup" in compact or "wake up" in t:
        named = re.escape(_agent_name.lower())
        if re.search(rf"\b(?:dai|die|dye|hey|{named})\b", t):
            return True
        if _agent_name.lower() == "dai" and re.search(r"\b(?:they|day|guy)\b", t):
            return True
    return False


def is_wakeup_followup(text: str) -> bool:
    """Second half when Google splits “DAI” and “wakeup” into two results."""
    t = normalize(text)
    return bool(re.match(rf"^{_WAKEUP_TAIL}$", t))


def looks_like_wakeup_progress(text: str) -> bool:
    """Idle partials that look like the person is saying DAI wakeup."""
    t = normalize(text)
    if not t:
        return False
    if is_wakeup_phrase(t) or is_wake_phrase(t) or is_wakeup_followup(t):
        return True
    named = re.escape(_agent_name.lower())
    return bool(re.search(rf"\b(dai|die|dye|wake|{named})\b", t))


def strip_wakeup(text: str) -> str:
    t = normalize(text)
    t = re.sub(rf"^{_WAKE}\s+{_WAKEUP_TAIL}\s*", "", t)
    t = re.sub(rf"^{_WAKEUP_TAIL}\s+{_WAKE_CORE}\s*", "", t)
    t = re.sub(rf"^{_WAKE_CLOSE}\s+{_WAKEUP_TAIL}\s*", "", t)
    return clean_spoken_command(t.strip(" .,!?"))


def is_wake_phrase(text: str) -> bool:
    t = normalize(text)
    if not t:
        return False
    # Whole-utterance aliases Vosk often produces instead of "DAI"
    if _agent_name.lower() == "dai" and t in (
        "they",
        "day",
        "guy",
        "tie",
        "thai",
        "tai",
        "diet",
        "hey they",
        "ok they",
        "okay they",
        "yo they",
        "hey day",
        "hey die",
        "hey guy",
    ):
        return True
    return bool(re.match(rf"^{_WAKE}\b", t))


def looks_complete_wake(text: str) -> bool:
    """Idle partial that is already “DAI wakeup” (optionally plus a full command)."""
    t = normalize(text)
    if not t:
        return False
    if is_sleep_phrase(t, session_active=False):
        return True
    if is_wakeup_phrase(t):
        leftover = strip_wakeup(t)
        if not leftover:
            return True
        return leftover == t or looks_complete_command(leftover)
    return False


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
    if is_sleep_phrase(raw, session_active=session_active):
        return "close", ""

    woke = is_wakeup_phrase(raw)
    leftover = strip_wakeup(raw) if woke else ""
    cleaned = leftover or clean_spoken_command(
        strip_wake(raw) if is_wake_phrase(raw) else raw
    )

    listening = session_active or woke
    if listening and (is_minimize_phrase(raw) or is_minimize_phrase(cleaned)):
        return "minimize", cleaned
    if listening and (is_restore_phrase(raw) or is_restore_phrase(cleaned)):
        return "restore", cleaned
    if session_active and re.match(r"^(again|repeat|do it again|execute that|do that)$", cleaned):
        return "repeat", ""
    if woke:
        return "wake", leftover
    if session_active:
        return "command", cleaned
    return "ignore", ""
