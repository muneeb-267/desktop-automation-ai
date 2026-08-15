"""NLP Engine: fast rule path + optional spaCy/NLTK enrichment."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Shared lazy handles so the app doesn't reload models repeatedly
_SPACY_NLP = None
_SPACY_TRIED = False
_NLTK_READY = False
_NLTK_TRIED = False


@dataclass
class ParsedCommand:
    raw_text: str
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    lemmas: List[str] = field(default_factory=list)
    pos_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "google": "google",
    "browser": "chrome",
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
    "gmail": "gmail",
    "youtube": "youtube",
}


class NLPEngine:
    """Intent classification & entity extraction (fast-first, spaCy/NLTK optional)."""

    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        lazy: bool = True,
        min_confidence: float = 0.45,
    ) -> None:
        self._spacy_model = spacy_model
        self._lazy = lazy
        self.min_confidence = float(min_confidence)
        if not lazy:
            self._ensure_spacy()
            self._ensure_nltk()

    def _ensure_spacy(self):
        global _SPACY_NLP, _SPACY_TRIED
        if _SPACY_TRIED:
            return _SPACY_NLP
        _SPACY_TRIED = True
        try:
            import spacy

            try:
                _SPACY_NLP = spacy.load(self._spacy_model)
            except OSError:
                _SPACY_NLP = spacy.blank("en")
        except Exception:
            _SPACY_NLP = None
        return _SPACY_NLP

    def _ensure_nltk(self) -> bool:
        global _NLTK_READY, _NLTK_TRIED
        if _NLTK_TRIED:
            return _NLTK_READY
        _NLTK_TRIED = True
        try:
            import nltk

            for pkg in ("punkt", "punkt_tab"):
                try:
                    nltk.data.find(f"tokenizers/{pkg}")
                except LookupError:
                    nltk.download(pkg, quiet=True)
            _NLTK_READY = True
        except Exception:
            _NLTK_READY = False
        return _NLTK_READY

    def tokenize(self, text: str) -> List[str]:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return []
        # Fast path — avoid model load for common commands
        return re.findall(r"[A-Za-z0-9_']+|[^\s\w]", cleaned)

    def analyze(self, text: str, *, enrich: bool = False) -> Dict[str, Any]:
        cleaned = " ".join(text.strip().split())
        tokens = self.tokenize(cleaned)
        lemmas = [t.lower() for t in tokens]
        pos_tags: List[str] = []
        noun_chunks: List[str] = []
        spacy_ents: List[Dict[str, str]] = []

        if enrich:
            nlp = self._ensure_spacy()
            if nlp is not None and cleaned:
                doc = nlp(cleaned)
                tokens = [t.text for t in doc] or tokens
                if any(getattr(t, "pos_", "") for t in doc):
                    lemmas = [t.lemma_.lower() for t in doc]
                    pos_tags = [t.pos_ for t in doc]
                try:
                    noun_chunks = [c.text for c in doc.noun_chunks]
                except Exception:
                    noun_chunks = []
                spacy_ents = [
                    {"text": e.text, "label": e.label_} for e in getattr(doc, "ents", [])
                ]
            elif self._ensure_nltk() and cleaned:
                from nltk.tokenize import word_tokenize

                tokens = word_tokenize(cleaned)
                lemmas = [t.lower() for t in tokens]

        return {
            "tokens": tokens,
            "lemmas": lemmas or [t.lower() for t in tokens],
            "pos_tags": pos_tags,
            "noun_chunks": noun_chunks,
            "spacy_ents": spacy_ents,
        }

    def parse(self, text: str) -> ParsedCommand:
        raw = " ".join(text.strip().split())
        if not raw:
            return ParsedCommand(raw_text=text, intent="unknown", confidence=0.0)

        # Split on " and " only when it joins commands (not inside quoted text)
        if re.search(r"\band\b", raw, flags=re.I) and not re.search(r"[\"'].*\band\b.*[\"']", raw, flags=re.I):
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
            analysis = self.analyze(raw, enrich=False)
            return ParsedCommand(
                raw_text=raw,
                intent=primary["intent"],
                entities=primary.get("entities", {}),
                confidence=sum(confidences) / len(confidences) if confidences else 0.0,
                steps=steps,
                tokens=analysis["tokens"],
                lemmas=analysis["lemmas"],
                pos_tags=analysis["pos_tags"],
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
        analysis = self.analyze(text, enrich=False)
        lemmas = analysis["lemmas"]
        tokens = analysis["tokens"]
        lower = text.lower().strip()

        intent, confidence = self._classify_intent(lemmas, lower)
        entities = self._extract_entities(intent, text, analysis)

        # Light enrichment only when entity extraction looks weak
        if intent == "unknown" or (intent == "open_app" and not entities.get("app")):
            analysis = self.analyze(text, enrich=True)
            lemmas = analysis["lemmas"] or lemmas
            intent, confidence = self._classify_intent(lemmas, lower)
            entities = self._extract_entities(intent, text, analysis)

        if confidence < self.min_confidence and intent != "unknown":
            # Keep intent but flag low confidence for UI messaging
            entities["low_confidence"] = True

        if intent in ("open_app",) and not entities.get("app"):
            intent, confidence = "unknown", 0.15
        if intent in ("click_text", "click_button") and not entities.get("element"):
            intent, confidence = "unknown", 0.15
        if intent == "fill_form" and not (entities.get("field") or entities.get("text")):
            intent, confidence = "unknown", 0.15
        if intent == "type_text" and not entities.get("text"):
            intent, confidence = "unknown", 0.15
        if intent == "search_web" and not entities.get("query"):
            intent, confidence = "unknown", 0.15

        return ParsedCommand(
            raw_text=text,
            intent=intent,
            entities=entities,
            confidence=confidence,
            tokens=tokens,
            lemmas=lemmas,
            pos_tags=analysis.get("pos_tags") or [],
        )

    def _classify_intent(self, lemmas: List[str], lower: str) -> Tuple[str, float]:
        if re.search(r"\b(run|replay|execute)\s+(workflow|macro)\b", lower):
            return "run_workflow", 0.95
        if re.search(
            r"\bpress\s+(key\s+)?(enter|tab|escape|esc|space|backspace|ctrl\+|alt\+|cmd\+|win\+)",
            lower,
        ):
            return "press_key", 0.9
        if "scroll" in lemmas or lower.startswith("scroll"):
            return "scroll", 0.9
        if any(w in lemmas for w in ("wait", "pause", "sleep")):
            return "wait", 0.93
        if any(w in lemmas for w in ("open", "launch", "start")):
            return "open_app", 0.92
        if "search" in lemmas or re.search(r"^\s*google\s+\S+", lower):
            return "search_web", 0.9
        # SDS intents: click_button / fill_form (plus click_text alias)
        if re.search(r"\b(click|tap)\s+(?:on\s+)?(?:the\s+)?button\b", lower):
            return "click_button", 0.93
        if re.search(
            r"\b(fill|complete)\s+(?:(?:the|a)\s+)?form\b",
            lower,
        ) or re.search(
            r"\bfill\s+(?:(?:in|into|the)\s+)?(?P<field>.+?)\s+with\b",
            lower,
        ):
            return "fill_form", 0.92
        if any(w in lemmas for w in ("click", "tap")):
            return "click_text", 0.88
        if any(w in lemmas for w in ("type", "write", "fill")) or (
            "enter" in lemmas and not re.search(r"\bpress\s+enter\b", lower)
        ):
            return "type_text", 0.86
        return "unknown", 0.2

    def _extract_entities(
        self, intent: str, text: str, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        if intent == "open_app":
            m = re.search(r"\b(?:open|launch|start)\s+(.+)$", text, re.I)
            app = (m.group(1) if m else "").strip()
            # Strip trailing follow-ups already split; keep first app token phrase
            app = re.split(r"\band\b", app, maxsplit=1, flags=re.I)[0].strip()
            for chunk in analysis.get("noun_chunks") or []:
                cleaned = re.sub(r"^(open|launch|start)\s+", "", chunk.strip(), flags=re.I).strip()
                key = cleaned.lower()
                if key in _APP_ALIASES or key.split()[0] in _APP_ALIASES:
                    app = cleaned
                    break
            app_key = app.lower().strip()
            if app_key in _APP_ALIASES:
                entities["app"] = _APP_ALIASES[app_key]
            elif app_key:
                first = app_key.split()[0]
                entities["app"] = _APP_ALIASES.get(first, first)
            else:
                entities["app"] = ""
        elif intent in ("click_text", "click_button"):
            m = re.search(
                r"\b(?:click|tap)\s+(?:(?:on|the)\s+)?(?:button\s+)?(.+)$",
                text,
                re.I,
            )
            entities["element"] = (m.group(1) if m else "").strip(" \"'")
            if intent == "click_button":
                entities["element_type"] = "button"
        elif intent == "fill_form":
            m = re.search(
                r"\bfill\s+(?:(?:in|into|the)\s+)?(?P<field>.+?)\s+with\s+[\"']?(?P<text>.+?)[\"']?\s*$",
                text,
                re.I,
            )
            if m:
                entities["field"] = m.group("field").strip(" \"'")
                entities["text"] = (m.group("text") or "").strip(" \"'")
            else:
                m2 = re.search(
                    r"\b(?:fill|complete)\s+(?:(?:the|a)\s+)?form\s+(?:with\s+)?[\"']?(?P<text>.+?)[\"']?\s*$",
                    text,
                    re.I,
                )
                entities["field"] = ""
                entities["text"] = (m2.group("text") if m2 else "").strip(" \"'")
        elif intent == "type_text":
            m = re.search(
                r"\b(?:type|enter|write|fill)\s+(?:(?:in|into|the)\s+(?P<field>.+?)\s+with\s+)?[\"']?(?P<text>.+?)[\"']?\s*$",
                text,
                re.I,
            )
            if m:
                if m.groupdict().get("field"):
                    entities["field"] = m.group("field").strip()
                entities["text"] = (m.group("text") or "").strip(" \"'")
            else:
                entities["text"] = ""
        elif intent == "search_web":
            m = re.search(r"\b(?:search(?:\s+for)?|google)\s+(.+)$", text, re.I)
            entities["query"] = (m.group(1) if m else "").strip(" \"'")
        elif intent == "press_key":
            m = re.search(
                r"\b(?:press|hit)\s+(?:key\s+)?(?P<key>enter|tab|escape|esc|space|backspace|ctrl\+[a-z]|alt\+[a-z]|cmd\+[a-z]|win\+[a-z])\b",
                text,
                re.I,
            )
            key = (m.group("key") if m else "enter").lower().replace("esc", "escape")
            entities["key"] = key
        elif intent == "scroll":
            m = re.search(
                r"\bscroll\s+(?P<direction>up|down|left|right)(?:\s+(?P<amount>\d+))?",
                text,
                re.I,
            )
            entities["direction"] = (m.group("direction") if m else "down").lower()
            entities["amount"] = int(m.group("amount")) if m and m.group("amount") else 3
        elif intent == "wait":
            m = re.search(r"(?P<seconds>\d+(?:\.\d+)?)", text)
            entities["seconds"] = float(m.group("seconds")) if m else 1.0
        elif intent == "run_workflow":
            m = re.search(r"\b(?:run|replay|execute)\s+(?:workflow|macro)\s+(.+)$", text, re.I)
            entities["workflow"] = (m.group(1) if m else "").strip(" \"'")
        if analysis.get("spacy_ents"):
            entities["ner"] = analysis["spacy_ents"]
        return entities
