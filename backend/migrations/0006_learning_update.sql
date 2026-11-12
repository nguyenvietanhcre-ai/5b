CREATE TABLE daily_usage (
    student_id INTEGER NOT NULL REFERENCES students(id),
    day TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('content','combined','human','bot')),
    request_key TEXT NOT NULL,
    PRIMARY KEY(student_id,category,request_key)
);
CREATE INDEX daily_usage_limits ON daily_usage(student_id,day,category);
ALTER TABLE online_classes ADD COLUMN schedule TEXT NOT NULL DEFAULT '';
ALTER TABLE online_classes ADD COLUMN curriculum TEXT NOT NULL DEFAULT '';
CREATE TABLE class_sessions (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES online_classes(id),
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    teacher_comment TEXT NOT NULL DEFAULT '',
    video_url TEXT NOT NULL DEFAULT ''
);
CREATE INDEX class_sessions_dates ON class_sessions(class_id,starts_at);
CREATE TABLE class_assignments (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES class_sessions(id),
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'Bài tập về nhà',
    document_url TEXT NOT NULL DEFAULT ''
);
CREATE TABLE class_scores (
    assignment_id INTEGER NOT NULL REFERENCES class_assignments(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    score REAL NOT NULL CHECK(score BETWEEN 0 AND 10),
    PRIMARY KEY(assignment_id,student_id)
);
CREATE TABLE class_attendance (
    session_id INTEGER NOT NULL REFERENCES class_sessions(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    status TEXT NOT NULL CHECK(status IN ('charged','free','absent')),
    PRIMARY KEY(session_id,student_id)
);
CREATE TABLE class_fees (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES online_classes(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    month TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount>=0),
    paid_at TEXT,
    UNIQUE(class_id,student_id,month)
);
CREATE TABLE payment_orders (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    fee_id INTEGER REFERENCES class_fees(id),
    reference TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL CHECK(amount>0),
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid','cancelled'))
);
CREATE UNIQUE INDEX payment_order_pending ON payment_orders(account_id,coalesce(fee_id,0)) WHERE status='pending';
