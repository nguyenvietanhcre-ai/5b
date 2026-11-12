-- Keep attendance and numeric scores intact; remarks may exist before either is set.
CREATE TABLE class_session_comments (
    session_id INTEGER NOT NULL REFERENCES class_sessions(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    comment TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(session_id,student_id)
);
CREATE TABLE class_assignment_comments (
    assignment_id INTEGER NOT NULL REFERENCES class_assignments(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    comment TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(assignment_id,student_id)
);
CREATE TABLE class_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES class_assignments(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL CHECK(mime_type IN ('image/jpeg','image/png','image/webp','application/pdf')),
    size INTEGER NOT NULL CHECK(size>0 AND size<=10485760),
    content BLOB NOT NULL,
    digest TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);
CREATE INDEX class_submissions_latest ON class_submissions(assignment_id,student_id,id DESC);
CREATE TABLE class_notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES online_classes(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    section TEXT NOT NULL CHECK(section IN ('assignments','fees')),
    source_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(student_id,section,source_id)
);
CREATE INDEX class_notices_unread ON class_notices(student_id,class_id,section,id) WHERE read_at IS NULL;
