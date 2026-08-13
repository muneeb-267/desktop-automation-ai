"""Microphone capture and speech-to-text conversion."""

from __future__ import annotations

from typing import Any, Dict, Optional


class SpeechService:
    """Wraps SpeechRecognition with ambient noise filtering."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        speech_cfg = (config or {}).get("speech", {})
        self.ambient_seconds = float(speech_cfg.get("ambient_seconds", 0.4))
        self.phrase_time_limit = float(speech_cfg.get("phrase_time_limit", 8))
        self.energy_threshold = int(speech_cfg.get("energy_threshold", 300))
        self._available = False
        self._sr = None
        try:
            import speech_recognition as sr

            self._sr = sr
            self._available = True
        except ImportError:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def listen_once(self) -> str:
        """Capture one utterance and return transcribed text.

        Raises RuntimeError when mic / backend is unavailable.
        """
        if not self._sr:
            raise RuntimeError(
                "SpeechRecognition is not installed. Type your command instead."
            )
        sr = self._sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = self.energy_threshold
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=self.ambient_seconds)
                audio = recognizer.listen(source, phrase_time_limit=self.phrase_time_limit)
        except OSError as exc:
            raise RuntimeError(
                f"Microphone not available ({exc}). Type your command instead."
            ) from exc

        # Prefer offline Sphinx if present; otherwise Google free web API.
        try:
            return recognizer.recognize_sphinx(audio)
        except Exception:
            pass
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError as exc:
            raise RuntimeError("Could not understand audio. Please try again.") from exc
        except sr.RequestError as exc:
            raise RuntimeError(
                f"Speech service error: {exc}. Check internet or type your command."
            ) from exc
