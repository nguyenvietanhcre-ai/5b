CREATE TABLE bunny_stream_uploads (
    id TEXT PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    request_key TEXT NOT NULL,
    provider TEXT NOT NULL CHECK(provider IN ('main','native')),
    lesson_key TEXT NOT NULL,
    library_id INTEGER NOT NULL CHECK(library_id > 0),
    video_guid TEXT,
    state TEXT NOT NULL CHECK(state IN ('creating','uploading','processing','ready','failed')),
    declared_size INTEGER NOT NULL CHECK(declared_size > 0),
    duration_seconds INTEGER NOT NULL DEFAULT 0 CHECK(duration_seconds >= 0),
    storage_bytes INTEGER NOT NULL DEFAULT 0 CHECK(storage_bytes >= 0),
    updated_at TEXT NOT NULL,
    UNIQUE(staff_id,request_key),
    UNIQUE(library_id,video_guid),
    UNIQUE(id,provider,lesson_key),
    CHECK((state='creating')=(video_guid IS NULL)),
    CHECK(state<>'ready' OR (duration_seconds > 0 AND storage_bytes > 0))
);

CREATE TABLE bunny_stream_progress (
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    lesson_key TEXT NOT NULL,
    lesson_revision INTEGER NOT NULL CHECK(lesson_revision > 0),
    upload_id TEXT NOT NULL,
    position_seconds REAL NOT NULL CHECK(position_seconds >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY(student_id,provider,lesson_key,lesson_revision,upload_id),
    FOREIGN KEY(upload_id,provider,lesson_key) REFERENCES bunny_stream_uploads(id,provider,lesson_key)
);
