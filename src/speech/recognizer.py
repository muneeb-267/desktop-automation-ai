"""Speech module: Microphone API + Speech-to-Text (SpeechRecognition / PyAudio)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class SpeechService:
    """Capture microphone audio, filter ambient noise, convert speech to text."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        speech_cfg = (config or {}).get("speech", {})
        self.ambient_seconds = float(speech_cfg.get("ambient_seconds", 0.4))
        self.phrase_time_limit = float(speech_cfg.get("phrase_time_limit", 8))
        self.energy_threshold = int(speech_cfg.get("energy_threshold", 300))
        self.mic_sensitivity = float(speech_cfg.get("mic_sensitivity", 0.7))
        self._available = False
        self._sr = None
        try:
            import speech_recognition as sr  # noqa: F401
            import pyaudio  # noqa: F401

            self._sr = __import__("speech_recognition")
            self._available = True
        except ImportError:
            # SpeechRecognition without PyAudio still marks library present for typed path,
            # but listen_once requires Microphone (PyAudio).
            try:
                import speech_recognition as sr

                self._sr = sr
                self._available = True
            except ImportError:
                self._available = False
                self._sr = None

    @property
    def available(self) -> bool:
        return self._available

    def listen_once(self) -> str:
        """Microphone API capture → ambient filter → Speech-to-Text string."""
        if not self._sr:
            raise RuntimeError(
                "SpeechRecognition is not installed. Type your command instead."
            )

        sr = self._sr
        recognizer = sr.Recognizer()
        # Sensitivity: higher mic_sensitivity => lower energy threshold
        recognizer.energy_threshold = max(
            50, int(self.energy_threshold * (1.5 - self.mic_sensitivity))
        )
        recognizer.dynamic_energy_threshold = True

        try:
            # Project stack: Microphone API via SpeechRecognition + PyAudio
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(
                    source, duration=self.ambient_seconds
                )
                audio = recognizer.listen(
                    source,
                    timeout=10,
                    phrase_time_limit=self.phrase_time_limit,
                )
        except AttributeError as exc:
            raise RuntimeError(
                "PyAudio is required for the Microphone API. "
                "Install PyAudio, then try Mic again — or type your command."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Microphone not available ({exc}). Type your command instead."
            ) from exc
        except sr.WaitTimeoutError as exc:
            raise RuntimeError(
                "No speech heard. Speak after clicking Mic, or type your command."
            ) from exc

        # Speech-to-Text conversion
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError as exc:
            raise RuntimeError("Could not understand audio. Please try again.") from exc
        except sr.RequestError as exc:
            raise RuntimeError(
                f"Speech-to-Text service error: {exc}. Check internet or type your command."
            ) from exc
