-- Reading completion is independent of a fixed self-check and never grants answers.
CREATE TABLE study_knowledge_completions (
 student_id INTEGER NOT NULL REFERENCES students(id), lesson_key TEXT NOT NULL,
 lesson_revision INTEGER NOT NULL CHECK(lesson_revision > 0), completed_at TEXT NOT NULL,
 PRIMARY KEY(student_id,lesson_key,lesson_revision)
);
