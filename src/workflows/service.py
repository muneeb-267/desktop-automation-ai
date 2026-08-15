"""Save, list, edit, and prepare multi-step workflows."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.db.database import Database
from src.db.repositories import (
    AutomationRuleRepository,
    TaskRepository,
    WorkflowRepository,
)


class WorkflowService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.workflows = WorkflowRepository(db)
        self.tasks = TaskRepository(db)
        self.rules = AutomationRuleRepository(db)

    def list_workflows(self, user_id: int) -> List[Dict[str, Any]]:
        items = self.workflows.list_for_user(user_id)
        for item in items:
            item["tasks"] = self.tasks.list_for_workflow(item["workflow_id"])
            item["rules"] = self.rules.list_for_workflow(item["workflow_id"])
        return items

    def get_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return None
        wf["tasks"] = self.tasks.list_for_workflow(workflow_id)
        wf["rules"] = self.rules.list_for_workflow(workflow_id)
        return wf

    def create_workflow(
        self,
        user_id: int,
        name: str,
        description: str = "",
        tasks: Optional[List[Dict[str, Any]]] = None,
        trigger_type: str = "manual",
    ) -> int:
        wid = self.workflows.create(user_id, name, description, trigger_type=trigger_type)
        self.rules.add(wid, "Always run", condition='{"when":"manual"}', action="run_workflow", priority=10)
        if tasks:
            self.tasks.replace_tasks(wid, tasks)
        return wid

    def rename_workflow(self, workflow_id: int, name: str) -> None:
        self.workflows.rename(workflow_id, name)

    def delete_workflow(self, workflow_id: int) -> None:
        self.workflows.delete(workflow_id)

    def save_tasks(self, workflow_id: int, tasks: List[Dict[str, Any]]) -> None:
        self.tasks.replace_tasks(workflow_id, tasks)

    def find_by_name(self, user_id: int, name: str) -> Optional[Dict[str, Any]]:
        for wf in self.list_workflows(user_id):
            if wf["name"].lower() == name.lower():
                return wf
        return None

    def tasks_from_action_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped: List[Dict[str, Any]] = []
        for item in history:
            action = item.get("action")
            if action == "open_app":
                mapped.append(
                    {
                        "intent": "open_app",
                        "target_app": item.get("app", ""),
                        "target_element": "",
                        "input_value": "",
                        "params": {},
                    }
                )
            elif action == "type_text":
                mapped.append(
                    {
                        "intent": "type_text",
                        "target_app": "",
                        "target_element": "",
                        "input_value": item.get("text", ""),
                        "params": {},
                    }
                )
            elif action == "click":
                mapped.append(
                    {
                        "intent": "click_text",
                        "target_app": "",
                        "target_element": "",
                        "input_value": "",
                        "params": {"x": item.get("x"), "y": item.get("y")},
                    }
                )
            elif action == "press":
                mapped.append(
                    {
                        "intent": "press_key",
                        "target_app": "",
                        "target_element": "",
                        "input_value": item.get("key", ""),
                        "params": {},
                    }
                )
            elif action in ("scroll", "hscroll"):
                mapped.append(
                    {
                        "intent": "scroll",
                        "target_app": "",
                        "target_element": "",
                        "input_value": "",
                        "params": {
                            "direction": item.get("direction", "down"),
                            "amount": item.get("amount", 3),
                        },
                    }
                )
            elif action == "wait":
                mapped.append(
                    {
                        "intent": "wait",
                        "target_app": "",
                        "target_element": "",
                        "input_value": str(item.get("seconds", 1)),
                        "params": {"seconds": item.get("seconds", 1)},
                    }
                )
            elif action == "search_google":
                mapped.append(
                    {
                        "intent": "search_web",
                        "target_app": "chrome",
                        "target_element": "",
                        "input_value": item.get("query", ""),
                        "params": {"query": item.get("query", ""), "url": item.get("url", "")},
                    }
                )
            elif action == "open_url":
                mapped.append(
                    {
                        "intent": "open_app",
                        "target_app": "chrome",
                        "target_element": "",
                        "input_value": item.get("url", ""),
                        "params": {"url": item.get("url", "")},
                    }
                )
            elif action == "address_bar_search":
                mapped.append(
                    {
                        "intent": "search_web",
                        "target_app": "",
                        "target_element": "",
                        "input_value": item.get("query", ""),
                        "params": {"query": item.get("query", "")},
                    }
                )
        return mapped

    @staticmethod
    def task_to_step(task: Dict[str, Any]) -> Dict[str, Any]:
        params = task.get("params_json") or "{}"
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                params = {}
        intent = task.get("intent", "wait")
        entities: Dict[str, Any] = dict(params) if isinstance(params, dict) else {}
        if intent == "open_app":
            entities["app"] = task.get("target_app", "") or entities.get("app", "")
            if entities.get("url") and not entities.get("app"):
                entities["app"] = "chrome"
        elif intent in ("click_text", "click_button"):
            entities["element"] = task.get("target_element", "") or entities.get("element", "")
        elif intent == "fill_form":
            entities["field"] = task.get("target_element", "") or entities.get("field", "")
            entities["text"] = task.get("input_value", "") or entities.get("text", "")
        elif intent == "type_text":
            entities["text"] = task.get("input_value", "") or entities.get("text", "")
            if task.get("target_element"):
                entities["field"] = task.get("target_element")
        elif intent == "press_key":
            entities["key"] = task.get("input_value", "") or entities.get("key", "enter")
        elif intent == "wait":
            entities["seconds"] = float(entities.get("seconds") or task.get("input_value") or 1)
        elif intent == "search_web":
            entities["query"] = task.get("input_value", "") or entities.get("query", "")
        elif intent == "scroll":
            entities.setdefault("direction", "down")
            entities.setdefault("amount", 3)
        return {"intent": intent, "entities": entities, "confidence": 1.0}
