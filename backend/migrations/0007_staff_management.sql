CREATE TABLE staff_users (
    id INTEGER PRIMARY KEY,
    login TEXT NOT NULL COLLATE NOCASE UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','teacher')),
    teacher_id INTEGER UNIQUE REFERENCES teachers(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','disabled')),
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    CHECK((role='teacher' AND teacher_id IS NOT NULL) OR (role='admin' AND teacher_id IS NULL))
);
CREATE TABLE staff_sessions (
    token_hash TEXT PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX staff_sessions_owner ON staff_sessions(staff_id);
CREATE INDEX staff_sessions_expiry ON staff_sessions(expires_at);
CREATE TABLE staff_audit_log (
    id INTEGER PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX staff_audit_time ON staff_audit_log(id DESC);
CREATE TABLE system_settings (
    name TEXT PRIMARY KEY,
    value_json TEXT NOT NULL CHECK(json_valid(value_json)),
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    staff_id INTEGER REFERENCES staff_users(id)
);
INSERT INTO system_settings(name,value_json,updated_at) VALUES (
    'platform',
    '{"registration_open":true,"learning_open":true,"practice_open":true,"arena_open":true,"leaderboard_open":true,"free_limits":{"content":1,"combined":1,"human":3,"bot":5}}',
    strftime('%Y-%m-%dT%H:%M:%SZ','now')
);
ALTER TABLE online_classes ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE class_sessions ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE class_assignments ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE lessons ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE lessons ADD COLUMN publication_status TEXT NOT NULL DEFAULT 'published'
    CHECK(publication_status IN ('draft','published'));
ALTER TABLE topics ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
