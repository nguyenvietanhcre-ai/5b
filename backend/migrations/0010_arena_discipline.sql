CREATE TABLE arena_discipline_events (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    duel_id INTEGER NOT NULL REFERENCES duels(id),
    kind TEXT NOT NULL CHECK (kind IN ('forfeit', 'disconnect')),
    occurred_at REAL NOT NULL,
    is_strike INTEGER NOT NULL CHECK (is_strike IN (0, 1)),
    cooldown_until REAL NOT NULL DEFAULT 0,
    UNIQUE (duel_id, student_id)
);
CREATE INDEX arena_discipline_recent ON arena_discipline_events(student_id, occurred_at);
