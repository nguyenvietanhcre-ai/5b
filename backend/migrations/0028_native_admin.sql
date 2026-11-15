CREATE TABLE staff_knowledge_drafts (
    lesson_key TEXT PRIMARY KEY,
    base_revision INTEGER NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1))
);
CREATE TABLE staff_native_events (
    id INTEGER PRIMARY KEY,
    staff_id INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    lesson_key TEXT NOT NULL,
    action TEXT NOT NULL,
    lesson_revision INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
