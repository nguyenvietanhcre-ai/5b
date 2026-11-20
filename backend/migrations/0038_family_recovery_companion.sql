CREATE TABLE family_password_resets (
 token_hash TEXT PRIMARY KEY, family_id INTEGER NOT NULL REFERENCES family_accounts(id),
 created_at TEXT NOT NULL, expires_at TEXT NOT NULL, redeemed_at TEXT
);
CREATE INDEX family_reset_owner ON family_password_resets(family_id,created_at);
CREATE TABLE companion_reselections (
 student_id INTEGER PRIMARY KEY REFERENCES students(id),
 changed_at TEXT NOT NULL, previous_mascot_id INTEGER NOT NULL, mascot_id INTEGER NOT NULL
);
CREATE TABLE family_closures (
 family_id INTEGER PRIMARY KEY REFERENCES family_accounts(id), closed_at TEXT NOT NULL,
 retention_notice TEXT NOT NULL
);
