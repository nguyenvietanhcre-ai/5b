-- Parent settings only. Successful admissions remain in the existing nonce ledger.
CREATE TABLE child_game_limits (
    student_id INTEGER NOT NULL REFERENCES family_children(student_id),
    game TEXT NOT NULL CHECK(game IN ('duel','capture_flag','animal_race')),
    daily_limit INTEGER CHECK(daily_limit IS NULL OR (typeof(daily_limit)='integer' AND daily_limit BETWEEN 0 AND 1000)),
    PRIMARY KEY(student_id,game)
);

CREATE INDEX game_claim_requests_student_day ON game_claim_requests(student_id,created_at,game,room_id);
CREATE INDEX game_claim_requests_student_room ON game_claim_requests(student_id,game,room_id,created_at);
