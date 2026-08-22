"""Screen understanding: OCR words → structured buttons / links / inputs."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.agent.elements import ScreenElement, ScreenState
from src.vision.search_result import pick_first_search_result

_BUTTON_WORDS = re.compile(
    r"\b(login|log in|sign in|signin|next|continue|submit|send|search|"
    r"ok|okay|cancel|close|save|apply|download|upload|register|create|"
    r"microsoft|google|facebook|apple|yes|no)\b",
    re.I,
)
_INPUT_WORDS = re.compile(
    r"\b(email|e-mail|username|user name|password|phone|search|otp|pin)\b",
    re.I,
)
_LINK_WORDS = re.compile(r"https?://|www\.|[\w-]+\.(com|org|net|edu|pk|uk|io)\b", re.I)


def _classify_line(text: str) -> str:
    t = text or ""
    if _INPUT_WORDS.search(t) and not _BUTTON_WORDS.search(t):
        return "input"
    if _LINK_WORDS.search(t) and len(t.split()) <= 4:
        return "link"
    if _BUTTON_WORDS.search(t) or len(t.split()) <= 5:
        return "button"
    return "text"


def _group_lines(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lines: Dict[Any, List[Dict[str, Any]]] = {}
    for item in words:
        key = (item.get("block"), item.get("line"), int(item.get("y") or 0) // 10)
        lines.setdefault(key, []).append(item)
    out = []
    for group in lines.values():
        group.sort(key=lambda i: int(i.get("x") or 0))
        text = " ".join(str(i.get("label") or "") for i in group).strip()
        if not text:
            continue
        x0 = int(group[0].get("x") or 0)
        y0 = min(int(i.get("y") or 0) for i in group)
        x1 = max(int(i.get("x") or 0) + int(i.get("w") or 0) for i in group)
        y1 = max(int(i.get("y") or 0) + int(i.get("h") or 0) for i in group)
        avg = sum(float(i.get("conf") or 70) for i in group) / max(1, len(group))
        out.append({"text": text, "x": x0, "y": y0, "w": max(8, x1 - x0), "h": max(8, y1 - y0), "conf": avg})
    out.sort(key=lambda r: (r["y"], r["x"]))
    return out


class ScreenAnalyzer:
    def __init__(self, vision) -> None:
        self.vision = vision

    def analyze(self, frame=None) -> ScreenState:
        img = frame if frame is not None else self.vision.capture_screen()
        h, w = img.shape[:2]
        words = []
        if hasattr(self.vision, "_ocr_words"):
            words = self.vision._ocr_words(img)
        elements: List[ScreenElement] = []
        for i, line in enumerate(_group_lines(words)):
            kind = _classify_line(line["text"])
            elements.append(
                ScreenElement(
                    id=f"ocr-{i}",
                    type=kind,
                    text=line["text"],
                    role=kind,
                    x=line["x"],
                    y=line["y"],
                    width=line["w"],
                    height=line["h"],
                    confidence=max(0.4, min(0.98, float(line["conf"]) / 100.0)),
                    source="OCR",
                )
            )
        first = pick_first_search_result(words, w, h)
        if first:
            elements.insert(
                0,
                ScreenElement(
                    id="ocr-first-result",
                    type="link",
                    text=str(first.get("label") or "first result"),
                    role="first_result",
                    x=int(first["x"]),
                    y=int(first["y"]),
                    width=int(first["w"]),
                    height=int(first["h"]),
                    confidence=0.88,
                    source="OCR",
                ),
            )
        path = ""
        try:
            path = self.vision.save_capture(img, label="screen_state", boxes=[e.to_dict() for e in elements[:24]])
        except Exception:
            path = ""
        a11y = _optional_accessibility()
        if a11y:
            elements.extend(a11y)
        return ScreenState(elements=elements, width=w, height=h, capture_path=path)


def _optional_accessibility() -> List[ScreenElement]:
    """Best-effort Windows UI Automation. Soft-fail if pywinauto is not installed."""
    try:
        from pywinauto import Desktop  # type: ignore
    except Exception:
        return []
    found: List[ScreenElement] = []
    try:
        desk = Desktop(backend="uia")
        win = desk.get_active()
        if win is None:
            return []
        for i, ctrl in enumerate(win.descendants()[:80]):
            try:
                text = (ctrl.window_text() or "").strip()
                if not text or len(text) > 80:
                    continue
                rec = ctrl.rectangle()
                kind = "button" if "Button" in str(ctrl.element_info.control_type) else "text"
                if "Edit" in str(ctrl.element_info.control_type):
                    kind = "input"
                found.append(
                    ScreenElement(
                        id=f"a11y-{i}",
                        type=kind,
                        text=text,
                        role=str(ctrl.element_info.control_type),
                        x=int(rec.left),
                        y=int(rec.top),
                        width=max(8, int(rec.width())),
                        height=max(8, int(rec.height())),
                        confidence=0.92,
                        source="ACCESSIBILITY",
                    )
                )
            except Exception:
                continue
    except Exception:
        return []
    return found
