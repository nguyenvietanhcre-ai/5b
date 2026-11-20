-- Classification does not grant accounts, reset usage or rewrite issued exams.
CREATE TABLE question_access_policy (
    id INTEGER PRIMARY KEY CHECK(id=1),
    mode TEXT NOT NULL DEFAULT 'legacy' CHECK(mode IN ('legacy','classified')),
    baseline TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO question_access_policy(id,baseline) VALUES(1,'0035-pre-classification-v1');

-- Frozen compatibility inventory, deliberately separate from an approved tier.
CREATE TABLE question_access_legacy (
    version_id INTEGER PRIMARY KEY REFERENCES question_versions(id),
    baseline TEXT NOT NULL,
    pin_json TEXT NOT NULL CHECK(json_valid(pin_json))
);
INSERT INTO question_access_legacy
SELECT v.id,'0035-pre-classification-v1',json_object(
    'question_id',v.question_id,'revision',v.revision,'grade_id',q.grade_id,
    'topic_id',q.topic_id,'difficulty',v.difficulty,'curriculum_week',v.curriculum_week,
    'prompt_json',v.prompt_json,'grading_rule_json',v.grading_rule_json,
    'solution_steps_json',v.solution_steps_json,'hints_json',v.hints_json,'options_json',v.options_json)
FROM question_versions v JOIN questions q ON q.id=v.question_id
WHERE v.status='published';

CREATE TABLE question_access_labels (
    version_id INTEGER PRIMARY KEY REFERENCES question_versions(id),
    tier TEXT NOT NULL CHECK(tier IN ('trial','free','vip','vip_plus')),
    purposes_json TEXT NOT NULL CHECK(json_valid(purposes_json) AND json_type(purposes_json)='array'),
    review_status TEXT NOT NULL CHECK(review_status IN ('draft','approved','rejected')),
    source_note TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
    staff_id INTEGER REFERENCES staff_users(id),
    updated_at TEXT NOT NULL
);
CREATE INDEX question_access_pool ON question_access_labels(tier,review_status,version_id);

-- Existing order payloads are the sole scope of this independent right.
CREATE TABLE question_access_order_pins (
    order_id INTEGER NOT NULL REFERENCES payment_orders(id),
    version_id INTEGER NOT NULL REFERENCES question_versions(id),
    pin_json TEXT NOT NULL CHECK(json_valid(pin_json)),
    PRIMARY KEY(order_id,version_id)
);
INSERT INTO question_access_order_pins
SELECT o.id,v.id,json_object(
    'question_id',v.question_id,'revision',v.revision,'grade_id',q.grade_id,
    'topic_id',q.topic_id,'difficulty',v.difficulty,'curriculum_week',v.curriculum_week,
    'prompt_json',v.prompt_json,'grading_rule_json',v.grading_rule_json,
    'solution_steps_json',v.solution_steps_json,'hints_json',v.hints_json,'options_json',v.options_json)
FROM payment_orders o,json_each(o.exam_payload_json,'$.ids') item
JOIN question_versions v ON v.id=item.value JOIN questions q ON q.id=v.question_id
WHERE o.purchase_type='exam' AND o.status IN ('pending','paid');
