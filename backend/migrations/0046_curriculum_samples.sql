-- Empty sample registries only. Questions require an explicit validated local import.

CREATE TABLE IF NOT EXISTS curriculum_sample_batches(batch_id TEXT PRIMARY KEY,package_sha256 TEXT NOT NULL,authorization_json TEXT NOT NULL,status TEXT NOT NULL CHECK(status='active'),teacher_review TEXT NOT NULL CHECK(teacher_review='pending'),installed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS curriculum_sample_versions(content_key TEXT PRIMARY KEY,version_id INTEGER NOT NULL UNIQUE REFERENCES question_versions(id),batch_id TEXT NOT NULL REFERENCES curriculum_sample_batches(batch_id),grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),topic_key TEXT NOT NULL,skill_key TEXT NOT NULL,band TEXT NOT NULL,access TEXT NOT NULL CHECK(access IN ('free','paid')),score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10),content_sha256 TEXT NOT NULL,payload_sha256 TEXT NOT NULL,diagram_sha256 TEXT,metadata_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS curriculum_sample_grade_pool ON curriculum_sample_versions(grade,access,band);
CREATE TABLE IF NOT EXISTS curriculum_sample_assets(sha256 TEXT PRIMARY KEY,svg BLOB NOT NULL,alt TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL);
