"""Speech module: faster, more reliable Microphone API + STT."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional


class SpeechService:
    """Capture microphone audio, filter ambient noise, convert speech to text."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        speech_cfg = (config or {}).get("speech", {})
        self.ambient_seconds = float(speech_cfg.get("ambient_seconds", 0.18))
        self.phrase_time_limit = float(speech_cfg.get("phrase_time_limit", 5))
        self.listen_timeout = float(speech_cfg.get("listen_timeout", 5))
        self.energy_threshold = int(speech_cfg.get("energy_threshold", 150))
        self.mic_sensitivity = float(speech_cfg.get("mic_sensitivity", 0.85))
        self.pause_threshold = float(speech_cfg.get("pause_threshold", 0.45))
        self.non_speaking_duration = float(speech_cfg.get("non_speaking_duration", 0.25))
        self.language = str(speech_cfg.get("language", "en-US"))
        self._available = False
        self._sr = None
        self._recognizer = None
        self._mic_index: Optional[int] = None
        self._warmed = False
        self._last_error = ""
        try:
            import speech_recognition as sr
            import pyaudio  # noqa: F401

            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._available = True
            self._configure()
        except ImportError:
            try:
                import speech_recognition as sr

                self._sr = sr
                self._recognizer = sr.Recognizer()
                self._available = True
                self._configure()
            except ImportError:
                self._available = False

    @property
    def available(self) -> bool:
        return bool(self._available and self._recognizer and self._sr)

    @property
    def last_error(self) -> str:
        return self._last_error

    def _configure(self) -> None:
        if not self._recognizer:
            return
        # Higher sensitivity => lower energy threshold
        threshold = max(35, int(self.energy_threshold * (1.7 - self.mic_sensitivity)))
        self._recognizer.energy_threshold = threshold
        self._recognizer.dynamic_energy_threshold = False  # more predictable for commands
        self._recognizer.pause_threshold = self.pause_threshold
        self._recognizer.non_speaking_duration = min(
            self.non_speaking_duration, self.pause_threshold - 0.05
        )
        self._recognizer.operation_timeout = 10
        self._recognizer.phrase_threshold = 0.2

    def set_sensitivity(self, value: float) -> None:
        self.mic_sensitivity = max(0.15, min(1.0, float(value)))
        self._configure()

    def _pick_microphone_index(self) -> Optional[int]:
        try:
            names = list(self._sr.Microphone.list_microphone_names() or [])
        except Exception as exc:
            self._last_error = str(exc)
            return None
        if not names:
            return None
        ranked = []
        for i, name in enumerate(names):
            n = (name or "").lower()
            score = 0
            if "default" in n:
                score += 50
            if "pulse" in n or "pipewire" in n:
                score += 40
            if any(k in n for k in ("usb", "headset", "microphone", "mic", "array")):
                score += 30
            if any(k in n for k in ("monitor", "loopback", "null", "dummy")):
                score -= 80
            ranked.append((score, i, name))
        ranked.sort(reverse=True)
        return ranked[0][1] if ranked else 0

    def warm_up(self) -> bool:
        """Open mic briefly so the first real listen is faster."""
        if not self.available or self._warmed:
            return self._warmed
        try:
            if self._mic_index is None:
                self._mic_index = self._pick_microphone_index()
            with self._sr.Microphone(device_index=self._mic_index) as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.12)
            self._warmed = True
            return True
        except Exception as exc:
            self._last_error = str(exc)
            return False

    def listen_once(self, status_cb: Optional[Callable[[str], None]] = None) -> str:
        if not self.available:
            raise RuntimeError(
                "SpeechRecognition/PyAudio not available. Type your command instead."
            )

        sr = self._sr
        recognizer = self._recognizer
        self._configure()
        emit = status_cb or (lambda _m: None)

        if self._mic_index is None:
            self._mic_index = self._pick_microphone_index()
        if self._mic_index is None:
            raise RuntimeError(
                "No microphone found. Plug in a mic or type your command."
            )

        audio = None
        try:
            emit("Opening microphone…")
            audio = self._capture_audio(recognizer, emit)
        except AttributeError as exc:
            raise RuntimeError(
                "PyAudio is required for the Microphone API. Install PyAudio or type your command."
            ) from exc
        except OSError as exc:
            self._last_error = str(exc)
            raise RuntimeError(
                f"Microphone not available ({exc}). Type your command instead."
            ) from exc
        except sr.WaitTimeoutError as exc:
            raise RuntimeError(
                "Didn’t catch speech. Click Mic, wait for “Speak now…”, then talk clearly."
            ) from exc

        emit("Transcribing…")
        text = self._transcribe(audio)
        text = " ".join((text or "").strip().split())
        if not text:
            raise RuntimeError("Empty transcription. Please try again.")
        return text

    def _capture_audio(self, recognizer, emit):
        """Capture one phrase; fall back if 16kHz is unsupported by the device."""
        sr = self._sr
        attempts = (
            {"device_index": self._mic_index, "sample_rate": 16000},
            {"device_index": self._mic_index},
        )
        last_exc = None
        for kwargs in attempts:
            try:
                with sr.Microphone(**kwargs) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=self.ambient_seconds)
                    lo = max(30, int(self.energy_threshold * 0.35))
                    hi = max(lo + 20, int(self.energy_threshold * 2.2))
                    recognizer.energy_threshold = min(max(recognizer.energy_threshold, lo), hi)
                    emit("Speak now…")
                    return recognizer.listen(
                        source,
                        timeout=self.listen_timeout,
                        phrase_time_limit=self.phrase_time_limit,
                    )
            except OSError as exc:
                last_exc = exc
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError("Could not open microphone.")

    def _transcribe(self, audio) -> str:
        sr = self._sr
        recognizer = self._recognizer
        errors = []

        # Pass 1: Google STT
        try:
            return recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError as exc:
            errors.append("unclear audio")
            # Pass 2: slightly boosted energy re-listen is not possible on same audio;
            # try show_all alternatives if present
            try:
                result = recognizer.recognize_google(
                    audio, language=self.language, show_all=True
                )
                if isinstance(result, dict):
                    alts = result.get("alternative") or []
                    if alts:
                        best = alts[0].get("transcript") or ""
                        if best.strip():
                            return best.strip()
            except Exception as exc2:
                errors.append(str(exc2))
            raise RuntimeError(
                "Could not understand audio. Speak closer/clearer, then try again."
            ) from exc
        except sr.RequestError as exc:
            # Offline fallback if pocketsphinx installed
            try:
                return recognizer.recognize_sphinx(audio)
            except Exception:
                raise RuntimeError(
                    f"Speech service error: {exc}. Check internet, then retry — or type the command."
                ) from exc
