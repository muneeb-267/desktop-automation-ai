from pathlib import Path

from src.config import load_config
from src.db.database import Database, hash_password, reset_database_singleton
from src.db.repositories import (
    ExecutionLogRepository,
    NLPCommandRepository,
    ScreenCaptureRepository,
    TaskRepository,
    UserConfRepository,
    UserRepository,
    WorkflowRepository,
)


def test_schema_seed_and_crud(tmp_path: Path):
    reset_database_singleton()
    cfg = load_config()
    db = Database(tmp_path / "test.db")
    db.initialize_schema()
    db.seed_defaults(cfg)

    users = UserRepository(db)
    user = users.authenticate("demo", "demo123")
    assert user is not None
    assert user["password"] == hash_password("demo123")
    assert "email" in user

    conf = UserConfRepository(db).get_map(user["user_id"])
    assert conf.get("dry_run") in ("0", "1")

    wfs = WorkflowRepository(db).list_for_user(user["user_id"])
    assert any(w["name"] == "Open Notepad Demo" for w in wfs)
    tasks = TaskRepository(db).list_for_workflow(wfs[0]["workflow_id"])
    assert len(tasks) >= 1

    cmd_id = NLPCommandRepository(db).create(
        "open chrome",
        "open_app",
        {"app": "chrome"},
        0.9,
        user_id=user["user_id"],
    )
    log_id = ExecutionLogRepository(db).create(
        "Success", 12, details={"ok": True}, user_id=user["user_id"], command_id=cmd_id
    )
    ScreenCaptureRepository(db).create("/tmp/fake.png", log_id=log_id, width=100, height=50, element_found="Login")
    assert ExecutionLogRepository(db).recent(user_id=user["user_id"], limit=5)
    db.close()
    reset_database_singleton()
