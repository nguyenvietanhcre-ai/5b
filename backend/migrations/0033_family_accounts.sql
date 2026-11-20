-- Additive family identity. Existing learner accounts/records are not rewritten.
CREATE TABLE family_accounts (
 id INTEGER PRIMARY KEY,
 email TEXT NOT NULL COLLATE NOCASE UNIQUE,
 password_hash TEXT NOT NULL,
 pin_hash TEXT,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')),
 auth_revision INTEGER NOT NULL DEFAULT 1,
 registration_key TEXT NOT NULL UNIQUE,
 registration_digest TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE family_parent_profiles (
 family_id INTEGER PRIMARY KEY REFERENCES family_accounts(id),
 display_name TEXT NOT NULL,
 verification_status TEXT NOT NULL DEFAULT 'self_declared' CHECK(verification_status='self_declared'),
 created_at TEXT NOT NULL
);
CREATE TABLE family_children (
 student_id INTEGER PRIMARY KEY REFERENCES students(id),
 family_id INTEGER NOT NULL REFERENCES family_accounts(id),
 declared_grade INTEGER NOT NULL CHECK(declared_grade BETWEEN 1 AND 5),
 grade_academic_year INTEGER NOT NULL,
 actual_birth_year INTEGER NOT NULL CHECK(actual_birth_year BETWEEN 1900 AND 2100),
 pin_hash TEXT,
 request_key TEXT NOT NULL,
 request_digest TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(family_id,request_key)
);
CREATE INDEX family_children_owner ON family_children(family_id,student_id);
CREATE TABLE family_child_consents (
 id INTEGER PRIMARY KEY,
 family_id INTEGER NOT NULL REFERENCES family_accounts(id),
 student_id INTEGER NOT NULL REFERENCES family_children(student_id),
 purpose TEXT NOT NULL,
 version TEXT NOT NULL,
 representative_role TEXT NOT NULL CHECK(representative_role IN ('parent','guardian')),
 accepted_at TEXT NOT NULL,
 withdrawn_at TEXT,
 verification_status TEXT NOT NULL DEFAULT 'self_declared' CHECK(verification_status='self_declared'),
 UNIQUE(student_id,purpose,version)
);
CREATE TABLE family_devices (
 id TEXT PRIMARY KEY,
 family_id INTEGER NOT NULL REFERENCES family_accounts(id),
 token_hash TEXT NOT NULL UNIQUE,
 csrf_token TEXT NOT NULL,
 context TEXT NOT NULL,
 scope TEXT NOT NULL CHECK(scope IN ('profiles','child','parent_read','parent_full')),
 selected_student_id INTEGER REFERENCES students(id),
 allowed_student_id INTEGER REFERENCES students(id),
 device_name TEXT NOT NULL,
 remembered INTEGER NOT NULL DEFAULT 0 CHECK(remembered IN (0,1)),
 auth_revision INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 last_seen_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 parent_opened_at TEXT,
 parent_seen_at TEXT,
 full_authenticated_at TEXT,
 pin_failures INTEGER NOT NULL DEFAULT 0,
 pin_locked_until TEXT,
 revoked_at TEXT
);
CREATE INDEX family_devices_owner ON family_devices(family_id,revoked_at,expires_at);
-- Separate revision table avoids altering historical exam schemas.
CREATE TABLE family_exam_revisions (
 attempt_id INTEGER PRIMARY KEY REFERENCES exam_attempts(id),
 revision INTEGER NOT NULL DEFAULT 0
);
