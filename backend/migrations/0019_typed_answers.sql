-- Old attempts keep their immutable multiple-choice contract and saved scores.
ALTER TABLE exams ADD COLUMN response_mode TEXT NOT NULL DEFAULT 'choice'
    CHECK (response_mode IN ('choice', 'typed'));
