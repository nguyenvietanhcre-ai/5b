-- Trusted main-family grade mirrored into a separate pilot learner identity.
-- Birth years remain genuine in accounts; no age-derived compatibility value.
CREATE TABLE local_pilot_family_grades (
 pilot_student_id INTEGER PRIMARY KEY REFERENCES students(id),
 main_family_id INTEGER NOT NULL,
 main_student_id INTEGER NOT NULL,
 declared_grade INTEGER NOT NULL CHECK(declared_grade BETWEEN 1 AND 5),
 grade_academic_year INTEGER NOT NULL,
 updated_at TEXT NOT NULL
);
