"""End-to-end command execution: NLP → Vision → Automation → Audit."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from src.automation.engine import AutomationEngine
from src.db.database import Database
from src.db.repositories import NLPCommandRepository, UserConfRepository
from src.logging_audit.service import AuditService
from src.nlp.engine import NLPEngine, ParsedCommand
from src.vision.engine import VisionEngine
from src.workflows.service import WorkflowService


class AutomationPipeline:
    def __init__(
        self,
        config: Dict[str, Any],
        db: Database,
        *,
        nlp: Optional[NLPEngine] = None,
        vision: Optional[VisionEngine] = None,
        automation: Optional[AutomationEngine] = None,
        workflows: Optional[WorkflowService] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self.config = config
        self.db = db
        self.nlp = nlp or NLPEngine(config.get("nlp", {}).get("spacy_model", "en_core_web_sm"))
        self.vision = vision or VisionEngine(config)
        self.automation = automation or AutomationEngine(config)
        self.workflows = workflows or WorkflowService(db)
        self.audit = audit or AuditService(db)
        self.nlp_repo = NLPCommandRepository(db)
        self.conf_repo = UserConfRepository(db)
        self._stop_requested = False
        self.last_frame = None
        self.last_boxes: List[Dict[str, Any]] = []

    def request_stop(self) -> None:
        self._stop_requested = True

    def apply_user_settings(self, user_id: int) -> None:
        conf = self.conf_repo.get_map(user_id)
        if not conf:
            return
        self.automation.set_dry_run(str(conf.get("dry_run", "0")) in ("1", "true", "True"))
        self.automation.failsafe = str(conf.get("failsafe", "1")) in ("1", "true", "True")
        self.automation.pause_seconds = float(conf.get("pause_seconds", 0.12))
        if self.automation._pyautogui is not None:
            self.automation._pyautogui.PAUSE = self.automation.pause_seconds
            self.automation._pyautogui.FAILSAFE = self.automation.failsafe

    def run_text_command(
        self,
        text: str,
        *,
        user_id: Optional[int] = None,
        source: str = "text",
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        self._stop_requested = False
        self._status_cb = status_cb or (lambda _m: None)
        started = time.perf_counter()
        emit = self._status_cb

        emit("Parsing command…")
        parsed = self.nlp.parse(text)
        command_id = self.nlp_repo.create(
            raw_text=text,
            parsed_intent=parsed.intent,
            entities=parsed.entities,
            confidence=parsed.confidence,
            source=source,
            user_id=user_id,
        )

        if parsed.intent == "unknown" and not parsed.steps:
            duration = int((time.perf_counter() - started) * 1000)
            log_id = self.audit.log_execution(
                status="Failed",
                duration_ms=duration,
                error_message="Could not understand command",
                details=parsed.to_dict(),
                user_id=user_id,
                command_id=command_id,
            )
            return {
                "ok": False,
                "parsed": parsed.to_dict(),
                "command_id": command_id,
                "log_id": log_id,
                "error": "Could not understand command",
            }

        # Special: run named workflow
        if parsed.intent == "run_workflow" and user_id is not None:
            return self.run_workflow_by_name(
                user_id,
                parsed.entities.get("workflow", ""),
                command_id=command_id,
                status_cb=status_cb,
            )

        actions_done: List[Dict[str, Any]] = []
        captures: List[str] = []
        error: Optional[str] = None

        try:
            steps = parsed.steps or [
                {
                    "intent": parsed.intent,
                    "entities": parsed.entities,
                    "confidence": parsed.confidence,
                }
            ]
            for step in steps:
                if self._stop_requested:
                    error = "Stopped by user"
                    break
                emit(f"Executing: {step.get('intent')}")
                result = self._execute_step(step, user_id=user_id)
                actions_done.append(result)
                if result.get("capture_path"):
                    captures.append(result["capture_path"])
                if result.get("boxes") is not None:
                    self.last_boxes = result.get("boxes") or []
                if self.vision.last_frame is not None:
                    self.last_frame = self.vision.last_frame
        except Exception as exc:
            error = str(exc)

        duration = int((time.perf_counter() - started) * 1000)
        status = "Failed" if error else "Success"
        log_id = self.audit.log_execution(
            status=status,
            duration_ms=duration,
            error_message=error or "",
            details={"parsed": parsed.to_dict(), "actions": actions_done},
            user_id=user_id,
            command_id=command_id,
            capture_paths=captures,
        )
        emit("Done" if not error else f"Error: {error}")
        return {
            "ok": error is None,
            "parsed": parsed.to_dict(),
            "actions": actions_done,
            "command_id": command_id,
            "log_id": log_id,
            "error": error,
            "boxes": self.last_boxes,
            "dry_run": self.automation.dry_run,
        }

    def run_workflow(
        self,
        workflow_id: int,
        *,
        user_id: Optional[int] = None,
        command_id: Optional[int] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        self._stop_requested = False
        emit = status_cb or (lambda _m: None)
        started = time.perf_counter()
        wf = self.workflows.get_workflow(workflow_id)
        if not wf:
            return {"ok": False, "error": "Workflow not found"}

        actions_done: List[Dict[str, Any]] = []
        captures: List[str] = []
        error: Optional[str] = None
        try:
            for task in wf.get("tasks", []):
                if self._stop_requested:
                    error = "Stopped by user"
                    break
                step = WorkflowService.task_to_step(task)
                emit(f"Workflow step: {step['intent']}")
                result = self._execute_step(step, user_id=user_id)
                actions_done.append(result)
                if result.get("capture_path"):
                    captures.append(result["capture_path"])
        except Exception as exc:
            error = str(exc)

        duration = int((time.perf_counter() - started) * 1000)
        status = "Failed" if error else "Success"
        log_id = self.audit.log_execution(
            status=status,
            duration_ms=duration,
            error_message=error or "",
            details={"workflow_id": workflow_id, "actions": actions_done},
            user_id=user_id,
            workflow_id=workflow_id,
            command_id=command_id,
            capture_paths=captures,
        )
        return {
            "ok": error is None,
            "actions": actions_done,
            "log_id": log_id,
            "error": error,
            "dry_run": self.automation.dry_run,
            "workflow": wf,
        }

    def run_workflow_by_name(
        self,
        user_id: int,
        name: str,
        *,
        command_id: Optional[int] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        wf = self.workflows.find_by_name(user_id, name)
        if not wf:
            started_error = f"Workflow not found: {name}"
            log_id = self.audit.log_execution(
                status="Failed",
                duration_ms=0,
                error_message=started_error,
                user_id=user_id,
                command_id=command_id,
            )
            return {"ok": False, "error": started_error, "log_id": log_id}
        return self.run_workflow(
            wf["workflow_id"],
            user_id=user_id,
            command_id=command_id,
            status_cb=status_cb,
        )

    def _execute_step(
        self, step: Dict[str, Any], *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        intent = step.get("intent", "unknown")
        entities = step.get("entities") or {}
        result: Dict[str, Any] = {"intent": intent, "entities": entities}

        if intent == "open_app":
            result["automation"] = self.automation.open_app(entities.get("app", ""))
            follow = entities.get("follow_up")
            if follow:
                follow_parsed = self.nlp.parse(follow)
                for sub in follow_parsed.steps:
                    sub_res = self._execute_step(sub, user_id=user_id)
                    result.setdefault("follow_ups", []).append(sub_res)
            return result

        if intent == "type_text":
            result["automation"] = self.automation.type_text(entities.get("text", ""))
            return result

        if intent == "press_key":
            result["automation"] = self.automation.press(entities.get("key", "enter"))
            return result

        if intent == "scroll":
            result["automation"] = self.automation.scroll(
                entities.get("direction", "down"),
                int(entities.get("amount", 3)),
            )
            return result

        if intent == "wait":
            result["automation"] = self.automation.wait(float(entities.get("seconds", 1)))
            return result

        if intent == "search_web":
            query = entities.get("query", "")
            # Real Google search via browser URL (fast + reliable)
            result["automation"] = self.automation.search_google(query)
            return result

        if intent == "click_text":
            element = entities.get("element", "")
            if entities.get("x") is not None and entities.get("y") is not None:
                x, y = int(entities["x"]), int(entities["y"])
                result["automation"] = self.automation.click(x, y)
                return result
            emit = getattr(self, "_status_cb", None) or (lambda _m: None)
            emit(f"Looking for “{element}” on screen…")
            frame = self.vision.capture_screen()
            detection = self.vision.locate(element, frame=frame)
            result["detection"] = {
                "found": detection.found,
                "x": detection.x,
                "y": detection.y,
                "method": detection.method,
                "confidence": detection.confidence,
                "label": detection.label,
            }
            result["boxes"] = detection.boxes
            path = self.vision.save_capture(frame, label=f"click_{element}", boxes=detection.boxes)
            result["capture_path"] = path
            if not detection.found:
                # Retry once after a short wait (UI may still be loading)
                self.automation.wait(0.6)
                frame = self.vision.capture_screen()
                detection = self.vision.locate(element, frame=frame)
                result["detection_retry"] = {
                    "found": detection.found,
                    "x": detection.x,
                    "y": detection.y,
                    "method": detection.method,
                    "confidence": detection.confidence,
                }
                result["boxes"] = detection.boxes
                if not detection.found:
                    if self.automation.dry_run:
                        h, w = frame.shape[:2]
                        result["automation"] = self.automation.click(w // 2, h // 2)
                        result["note"] = "Element not found; dry-run used screen center"
                        return result
                    raise RuntimeError(f"Could not find on-screen element: {element}")
            result["automation"] = self.automation.click(detection.x, detection.y)
            return result

        if intent == "run_workflow":
            name = entities.get("workflow", "")
            if user_id is None:
                raise RuntimeError("Login required to run workflows")
            nested = self.run_workflow_by_name(user_id, name)
            result["nested"] = nested
            if not nested.get("ok"):
                raise RuntimeError(nested.get("error") or "Workflow failed")
            return result

        raise RuntimeError(f"Unsupported intent: {intent}")

    def capture_preview(self) -> Dict[str, Any]:
        frame = self.vision.capture_screen()
        self.last_frame = frame
        path = self.vision.save_capture(frame, label="preview")
        return {"frame": frame, "path": path, "boxes": []}
