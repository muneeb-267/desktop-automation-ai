"""Intent classification and entity extraction for plain-English commands."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedCommand:
    raw_text: str
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Intent patterns: (intent, regex, confidence)
_PATTERNS: List[Tuple[str, re.Pattern[str], float]] = [
    (
        "run_workflow",
        re.compile(
            r"\b(?:run|replay|execute)\s+(?:workflow|macro)\s+(?P<workflow>.+)$",
            re.I,
        ),
        0.95,
    ),
    (
        "search_web",
        re.compile(
            r"\b(?:search(?:\s+for)?|google)\s+(?P<query>.+)$",
            re.I,
        ),
        0.9,
    ),
    (
        "open_app",
        re.compile(
            r"\b(?:open|launch|start)\s+(?P<app>[\w .\-]+?)(?:\s+and\s+(?P<rest>.+))?$",
            re.I,
        ),
        0.92,
    ),
    (
        "click_text",
        re.compile(
            r"\b(?:click|press|tap)\s+(?:(?:on|the)\s+)?(?P<element>.+)$",
            re.I,
        ),
        0.88,
    ),
    (
        "type_text",
        re.compile(
            r"\b(?:type|enter|write|fill)\s+(?:(?:in|into|the)\s+(?P<field>.+?)\s+with\s+)?[\"']?(?P<text>.+?)[\"']?\s*$",
            re.I,
        ),
        0.86,
    ),
    (
        "press_key",
        re.compile(
            r"\b(?:press|hit)\s+(?:key\s+)?(?P<key>enter|tab|escape|esc|space|backspace|ctrl\+[a-z]|alt\+[a-z]|cmd\+[a-z]|win\+[a-z])$",
            re.I,
        ),
        0.9,
    ),
    (
        "scroll",
        re.compile(
            r"\bscroll\s+(?P<direction>up|down|left|right)(?:\s+(?P<amount>\d+))?$",
            re.I,
        ),
        0.9,
    ),
    (
        "wait",
        re.compile(
            r"\b(?:wait|pause|sleep)\s+(?:for\s+)?(?P<seconds>\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?$",
            re.I,
        ),
        0.93,
    ),
]

_APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "terminal": "terminal",
    "cmd": "cmd",
    "explorer": "explorer",
    "file explorer": "explorer",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
}


class NLPEngine:
    """spaCy tokenizer when available, plus robust rule-based intents."""

    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        self._nlp = None
        self._spacy_model = spacy_model
        try:
            import spacy

            try:
                self._nlp = spacy.load(spacy_model)
            except OSError:
                self._nlp = None
        except ImportError:
            self._nlp = None

    def tokenize(self, text: str) -> List[str]:
        cleaned = " ".join(text.strip().split())
        if self._nlp is not None:
            return [t.text for t in self._nlp(cleaned)]
        # Lightweight NLTK / regex fallback
        try:
            import nltk
            from nltk.tokenize import word_tokenize

            try:
                return word_tokenize(cleaned)
            except LookupError:
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)
                return word_tokenize(cleaned)
        except Exception:
            return re.findall(r"[\w']+|[.,!?;]", cleaned)

    def parse(self, text: str) -> ParsedCommand:
        raw = " ".join(text.strip().split())
        if not raw:
            return ParsedCommand(raw_text=text, intent="unknown", confidence=0.0)

        # Multi-step: "open chrome and search cats"
        if " and " in raw.lower():
            parts = re.split(r"\band\b", raw, flags=re.I)
            steps: List[Dict[str, Any]] = []
            confidences: List[float] = []
            for part in parts:
                part = part.strip(" ,.")
                if not part:
                    continue
                parsed = self._parse_single(part)
                steps.append(
                    {
                        "intent": parsed.intent,
                        "entities": parsed.entities,
                        "confidence": parsed.confidence,
                    }
                )
                confidences.append(parsed.confidence)
            primary = steps[0] if steps else {"intent": "unknown", "entities": {}, "confidence": 0.0}
            return ParsedCommand(
                raw_text=raw,
                intent=primary["intent"],
                entities=primary.get("entities", {}),
                confidence=sum(confidences) / len(confidences) if confidences else 0.0,
                steps=steps,
            )

        single = self._parse_single(raw)
        single.steps = [
            {
                "intent": single.intent,
                "entities": single.entities,
                "confidence": single.confidence,
            }
        ]
        return single

    def _parse_single(self, text: str) -> ParsedCommand:
        # Tokens kept for auditing / future ML features
        _ = self.tokenize(text)
        for intent, pattern, base_conf in _PATTERNS:
            match = pattern.search(text.strip())
            if not match:
                continue
            entities = {k: (v.strip() if isinstance(v, str) else v) for k, v in match.groupdict().items() if v}
            entities = self._normalize_entities(intent, entities, text)
            return ParsedCommand(
                raw_text=text,
                intent=intent,
                entities=entities,
                confidence=base_conf,
            )
        return ParsedCommand(
            raw_text=text,
            intent="unknown",
            entities={},
            confidence=0.2,
        )

    def _normalize_entities(
        self, intent: str, entities: Dict[str, Any], text: str
    ) -> Dict[str, Any]:
        out = dict(entities)
        if intent == "open_app" and "app" in out:
            app_key = out["app"].lower().strip()
            out["app"] = _APP_ALIASES.get(app_key, app_key)
            rest = out.pop("rest", None)
            if rest:
                out["follow_up"] = rest
        if intent == "type_text":
            if "text" not in out:
                # Fallback: everything after type/enter
                m = re.search(r"\b(?:type|enter|write|fill)\s+(.+)$", text, re.I)
                if m:
                    out["text"] = m.group(1).strip(" \"'")
            out.setdefault("text", "")
        if intent == "click_text":
            out["element"] = out.get("element", "").strip(" \"'")
        if intent == "press_key":
            key = out.get("key", "").lower().replace("esc", "escape")
            out["key"] = key
        if intent == "scroll":
            out["direction"] = out.get("direction", "down").lower()
            out["amount"] = int(out.get("amount") or 3)
        if intent == "wait":
            out["seconds"] = float(out.get("seconds") or 1)
        if intent == "search_web":
            out["query"] = out.get("query", "").strip(" \"'")
        if intent == "run_workflow":
            out["workflow"] = out.get("workflow", "").strip(" \"'")
        return out
