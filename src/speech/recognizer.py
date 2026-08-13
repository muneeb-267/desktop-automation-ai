"""Speech module: Microphone API + Speech-to-Text (faster, more reliable)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class SpeechService:
    """Capture microphone audio, filter ambient noise, convert speech to text."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        speech_cfg = (config or {}).get("speech", {})
        self.ambient_seconds = float(speech_cfg.get("ambient_seconds", 0.25))
        self.phrase_time_limit = float(speech_cfg.get("phrase_time_limit", 6))
        self.listen_timeout = float(speech_cfg.get("listen_timeout", 6))
        self.energy_threshold = int(speech_cfg.get("energy_threshold", 200))
        self.mic_sensitivity = float(speech_cfg.get("mic_sensitivity", 0.75))
        self.pause_threshold = float(speech_cfg.get("pause_threshold", 0.55))
        self.non_speaking_duration = float(speech_cfg.get("non_speaking_duration", 0.35))
        self._available = False
        self._sr = None
        self._recognizer = None
        self._calibrated = False
        self._mic_index: Optional[int] = None
        try:
            import speech_recognition as sr
            import pyaudio  # noqa: F401

            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._available = True
            self._prepare_recognizer()
        except ImportError:
            try:
                import speech_recognition as sr

                self._sr = sr
                self._recognizer = sr.Recognizer()
                self._available = True
                self._prepare_recognizer()
            except ImportError:
                self._available = False

    @property
    def available(self) -> bool:
        return self._available and self._recognizer is not None

    def _prepare_recognizer(self) -> None:
        if not self._recognizer:
            return
        # Higher sensitivity => lower energy threshold (easier to trigger)
        base = max(40, int(self.energy_threshold * (1.6 - self.mic_sensitivity)))
        self._recognizer.energy_threshold = base
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.dynamic_energy_adjustment_damping = 0.12
        self._recognizer.pause_threshold = self.pause_threshold
        self._recognizer.non_speaking_duration = self.non_speaking_duration
        self._recognizer.operation_timeout = 12

    def set_sensitivity(self, value: float) -> None:
        self.mic_sensitivity = max(0.1, min(1.0, float(value)))
        self._prepare_recognizer()

    def _pick_microphone_index(self) -> Optional[int]:
        try:
            names = self._sr.Microphone.list_microphone_names()
        except Exception:
            return None
        preferred = ("default", "pulse", "pipewire", "usb", "headset", "mic")
        lowered = [(i, (n or "").lower()) for i, n in enumerate(names)]
        for key in preferred:
            for i, name in lowered:
                if key in name:
                    return i
        return 0 if names else None

    def listen_once(self, status_cb=None) -> str:
        """Microphone API capture → ambient filter → Speech-to-Text string."""
        if not self._sr or not self._recognizer:
            raise RuntimeError(
                "SpeechRecognition is not installed. Type your command instead."
            )

        sr = self._sr
        recognizer = self._recognizer
        self._prepare_recognizer()
        emit = status_cb or (lambda _m: None)

        if self._mic_index is None:
            self._mic_index = self._pick_microphone_index()

        try:
            emit("Calibrating mic…")
            with sr.Microphone(device_index=self._mic_index) as source:
                # Fast ambient calibration; only longer on first listen
                duration = self.ambient_seconds if self._calibrated else max(0.35, self.ambient_seconds)
                recognizer.adjust_for_ambient_noise(source, duration=duration)
                self._calibrated = True
                # Keep threshold responsive after calibration
                recognizer.energy_threshold = max(
                    40,
                    min(recognizer.energy_threshold, int(self.energy_threshold * 1.8)),
                )
                emit("Speak now…")
                audio = recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
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
                "No speech heard. Click Mic, wait for “Speak now…”, then talk."
            ) from exc

        emit("Transcribing…")
        try:
            # show_all=False is faster; language hint helps accuracy
            return recognizer.recognize_google(audio, language="en-US")
        except sr.UnknownValueError as exc:
            raise RuntimeError("Could not understand audio. Please try again.") from exc
        except sr.RequestError as exc:
            raise RuntimeError(
                f"Speech-to-Text service error: {exc}. Check internet or type your command."
            ) from exc
