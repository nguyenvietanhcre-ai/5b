CREATE TABLE study_retakes (
 exam_id INTEGER PRIMARY KEY REFERENCES exams(id), root_exam_id INTEGER NOT NULL REFERENCES exams(id),
 parent_exam_id INTEGER NOT NULL REFERENCES exams(id), student_id INTEGER NOT NULL REFERENCES students(id),
 created_at TEXT NOT NULL
);
CREATE INDEX study_retakes_owner ON study_retakes(student_id,root_exam_id,exam_id);
CREATE TABLE study_retake_requests (
 student_id INTEGER NOT NULL REFERENCES students(id), request_key TEXT NOT NULL,
 requested_exam_id INTEGER NOT NULL REFERENCES exams(id), exam_id INTEGER NOT NULL REFERENCES exams(id),
 PRIMARY KEY(student_id,request_key)
);
CREATE TABLE study_lesson_opens (
 student_id INTEGER NOT NULL REFERENCES students(id), lesson_key TEXT NOT NULL,
 lesson_revision INTEGER NOT NULL, opened_at TEXT NOT NULL,
 PRIMARY KEY(student_id,lesson_key,lesson_revision)
);
