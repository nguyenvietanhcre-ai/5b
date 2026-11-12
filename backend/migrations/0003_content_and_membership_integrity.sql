CREATE TRIGGER question_versions_preserve_used_content
BEFORE UPDATE OF question_id, revision, difficulty, curriculum_week, prompt_json,
    grading_rule_json, solution_steps_json, hints_json ON question_versions
WHEN EXISTS (SELECT 1 FROM exam_items WHERE question_version_id = OLD.id)
  OR EXISTS (SELECT 1 FROM duel_rounds WHERE question_version_id = OLD.id)
BEGIN
    SELECT RAISE(ABORT, 'Create a new question version for revised content');
END;

CREATE TRIGGER exam_items_preserve_started_exam_update
BEFORE UPDATE ON exam_items
WHEN EXISTS (SELECT 1 FROM exam_attempts WHERE exam_id = OLD.exam_id)
BEGIN
    SELECT RAISE(ABORT, 'Started exam content is immutable');
END;

CREATE TRIGGER exam_items_preserve_started_exam_insert
BEFORE INSERT ON exam_items
WHEN EXISTS (SELECT 1 FROM exam_attempts WHERE exam_id = NEW.exam_id)
BEGIN
    SELECT RAISE(ABORT, 'Started exam content is immutable');
END;

CREATE TRIGGER exam_items_preserve_started_exam_delete
BEFORE DELETE ON exam_items
WHEN EXISTS (SELECT 1 FROM exam_attempts WHERE exam_id = OLD.exam_id)
BEGIN
    SELECT RAISE(ABORT, 'Started exam content is immutable');
END;

CREATE TRIGGER exam_attempts_owner
BEFORE INSERT ON exam_attempts
WHEN EXISTS (
    SELECT 1 FROM exams WHERE id = NEW.exam_id
    AND owner_student_id IS NOT NULL AND owner_student_id <> NEW.student_id
)
BEGIN
    SELECT RAISE(ABORT, 'Exam belongs to a different student');
END;

CREATE TRIGGER entitlement_enrollment_account
BEFORE INSERT ON access_entitlements
WHEN NEW.enrollment_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM class_enrollments e JOIN students s ON s.id = e.student_id
    WHERE e.id = NEW.enrollment_id AND s.account_id = NEW.account_id
)
BEGIN
    SELECT RAISE(ABORT, 'Enrollment belongs to a different account');
END;
