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
        nlp_cfg = config.get("nlp", {})
        self.nlp = nlp or NLPEngine(
            nlp_cfg.get("spacy_model", "en_core_web_sm"),
            min_confidence=float(nlp_cfg.get("min_confidence", 0.45)),
        )
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
        self.automation.pause_seconds = float(conf.get("pause_seconds", 0.04))
        if self.automation._pyautogui is not None:
            self.automation._pyautogui.PAUSE = self.automation.pause_seconds
            self.automation._pyautogui.FAILSAFE = self.automation.failsafe

    def _ensure_live_automation(self) -> None:
        if self.automation.dry_run:
            return
        if self.automation._pyautogui is None:
            raise RuntimeError(
                "PyAutoGUI is unavailable — cannot run live mouse/keyboard automation. "
                "Enable dry-run in Settings or install PyAutoGUI."
            )

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

        # Graceful invalid / ambiguous input — never crash the UI
        if parsed.intent == "unknown" or (
            not parsed.steps
            and parsed.intent not in (
                "open_app",
                "click_text",
                "click_button",
                "fill_form",
                "type_text",
                "search_web",
                "press_key",
                "scroll",
                "wait",
                "run_workflow",
            )
        ):
            duration = int((time.perf_counter() - started) * 1000)
            msg = (
                "Could not understand that command. Try: "
                "Open Chrome · Click button Login · Fill username with alice · Search weather"
            )
            log_id = self.audit.log_execution(
                status="Failed",
                duration_ms=duration,
                error_message=msg,
                details=parsed.to_dict(),
                user_id=user_id,
                command_id=command_id,
            )
            emit(msg)
            return {
                "ok": False,
                "parsed": parsed.to_dict(),
                "command_id": command_id,
                "log_id": log_id,
                "error": msg,
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
            self._ensure_live_automation()
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
                if step.get("intent") == "unknown":
                    error = (
                        "Unrecognized step — please rephrase. "
                        "Supported: open, click, fill, type, search, press, scroll, wait."
                    )
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
        if error and "Stopped" in error:
            status = "Exception"
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
            log_id = self.audit.log_execution(
                status="Failed",
                duration_ms=0,
                error_message="Workflow not found",
                user_id=user_id,
                command_id=command_id,
                workflow_id=workflow_id,
            )
            return {"ok": False, "error": "Workflow not found", "log_id": log_id}
        if user_id is not None and int(wf.get("user_id") or 0) != int(user_id):
            return {"ok": False, "error": "Workflow not found for this user"}

        actions_done: List[Dict[str, Any]] = []
        captures: List[str] = []
        error: Optional[str] = None
        try:
            self._ensure_live_automation()
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
        if error and "Stopped" in error:
            status = "Exception"
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

    def _click_element(self, element: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"intent": "click_button", "entities": entities}
        if entities.get("x") is not None and entities.get("y") is not None:
            x, y = int(entities["x"]), int(entities["y"])
            result["automation"] = self.automation.click(x, y)
            return result
        emit = getattr(self, "_status_cb", None) or (lambda _m: None)
        emit(f"Looking for “{element}” on screen…")
        frame = self.vision.capture_screen()
        if not self.vision.last_capture_ok:
            raise RuntimeError(
                f"Screen capture failed: {self.vision.last_capture_error or 'unknown error'}"
            )
        prefer = "template" if entities.get("prefer") == "template" else "ocr"
        detection = self.vision.locate(element, prefer=prefer, frame=frame)
        result["detection"] = {
            "found": detection.found,
            "x": detection.x,
            "y": detection.y,
            "width": detection.width,
            "height": detection.height,
            "method": detection.method,
            "confidence": detection.confidence,
            "label": detection.label,
        }
        result["boxes"] = detection.boxes
        if not detection.found:
            self.automation.wait(0.2)
            frame = self.vision.capture_screen()
            detection = self.vision.locate(element, prefer=prefer, frame=frame)
            result["detection_retry"] = {
                "found": detection.found,
                "x": detection.x,
                "y": detection.y,
                "method": detection.method,
                "confidence": detection.confidence,
            }
            result["boxes"] = detection.boxes
            if not detection.found:
                result["capture_path"] = self.vision.save_capture(
                    frame, label=f"click_miss_{element}", boxes=detection.boxes
                )
                if self.automation.dry_run:
                    h, w = frame.shape[:2]
                    result["automation"] = self.automation.click(w // 2, h // 2)
                    result["note"] = "Element not found; dry-run used screen center"
                    return result
                raise RuntimeError(f"Could not find on-screen element: {element}")
        # Diagnostic capture of matched bounds (verification)
        result["capture_path"] = self.vision.save_capture(
            frame if frame is not None else self.vision.last_frame,
            label=f"click_hit_{element}",
            boxes=detection.boxes or [
                {
                    "x": detection.x - detection.width // 2,
                    "y": detection.y - detection.height // 2,
                    "w": detection.width or 8,
                    "h": detection.height or 8,
                    "label": detection.label or element,
                }
            ],
        )
        result["automation"] = self.automation.click(detection.x, detection.y)
        return result

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
            field = entities.get("field")
            if field:
                # Focus named field first (form-friendly)
                click_res = self._click_element(str(field), {"element": field})
                result["focus"] = click_res
                if click_res.get("capture_path"):
                    result["capture_path"] = click_res["capture_path"]
            result["automation"] = self.automation.type_text(entities.get("text", ""))
            return result

        if intent == "fill_form":
            field = str(entities.get("field") or "").strip()
            text = str(entities.get("text") or "")
            emit = getattr(self, "_status_cb", None) or (lambda _m: None)
            if field:
                emit(f"Filling form field “{field}”…")
                click_res = self._click_element(field, {"element": field})
                result["focus"] = click_res
                if click_res.get("capture_path"):
                    result["capture_path"] = click_res["capture_path"]
                result["boxes"] = click_res.get("boxes")
            else:
                emit("Typing into focused form field…")
            result["automation"] = self.automation.type_text(text)
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
            result["automation"] = self.automation.search_google(query)
            return result

        if intent in ("click_text", "click_button"):
            element = entities.get("element", "")
            clicked = self._click_element(str(element), entities)
            clicked["intent"] = intent
            return clicked

        if intent == "run_workflow":
            name = entities.get("workflow", "")
            if user_id is None:
                raise RuntimeError("Login required to run workflows")
            nested = self.run_workflow_by_name(user_id, name)
            result["nested"] = nested
            if not nested.get("ok"):
                raise RuntimeError(nested.get("error") or "Workflow failed")
            return result

        raise RuntimeError(
            f"Unsupported intent: {intent}. Try open / click / fill / type / search."
        )

    def capture_preview(self) -> Dict[str, Any]:
        frame = self.vision.capture_screen()
        self.last_frame = frame
        path = self.vision.save_capture(frame, label="preview")
        return {"frame": frame, "path": path, "boxes": [], "ok": self.vision.last_capture_ok}
