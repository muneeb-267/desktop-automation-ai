"""Background QThread workers so NLP/CV/automation never freeze the UI."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal


class CommandWorker(QThread):
    status = pyqtSignal(str)
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)
    frame_ready = pyqtSignal(object, list)

    def __init__(
        self,
        pipeline,
        text: str,
        user_id: Optional[int],
        source: str = "text",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pipeline = pipeline
        self.text = text
        self.user_id = user_id
        self.source = source

    def run(self) -> None:
        try:
            result = self.pipeline.run_text_command(
                self.text,
                user_id=self.user_id,
                source=self.source,
                status_cb=self.status.emit,
            )
            frame = self.pipeline.last_frame
            boxes = result.get("boxes") or self.pipeline.last_boxes or []
            if frame is not None:
                self.frame_ready.emit(frame, boxes)
            if result.get("ok"):
                self.finished_ok.emit(result)
            else:
                self.failed.emit(result.get("error") or "Command failed")
                self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self) -> None:
        self.pipeline.request_stop()


class WorkflowWorker(QThread):
    status = pyqtSignal(str)
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, pipeline, workflow_id: int, user_id: Optional[int], parent=None) -> None:
        super().__init__(parent)
        self.pipeline = pipeline
        self.workflow_id = workflow_id
        self.user_id = user_id

    def run(self) -> None:
        try:
            result = self.pipeline.run_workflow(
                self.workflow_id,
                user_id=self.user_id,
                status_cb=self.status.emit,
            )
            if result.get("ok"):
                self.finished_ok.emit(result)
            else:
                self.failed.emit(result.get("error") or "Workflow failed")
                self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self) -> None:
        self.pipeline.request_stop()


class SpeechWorker(QThread):
    transcribed = pyqtSignal(str)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, speech_service, parent=None) -> None:
        super().__init__(parent)
        self.speech_service = speech_service

    def run(self) -> None:
        try:
            self.status.emit("Listening…")
            text = self.speech_service.listen_once()
            self.transcribed.emit(text)
        except Exception as exc:
            self.failed.emit(str(exc))


class CaptureWorker(QThread):
    frame_ready = pyqtSignal(object, list)
    failed = pyqtSignal(str)

    def __init__(self, pipeline, parent=None) -> None:
        super().__init__(parent)
        self.pipeline = pipeline

    def run(self) -> None:
        try:
            preview = self.pipeline.capture_preview()
            self.frame_ready.emit(preview["frame"], preview.get("boxes") or [])
        except Exception as exc:
            self.failed.emit(str(exc))
