-- Keep every new homework BLOB below SQLite Durable Object's row limit.
-- Existing inline submissions remain unchanged and continue to be readable.
CREATE TABLE class_submission_chunks (
    submission_id INTEGER NOT NULL REFERENCES class_submissions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK(position >= 0),
    content BLOB NOT NULL CHECK(typeof(content) = 'blob' AND length(content) BETWEEN 1 AND 1048576),
    PRIMARY KEY(submission_id, position)
);
