ALTER TABLE accounts ADD COLUMN password_hash TEXT;
CREATE TABLE auth_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    csrf_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX auth_sessions_expiry ON auth_sessions(expires_at);
CREATE INDEX auth_sessions_account ON auth_sessions(account_id);
ALTER TABLE topics ADD COLUMN client_key TEXT;
CREATE UNIQUE INDEX topics_client_key ON topics(grade_id, client_key);
ALTER TABLE lessons ADD COLUMN client_key TEXT;
ALTER TABLE lessons ADD COLUMN presentation_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(presentation_json));
CREATE UNIQUE INDEX lessons_client_key ON lessons(client_key);
ALTER TABLE question_versions ADD COLUMN options_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(options_json));
ALTER TABLE exam_items ADD COLUMN options_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(options_json));
ALTER TABLE exam_attempts ADD COLUMN request_key TEXT;
ALTER TABLE exam_attempts ADD COLUMN cursor INTEGER NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX exam_attempts_request ON exam_attempts(student_id, request_key);
CREATE TABLE exam_draft_answers (
    attempt_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    answer TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (attempt_id, position),
    FOREIGN KEY (attempt_id, exam_id) REFERENCES exam_attempts(id, exam_id),
    FOREIGN KEY (exam_id, position) REFERENCES exam_items(exam_id, position)
);
CREATE TABLE learning_preferences (
    student_id INTEGER PRIMARY KEY REFERENCES students(id),
    last_lesson TEXT NOT NULL DEFAULT ''
);
CREATE TABLE arena_members (
    room_id TEXT NOT NULL,
    token_hash TEXT PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    duel_id INTEGER NOT NULL REFERENCES duels(id),
    UNIQUE(room_id, student_id)
);
