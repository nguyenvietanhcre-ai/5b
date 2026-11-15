CREATE TABLE IF NOT EXISTS account_scratchpads (
 student_id INTEGER NOT NULL REFERENCES students(id),
 exam_id INTEGER NOT NULL REFERENCES exams(id),
 position INTEGER NOT NULL,
 revision INTEGER NOT NULL,
 note_json TEXT NOT NULL,
 request_key TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 PRIMARY KEY(student_id,exam_id,position),
 FOREIGN KEY(exam_id,position) REFERENCES exam_items(exam_id,position)
);
