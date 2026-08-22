"""Pick the first Google-style search result from OCR words (no Tesseract)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

FIRST_RESULT_ELEMENT = "__first_result__"

_FIRST_RESULT_RE = re.compile(
    r"\b(?:click|tap|open|go\s+to)?\s*(?:on\s+)?(?:the\s+)?(?:first|top|1st)\s+"
    r"(?:search\s+)?(?:result|link|hit)\b",
    re.I,
)
_FIRST_RESULT_ONLY_RE = re.compile(
    r"^(?:on\s+)?(?:the\s+)?(?:first|top|1st)\s+(?:search\s+)?(?:result|link|hit)$",
    re.I,
)

_SKIP_LINE = re.compile(
    r"(dai\b|google mic|wakeup|sleeping|heard:|do you mean|"
    r"ai overview|people also ask|sponsored|about this result|"
    r"^all$|^images$|^videos$|^maps$|^news$|^shopping$|^more$|"
    r"^tools$|^settings$|^sign in$|^gmail$|^search$|^app$|"
    r"translations?|feedback|missing:|did you mean)",
    re.I,
)

_URLISH = re.compile(
    r"(https?://)|(\b[\w-]+\.(com|org|net|edu|pk|uk|io|gov|co|info)\b)",
    re.I,
)


def is_first_result_phrase(text: str) -> bool:
    t = " ".join((text or "").lower().split())
    if not t:
        return False
    if t in {FIRST_RESULT_ELEMENT, "1", "first", "first result"}:
        return True
    return bool(_FIRST_RESULT_RE.search(t) or _FIRST_RESULT_ONLY_RE.match(t))


def text_matches_query(ocr_text: str, query: str) -> bool:
    """True when an OCR fragment is a real match, not a short substring like 'the'."""
    from src.vision.ocr_text import distinctive_tokens, normalize_ocr_query

    text_l = normalize_ocr_query(ocr_text)
    query_l = normalize_ocr_query(query)
    if not text_l or not query_l:
        return False
    if query_l == text_l or query_l in text_l:
        return True
    if len(text_l) >= 5 and text_l in query_l:
        return True
    q_brands = set(distinctive_tokens(query_l))
    t_brands = set(distinctive_tokens(text_l))
    if q_brands and q_brands <= t_brands | set(text_l.split()):
        if q_brands & set(re.findall(r"[a-z0-9]+", text_l)):
            return True
    if q_brands and q_brands & set(re.findall(r"[a-z0-9]+", text_l)):
        return True
    return False


def pick_first_search_result(
    words: List[Dict[str, Any]],
    width: int,
    height: int,
) -> Optional[Dict[str, Any]]:
    """Return a box {x,y,w,h,label} for the first organic result title."""
    if not words or width <= 0 or height <= 0:
        return None
    top_cut = max(int(height * 0.20), 170)
    bot_cut = int(height * 0.90)
    right_cut = int(width * 0.78)

    lines: Dict[Any, List[Dict[str, Any]]] = {}
    for item in words:
        y = int(item.get("y") or 0)
        x = int(item.get("x") or 0)
        if y < top_cut or y > bot_cut or x > right_cut:
            continue
        key = (item.get("block"), item.get("line"), y // 10)
        lines.setdefault(key, []).append(item)

    ordered: List[Dict[str, Any]] = []
    for group in lines.values():
        group.sort(key=lambda i: int(i.get("x") or 0))
        text = " ".join(str(i.get("label") or "") for i in group).strip()
        if not text:
            continue
        x0 = int(group[0].get("x") or 0)
        y0 = min(int(i.get("y") or 0) for i in group)
        x1 = max(int(i.get("x") or 0) + int(i.get("w") or 0) for i in group)
        y1 = max(int(i.get("y") or 0) + int(i.get("h") or 0) for i in group)
        ordered.append(
            {
                "text": text,
                "x": x0,
                "y": y0,
                "w": max(8, x1 - x0),
                "h": max(8, y1 - y0),
            }
        )
    ordered.sort(key=lambda line: (line["y"], line["x"]))

    content: List[Dict[str, Any]] = []
    for line in ordered:
        text = line["text"]
        if len(text) < 3:
            continue
        if _SKIP_LINE.search(text):
            continue
        content.append(line)

    def as_box(line: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "x": line["x"],
            "y": line["y"],
            "w": line["w"],
            "h": line["h"],
            "label": line["text"],
        }

    for i, line in enumerate(content):
        if _URLISH.search(line["text"]):
            for j in range(i - 1, -1, -1):
                prev = content[j]
                if _URLISH.search(prev["text"]):
                    continue
                if len(prev["text"].split()) >= 2 or len(prev["text"]) >= 8:
                    return as_box(prev)
            return as_box(line)

    for line in content:
        if len(line["text"].split()) >= 2:
            return as_box(line)
    if content:
        return as_box(content[0])
    return None
