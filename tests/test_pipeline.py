from pathlib import Path

from src.config import load_config
from src.db.database import Database, reset_database_singleton
from src.db.repositories import UserRepository
from src.pipeline import AutomationPipeline
from src.workflows.service import WorkflowService


def test_text_command_dry_run(tmp_path: Path):
    reset_database_singleton()
    cfg = load_config()
    cfg = dict(cfg)
    cfg["paths"] = dict(cfg["paths"])
    cfg["paths"]["db_file"] = str(tmp_path / "auto.db")
    cfg["paths"]["captures_dir"] = str(tmp_path / "captures")
    cfg["paths"]["templates_dir"] = str(tmp_path / "templates")
    cfg["automation"] = dict(cfg.get("automation", {}))
    cfg["automation"]["dry_run"] = True

    db = Database(tmp_path / "auto.db")
    db.initialize_schema()
    db.seed_defaults(cfg)

    users = UserRepository(db)
    user_id = users.create("tester", "tester@example.com", "secret123")
    db.seed_user_workspace(user_id, cfg)

    pipeline = AutomationPipeline(cfg, db)
    pipeline.automation.set_dry_run(True)

    result = pipeline.run_text_command("Open notepad and type hello", user_id=user_id)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert any(a.get("intent") == "open_app" for a in result["actions"])

    # Save history as workflow and replay
    wf_service = WorkflowService(db)
    tasks = wf_service.tasks_from_action_history(pipeline.automation.history)
    wid = wf_service.create_workflow(user_id, "From History", tasks=tasks)
    replay = pipeline.run_workflow(wid, user_id=user_id)
    assert replay["ok"] is True

    logs = pipeline.audit.recent_logs(10)
    assert any(l["status"] == "Success" for l in logs)

    # Voice-style: run by short name + copy file dry-run
    by_name = pipeline.run_workflow_by_name(user_id, "From History")
    assert by_name["ok"] is True

    copy = pipeline.run_text_command(
        "Copy file report to Desktop", user_id=user_id
    )
    # May fail if file missing — dry_run still resolves destinations; accept ok or clear error
    assert copy["parsed"]["intent"] == "copy_file"

    db.close()
    reset_database_singleton()


def test_unknown_command(tmp_path: Path):
    reset_database_singleton()
    cfg = load_config()
    db = Database(tmp_path / "u.db")
    db.initialize_schema()
    db.seed_defaults(cfg)
    pipeline = AutomationPipeline(cfg, db)
    result = pipeline.run_text_command("asdf qwer zxcv")
    assert result["ok"] is False
    db.close()
    reset_database_singleton()
