-- Additive, no legacy data rewrite or source/question seed.
CREATE TABLE group_game_rooms (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL CHECK(mode IN ('capture_flag','animal_race')),
    grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX group_games_waiting ON group_game_rooms(status,grade,mode);
CREATE TABLE group_game_requests (
    student_id INTEGER NOT NULL REFERENCES students(id),
    request_key TEXT NOT NULL,
    signature TEXT NOT NULL,
    room_id TEXT NOT NULL REFERENCES group_game_rooms(id),
    PRIMARY KEY(student_id,request_key)
);
CREATE TABLE group_game_rewards (
    room_id TEXT NOT NULL REFERENCES group_game_rooms(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    mode TEXT NOT NULL,
    rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 5),
    points INTEGER NOT NULL CHECK(points BETWEEN 0 AND 5),
    awarded_at INTEGER NOT NULL,
    PRIMARY KEY(room_id,student_id)
);
CREATE INDEX group_game_scores ON group_game_rewards(mode,student_id);
