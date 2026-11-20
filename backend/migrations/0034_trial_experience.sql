CREATE TABLE trial_browsers (
 id TEXT PRIMARY KEY, secret_hash TEXT NOT NULL UNIQUE, csrf TEXT NOT NULL,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, current_session TEXT,
 generation INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE trial_sessions (
 id TEXT PRIMARY KEY, browser_id TEXT NOT NULL REFERENCES trial_browsers(id),
 generation INTEGER NOT NULL, created_at INTEGER NOT NULL, last_activity_at INTEGER NOT NULL,
 absolute_expires_at INTEGER NOT NULL, revoked_at INTEGER, state_json TEXT NOT NULL
);
CREATE INDEX trial_session_browser ON trial_sessions(browser_id);
CREATE INDEX trial_session_created ON trial_sessions(created_at);
CREATE TABLE trial_counters (
 browser_id TEXT PRIMARY KEY REFERENCES trial_browsers(id), expires_at INTEGER NOT NULL,
 creates_json TEXT NOT NULL DEFAULT '[]', requests_json TEXT NOT NULL DEFAULT '[]',
 issued_count INTEGER NOT NULL DEFAULT 0, cooldown_until INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE trial_attempts (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES trial_sessions(id) ON DELETE CASCADE,
 mode TEXT NOT NULL, created_at INTEGER NOT NULL, payload_json TEXT NOT NULL
);
CREATE INDEX trial_attempt_session ON trial_attempts(session_id);
CREATE TABLE trial_keep_packages (
 id TEXT PRIMARY KEY, browser_id TEXT NOT NULL REFERENCES trial_browsers(id),
 session_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE, csrf TEXT NOT NULL,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
 cancelled_at INTEGER, claimed_at INTEGER, claimed_student_id INTEGER, claimed_family_id TEXT
);
CREATE INDEX trial_keep_browser ON trial_keep_packages(browser_id);
CREATE TABLE trial_claimed_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, package_id TEXT NOT NULL UNIQUE,
 student_id INTEGER NOT NULL REFERENCES students(id), family_id TEXT NOT NULL,
 claimed_at INTEGER NOT NULL, consent_basis TEXT NOT NULL, snapshot_json TEXT NOT NULL
);
CREATE INDEX trial_history_student ON trial_claimed_history(student_id);
CREATE TABLE trial_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at INTEGER NOT NULL, event TEXT NOT NULL
);
CREATE INDEX trial_events_time ON trial_events(occurred_at);
