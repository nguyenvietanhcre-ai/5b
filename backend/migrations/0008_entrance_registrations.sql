CREATE TABLE entrance_registrations (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    request_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    parent_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    student_name TEXT NOT NULL,
    grade INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 5),
    details_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','contacted','scheduled','completed','closed')),
    admin_note TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX entrance_registrations_created ON entrance_registrations(created_at DESC, id DESC);
