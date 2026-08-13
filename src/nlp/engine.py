"""NLP Engine: spaCy + NLTK for intent classification and entity extraction."""

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
    tokens: List[str] = field(default_factory=list)
    lemmas: List[str] = field(default_factory=list)
    pos_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Intent verb/keyword map used after spaCy/NLTK tokenization
_INTENT_KEYWORDS: Dict[str, Tuple[str, float]] = {
    "open": ("open_app", 0.92),
    "launch": ("open_app", 0.92),
    "start": ("open_app", 0.90),
    "click": ("click_text", 0.88),
    "tap": ("click_text", 0.86),
    "type": ("type_text", 0.88),
    "enter": ("type_text", 0.84),
    "write": ("type_text", 0.84),
    "fill": ("type_text", 0.84),
    "search": ("search_web", 0.90),
    "google": ("search_web", 0.88),
    "scroll": ("scroll", 0.90),
    "wait": ("wait", 0.93),
    "pause": ("wait", 0.90),
    "sleep": ("wait", 0.90),
    "press": ("press_key", 0.86),
    "hit": ("press_key", 0.84),
    "run": ("run_workflow", 0.90),
    "replay": ("run_workflow", 0.92),
    "execute": ("run_workflow", 0.90),
}

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

_KEY_NAMES = {
    "enter",
    "tab",
    "escape",
    "esc",
    "space",
    "backspace",
}


class NLPEngine:
    """Intent classification & entity extraction using spaCy and NLTK."""

    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        self._spacy_model = spacy_model
        self._nlp = None
        self._nltk_ready = False
        self._init_spacy()
        self._init_nltk()

    def _init_spacy(self) -> None:
        try:
            import spacy

            try:
                self._nlp = spacy.load(self._spacy_model)
            except OSError:
                # Model missing — try blank English pipeline for tokenization
                self._nlp = spacy.blank("en")
        except ImportError:
            self._nlp = None

    def _init_nltk(self) -> None:
        try:
            import nltk

            for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"):
                try:
                    if pkg.startswith("averaged_perceptron"):
                        nltk.data.find(f"taggers/{pkg}")
                    else:
                        nltk.data.find(f"tokenizers/{pkg}")
                except LookupError:
                    nltk.download(pkg, quiet=True)
            self._nltk_ready = True
        except Exception:
            self._nltk_ready = False

    def analyze(self, text: str) -> Dict[str, Any]:
        """Tokenize + POS + lemmas via spaCy, with NLTK fallback."""
        cleaned = " ".join(text.strip().split())
        tokens: List[str] = []
        lemmas: List[str] = []
        pos_tags: List[str] = []
        noun_chunks: List[str] = []
        spacy_ents: List[Dict[str, str]] = []

        if self._nlp is not None and cleaned:
            doc = self._nlp(cleaned)
            tokens = [t.text for t in doc]
            # blank model may lack lemmas/pos — fill from NLTK if needed
            if any(getattr(t, "pos_", "") for t in doc):
                lemmas = [t.lemma_.lower() for t in doc]
                pos_tags = [t.pos_ for t in doc]
            try:
                noun_chunks = [c.text for c in doc.noun_chunks]
            except Exception:
                noun_chunks = []
            spacy_ents = [{"text": e.text, "label": e.label_} for e in getattr(doc, "ents", [])]

        if not tokens and self._nltk_ready and cleaned:
            from nltk.tokenize import word_tokenize

            tokens = word_tokenize(cleaned)

        if (not pos_tags or not lemmas) and self._nltk_ready and tokens:
            from nltk import pos_tag

            tagged = pos_tag(tokens)
            if not pos_tags:
                pos_tags = [p for _, p in tagged]
            if not lemmas:
                lemmas = [t.lower() for t, _ in tagged]

        if not tokens and cleaned:
            tokens = re.findall(r"[\w']+|[.,!?;]", cleaned)
            lemmas = [t.lower() for t in tokens]
            pos_tags = ["X"] * len(tokens)

        return {
            "tokens": tokens,
            "lemmas": lemmas,
            "pos_tags": pos_tags,
            "noun_chunks": noun_chunks,
            "spacy_ents": spacy_ents,
        }

    def tokenize(self, text: str) -> List[str]:
        return self.analyze(text)["tokens"]

    def parse(self, text: str) -> ParsedCommand:
        raw = " ".join(text.strip().split())
        if not raw:
            return ParsedCommand(raw_text=text, intent="unknown", confidence=0.0)

        # Multi-step commands: "Open Chrome and search weather"
        if re.search(r"\band\b", raw, flags=re.I):
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
            analysis = self.analyze(raw)
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
        analysis = self.analyze(text)
        lemmas = analysis["lemmas"] or [t.lower() for t in analysis["tokens"]]
        tokens = analysis["tokens"]
        lower = text.lower().strip()

        intent, confidence = self._classify_intent(lemmas, lower)
        entities = self._extract_entities(intent, text, tokens, lemmas, analysis)

        return ParsedCommand(
            raw_text=text,
            intent=intent,
            entities=entities,
            confidence=confidence,
            tokens=tokens,
            lemmas=lemmas,
            pos_tags=analysis["pos_tags"],
        )

    def _classify_intent(self, lemmas: List[str], lower: str) -> Tuple[str, float]:
        # Workflow phrases first
        if re.search(r"\b(run|replay|execute)\s+(workflow|macro)\b", lower):
            return "run_workflow", 0.95
        if re.search(r"\bpress\s+(key\s+)?(enter|tab|escape|esc|space|backspace|ctrl\+|alt\+|cmd\+|win\+)", lower):
            return "press_key", 0.9
        if "scroll" in lemmas or lower.startswith("scroll"):
            return "scroll", 0.9
        if any(w in lemmas for w in ("wait", "pause", "sleep")):
            return "wait", 0.93
        if any(w in lemmas for w in ("search", "google")):
            return "search_web", 0.9
        if any(w in lemmas for w in ("open", "launch", "start")):
            return "open_app", 0.92
        if any(w in lemmas for w in ("click", "tap")):
            return "click_text", 0.88
        if any(w in lemmas for w in ("type", "write", "fill")) or (
            "enter" in lemmas and not re.search(r"\bpress\s+enter\b", lower)
        ):
            return "type_text", 0.86

        for lemma in lemmas:
            if lemma in _INTENT_KEYWORDS:
                return _INTENT_KEYWORDS[lemma]
        return "unknown", 0.2

    def _extract_entities(
        self,
        intent: str,
        text: str,
        tokens: List[str],
        lemmas: List[str],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        lower = text.lower().strip()

        if intent == "open_app":
            m = re.search(r"\b(?:open|launch|start)\s+(.+)$", text, re.I)
            app = (m.group(1) if m else "").strip()
            # Refine with spaCy noun chunks / NER when they look like app names
            candidates = []
            for chunk in analysis.get("noun_chunks") or []:
                cleaned = re.sub(
                    r"^(open|launch|start)\s+", "", chunk.strip(), flags=re.I
                ).strip()
                if cleaned:
                    candidates.append(cleaned)
            for ent in analysis.get("spacy_ents") or []:
                if ent.get("text"):
                    candidates.append(ent["text"])
            for cand in candidates:
                key = cand.lower().strip()
                if key in _APP_ALIASES or key.split()[0] in _APP_ALIASES:
                    app = cand
                    break
            app_key = app.lower().strip()
            if app_key in _APP_ALIASES:
                entities["app"] = _APP_ALIASES[app_key]
            elif app_key:
                first = app_key.split()[0]
                entities["app"] = _APP_ALIASES.get(first, first)
            else:
                entities["app"] = ""

        elif intent == "click_text":
            m = re.search(r"\b(?:click|tap)\s+(?:(?:on|the)\s+)?(.+)$", text, re.I)
            entities["element"] = (m.group(1) if m else "").strip(" \"'")

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
            m = re.search(r"\bscroll\s+(?P<direction>up|down|left|right)(?:\s+(?P<amount>\d+))?", text, re.I)
            entities["direction"] = (m.group("direction") if m else "down").lower()
            entities["amount"] = int(m.group("amount")) if m and m.group("amount") else 3

        elif intent == "wait":
            m = re.search(r"(?P<seconds>\d+(?:\.\d+)?)", text)
            entities["seconds"] = float(m.group("seconds")) if m else 1.0

        elif intent == "run_workflow":
            m = re.search(r"\b(?:run|replay|execute)\s+(?:workflow|macro)\s+(.+)$", text, re.I)
            entities["workflow"] = (m.group(1) if m else "").strip(" \"'")

        # Attach spaCy NER labels for auditing
        if analysis.get("spacy_ents"):
            entities["ner"] = analysis["spacy_ents"]
        return entities
