CREATE TABLE purchased_credit_grants (
    id INTEGER PRIMARY KEY,
    source_line_id INTEGER NOT NULL UNIQUE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    sku TEXT NOT NULL CHECK(sku IN ('questions-100','exams-10')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    granted_at TEXT NOT NULL
);
CREATE INDEX purchased_credit_grants_owner ON purchased_credit_grants(student_id,sku);

-- The native store records its usage with the attempt it created. This binding
-- prevents creating new spends when an already-used native store is detached.
CREATE TABLE purchased_credit_native_store (
    id INTEGER PRIMARY KEY CHECK(id=1),
    store_key TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(24))))
);
INSERT INTO purchased_credit_native_store(id) VALUES (1);
CREATE TABLE purchased_credit_native_bindings (
    student_id INTEGER PRIMARY KEY REFERENCES students(id),
    store_key TEXT NOT NULL
);

CREATE TABLE purchased_credit_quotes (
    quote_id TEXT PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    sku TEXT NOT NULL CHECK(sku IN ('questions-100','exams-10')),
    criteria_hash TEXT NOT NULL,
    quote_json TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE purchased_credit_usage (
    exam_id INTEGER PRIMARY KEY REFERENCES exams(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    bank_key TEXT NOT NULL,
    bank_student_id INTEGER NOT NULL,
    sku TEXT NOT NULL CHECK(sku IN ('questions-100','exams-10')),
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 0 AND 10),
    quote_id TEXT NOT NULL UNIQUE REFERENCES purchased_credit_quotes(quote_id),
    request_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    spent_at TEXT NOT NULL,
    intent_id TEXT,
    UNIQUE(student_id,request_key),
    UNIQUE(student_id,intent_id),
    CHECK(sku <> 'exams-10' OR quantity = 1)
);
CREATE INDEX purchased_credit_usage_owner ON purchased_credit_usage(bank_key,bank_student_id,sku);

CREATE TABLE purchased_credit_question_usage (
    bank_key TEXT NOT NULL,
    student_id INTEGER NOT NULL REFERENCES students(id),
    content_key TEXT NOT NULL,
    exam_id INTEGER NOT NULL REFERENCES purchased_credit_usage(exam_id),
    PRIMARY KEY(bank_key,student_id,content_key)
);

CREATE TRIGGER purchased_credit_grants_immutable BEFORE UPDATE ON purchased_credit_grants
BEGIN SELECT RAISE(ABORT,'Purchased credit grants are immutable'); END;
CREATE TRIGGER purchased_credit_grants_no_delete BEFORE DELETE ON purchased_credit_grants
BEGIN SELECT RAISE(ABORT,'Purchased credit grants are durable'); END;
CREATE TRIGGER purchased_credit_usage_immutable BEFORE UPDATE ON purchased_credit_usage
BEGIN SELECT RAISE(ABORT,'Purchased credit usage is immutable'); END;
CREATE TRIGGER purchased_credit_usage_no_delete BEFORE DELETE ON purchased_credit_usage
BEGIN SELECT RAISE(ABORT,'Purchased credit usage is durable'); END;
