"""Background QThread workers so CV/OCR work never freezes the UI."""

from __future__ import annotations

import random
import time
from typing import Optional

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal


class VisionWorker(QThread):
    """Simulates OpenCV screen / camera capture on a background thread.

    Emits RGB frame arrays at ~15 FPS with placeholder target boxes.
    Replace ``_generate_frame`` with real ``cv2`` / ``mss`` capture later.
    """

    frame_ready = pyqtSignal(object)  # np.ndarray (H, W, 3) RGB
    targets_ready = pyqtSignal(list)  # list[dict] bounding boxes
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, parent=None, fps: float = 15.0) -> None:
        super().__init__(parent)
        self._running = False
        self._fps = fps
        self._frame_w = 960
        self._frame_h = 540
        self._tick = 0

    def run(self) -> None:
        self._running = True
        self.status.emit("Vision worker started")
        interval = 1.0 / max(self._fps, 1.0)

        try:
            while self._running and not self.isInterruptionRequested():
                frame = self._generate_frame()
                boxes = self._generate_targets()
                self.frame_ready.emit(frame)
                self.targets_ready.emit(boxes)
                self._tick += 1
                self._sleep(interval)
        except Exception as exc:  # pragma: no cover - defensive
            self.error.emit(str(exc))
        finally:
            self._running = False
            self.status.emit("Vision worker stopped")

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def _sleep(self, seconds: float) -> None:
        """Interruptible sleep so stop() returns quickly."""
        end = time.monotonic() + seconds
        while self._running and not self.isInterruptionRequested():
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

    def _generate_frame(self) -> np.ndarray:
        """Synthetic dark feed with subtle noise + scanline feel."""
        h, w = self._frame_h, self._frame_w
        base = np.full((h, w, 3), 18, dtype=np.uint8)

        # Soft gradient band that drifts over time
        offset = (self._tick * 3) % h
        for y in range(0, h, 4):
            shade = 22 + ((y + offset) % 40)
            base[y : y + 2, :] = (shade, shade + 4, shade + 8)

        # Noise speckles
        noise = np.random.randint(0, 12, (h, w, 3), dtype=np.uint8)
        frame = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Crosshair center mark
        cx, cy = w // 2, h // 2
        frame[cy - 1 : cy + 2, cx - 18 : cx + 19] = (61, 222, 170)
        frame[cy - 18 : cy + 19, cx - 1 : cx + 2] = (61, 222, 170)

        return frame

    def _generate_targets(self) -> list:
        """Placeholder detection boxes that gently drift."""
        if self._tick % 8 == 0:
            # Occasionally empty so the UI shows "no targets"
            if random.random() < 0.15:
                return []

        t = self._tick
        boxes = [
            {
                "label": "button:Submit",
                "confidence": 0.92 - (t % 20) * 0.002,
                "x": 180 + (t % 40),
                "y": 120 + (t % 25),
                "w": 140,
                "h": 42,
            },
            {
                "label": "text:Confirm",
                "confidence": 0.81,
                "x": 520 + (t % 30),
                "y": 300,
                "w": 160,
                "h": 36,
            },
        ]
        return boxes


class AutomationWorker(QThread):
    """Simulates an automation / OCR task loop.

    Wire real ``pyautogui`` / ``pytesseract`` calls into ``_step`` later.
    """

    log = pyqtSignal(str, str)  # message, level (info|success|warning|error)
    status_changed = pyqtSignal(str)  # idle|active|error
    progress = pyqtSignal(int)  # 0–100
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        task: str = "Click Target",
        ocr_target: str = "",
        confidence: float = 0.8,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.task = task
        self.ocr_target = ocr_target
        self.confidence = confidence
        self._running = False
        self._paused = False

    def run(self) -> None:
        self._running = True
        self._paused = False
        self.status_changed.emit("active")
        self.log.emit(f"Starting task: {self.task}", "info")
        self.log.emit(
            f"OCR target='{self.ocr_target or '(none)'}'  "
            f"confidence≥{self.confidence:.2f}",
            "info",
        )

        steps = [
            ("Capturing screen region", 15),
            ("Running OCR / template match", 40),
            ("Evaluating confidence scores", 65),
            ("Executing automation action", 85),
            ("Verifying result", 100),
        ]

        try:
            for label, pct in steps:
                if not self._running:
                    self.log.emit("Task cancelled by user", "warning")
                    self.status_changed.emit("idle")
                    return

                while self._paused and self._running and not self.isInterruptionRequested():
                    time.sleep(0.05)

                if not self._running or self.isInterruptionRequested():
                    self.log.emit("Task cancelled by user", "warning")
                    self.status_changed.emit("idle")
                    return

                self.log.emit(label + "…", "info")
                self._sleep(0.55 + random.random() * 0.35)
                if not self._running or self.isInterruptionRequested():
                    self.log.emit("Task cancelled by user", "warning")
                    self.status_changed.emit("idle")
                    return
                self.progress.emit(pct)

                # Simulate an occasional soft miss that recovers
                if pct == 40 and random.random() < 0.2:
                    self.log.emit(
                        f"Low match for '{self.ocr_target}' "
                        f"(score={self.confidence - 0.12:.2f})",
                        "warning",
                    )

            result = {
                "task": self.task,
                "ocr_target": self.ocr_target,
                "confidence": self.confidence,
                "matched": True,
                "duration_s": round(2.5 + random.random(), 2),
            }
            self.log.emit(
                f"Task complete — matched target in {result['duration_s']}s",
                "success",
            )
            self.finished_ok.emit(result)
            self.status_changed.emit("idle")
        except Exception as exc:  # pragma: no cover - defensive
            self.log.emit(f"Automation error: {exc}", "error")
            self.failed.emit(str(exc))
            self.status_changed.emit("error")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def _sleep(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while self._running and not self.isInterruptionRequested():
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))


class DummyLogFeeder(QThread):
    """Optional idle heartbeat logs while the suite is open."""

    log = pyqtSignal(str, str)

    def __init__(self, parent=None, interval: float = 12.0) -> None:
        super().__init__(parent)
        self._running = False
        self._interval = interval

    def run(self) -> None:
        self._running = True
        messages = [
            ("Heartbeat — vision pipeline idle", "info"),
            ("Screen capture device ready", "info"),
            ("OCR engine warm cache OK", "info"),
        ]
        i = 0
        while self._running and not self.isInterruptionRequested():
            self._sleep(self._interval)
            if not self._running or self.isInterruptionRequested():
                break
            msg, level = messages[i % len(messages)]
            self.log.emit(msg, level)
            i += 1
        self._running = False

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def _sleep(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while self._running and not self.isInterruptionRequested():
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))
