from pathlib import Path

from src.config import load_config
from src.db.database import Database, reset_database_singleton
from src.db.repositories import UserRepository
from src.workflows.service import WorkflowService


def test_workflow_create_edit_delete_and_ownership(tmp_path: Path):
    reset_database_singleton()
    cfg = load_config()
    db = Database(tmp_path / "wf.db")
    db.initialize_schema()
    users = UserRepository(db)
    a = users.create("alice", "a@example.com", "secret123")
    b = users.create("bob", "b@example.com", "secret123")
    svc = WorkflowService(db)
    wid = svc.create_workflow(
        a,
        "Research Setup",
        tasks=[
            {"intent": "open_app", "target_app": "chrome", "params": {}},
            {"intent": "wait", "input_value": "1", "params": {"seconds": 1}},
        ],
    )
    wf = svc.get_workflow(wid)
    assert wf["name"] == "Research Setup"
    assert len(wf["tasks"]) == 2
    svc.rename_workflow(wid, "Daily Research")
    svc.save_tasks(
        wid,
        [
            {"intent": "open_app", "target_app": "chrome", "params": {}},
            {"intent": "search_web", "input_value": "AI", "params": {"query": "AI"}},
            {"intent": "wait", "input_value": "1", "params": {"seconds": 1}},
        ],
    )
    wf = svc.get_workflow(wid)
    assert wf["name"] == "Daily Research"
    assert len(wf["tasks"]) == 3
    assert svc.find_by_name(a, "Daily Research")
    assert svc.find_by_name(b, "Daily Research") is None
    listed = svc.list_workflows(a)
    assert any(w["workflow_id"] == wid for w in listed)
    assert not any(w["workflow_id"] == wid for w in svc.list_workflows(b))
    svc.delete_workflow(wid)
    assert all(w["workflow_id"] != wid for w in svc.list_workflows(a))
    db.close()
    reset_database_singleton()


def test_tasks_from_history():
    history = [
        {"action": "open_app", "app": "notepad"},
        {"action": "type_text", "text": "hello"},
    ]
    tasks = WorkflowService.tasks_from_action_history(None, history)  # type: ignore[arg-type]
    assert len(tasks) == 2
    assert tasks[0]["intent"] == "open_app"


def test_task_to_step_roundtrip():
    step = WorkflowService.task_to_step(
        {
            "intent": "click_text",
            "target_element": "Login",
            "params": {},
        }
    )
    assert step["intent"] == "click_text"
    assert step["entities"]["element"] == "Login"
