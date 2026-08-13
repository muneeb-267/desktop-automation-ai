PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS User_Conf (
    conf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    theme TEXT NOT NULL DEFAULT 'light',
    mic_sensitivity REAL NOT NULL DEFAULT 0.7,
    dry_run INTEGER NOT NULL DEFAULT 1,
    failsafe INTEGER NOT NULL DEFAULT 1,
    pause_seconds REAL NOT NULL DEFAULT 0.35,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Workflow (
    workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS AutomationRule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    condition_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 100,
    enabled INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (workflow_id) REFERENCES Workflow(workflow_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Task (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    intent TEXT NOT NULL,
    target_app TEXT DEFAULT '',
    target_element TEXT DEFAULT '',
    input_value TEXT DEFAULT '',
    params_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (workflow_id) REFERENCES Workflow(workflow_id) ON DELETE CASCADE,
    UNIQUE(workflow_id, step_order)
);

CREATE TABLE IF NOT EXISTS NLP_Command (
    command_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    raw_text TEXT NOT NULL,
    intent TEXT,
    entities_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'text',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Execution_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    workflow_id INTEGER,
    command_id INTEGER,
    status TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    error_message TEXT DEFAULT '',
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE SET NULL,
    FOREIGN KEY (workflow_id) REFERENCES Workflow(workflow_id) ON DELETE SET NULL,
    FOREIGN KEY (command_id) REFERENCES NLP_Command(command_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Screen_capture (
    capture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER,
    file_path TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (log_id) REFERENCES Execution_log(log_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_task_workflow ON Task(workflow_id, step_order);
CREATE INDEX IF NOT EXISTS idx_exec_created ON Execution_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_nlp_created ON NLP_Command(created_at DESC);
