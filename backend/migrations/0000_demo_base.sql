CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    student_code TEXT NOT NULL UNIQUE CHECK (length(trim(student_code)) > 0),
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    grade_level INTEGER NOT NULL CHECK (grade_level BETWEEN 1 AND 12),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY,
    exam_code TEXT NOT NULL CHECK (length(trim(exam_code)) > 0),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    grade_level INTEGER NOT NULL CHECK (grade_level BETWEEN 1 AND 12),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'hidden')),
    UNIQUE (exam_code, version)
);
