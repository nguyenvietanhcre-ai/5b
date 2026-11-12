ALTER TABLE online_classes ADD COLUMN session_fee INTEGER CHECK(session_fee IS NULL OR (session_fee BETWEEN 0 AND 1000000000));
ALTER TABLE class_fees ADD COLUMN source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual','calculated'));
ALTER TABLE class_fees ADD COLUMN session_fee INTEGER;
ALTER TABLE class_fees ADD COLUMN charged_count INTEGER;
ALTER TABLE class_fees ADD COLUMN free_count INTEGER;
ALTER TABLE class_fees ADD COLUMN absent_count INTEGER;
ALTER TABLE class_fees ADD COLUMN pending_count INTEGER;
ALTER TABLE class_fees ADD COLUMN sessions_json TEXT CHECK(sessions_json IS NULL OR json_valid(sessions_json));
ALTER TABLE class_fees ADD COLUMN calculation_id INTEGER REFERENCES class_tuition_calculations(id);
ALTER TABLE class_fees ADD COLUMN calculated_at TEXT;
CREATE TABLE class_tuition_calculations (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES online_classes(id),
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    request_key TEXT NOT NULL,
    month TEXT NOT NULL,
    preview_token TEXT NOT NULL,
    result_json TEXT NOT NULL CHECK(json_valid(result_json)),
    created_at TEXT NOT NULL,
    UNIQUE(staff_id,request_key)
);
CREATE TABLE class_tuition_calculation_items (
    calculation_id INTEGER NOT NULL REFERENCES class_tuition_calculations(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    fee_id INTEGER REFERENCES class_fees(id),
    action TEXT NOT NULL,
    snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
    PRIMARY KEY(calculation_id,student_id)
);
CREATE INDEX class_tuition_calculations_class ON class_tuition_calculations(class_id,month,id DESC);
