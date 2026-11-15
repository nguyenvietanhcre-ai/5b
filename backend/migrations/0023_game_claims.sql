-- Main-account game occupancy only; no legacy content/history/quota rewrites.
CREATE TABLE game_claims (
 student_id INTEGER PRIMARY KEY REFERENCES students(id),
 account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
 claim_id TEXT NOT NULL UNIQUE,
 game TEXT NOT NULL CHECK(game IN ('duel','capture_flag','animal_race')),
 play_mode TEXT NOT NULL CHECK(play_mode IN ('human','bot')),
 room_id TEXT NOT NULL,
 source_pool TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 created_at INTEGER NOT NULL,
 updated_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL
);
CREATE TABLE game_claim_requests (
 student_id INTEGER NOT NULL REFERENCES students(id),
 request_key TEXT NOT NULL,
 signature TEXT NOT NULL,
 claim_id TEXT NOT NULL,
 game TEXT NOT NULL,
 room_id TEXT NOT NULL,
 status TEXT NOT NULL,
 response_json TEXT NOT NULL,
 created_at INTEGER NOT NULL,
 PRIMARY KEY(student_id,request_key)
);
CREATE INDEX game_claim_room ON game_claims(game,room_id);
