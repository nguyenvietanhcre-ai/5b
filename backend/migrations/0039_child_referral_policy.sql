CREATE TABLE child_referral_order_pins (
 order_id INTEGER PRIMARY KEY REFERENCES payment_orders(id), policy TEXT NOT NULL,
 invitee_student_id INTEGER NOT NULL REFERENCES students(id),
 referrer_student_id INTEGER REFERENCES students(id), code TEXT NOT NULL
);
CREATE TABLE child_referral_rewards (
 invitee_student_id INTEGER PRIMARY KEY REFERENCES students(id),
 referrer_student_id INTEGER NOT NULL REFERENCES students(id),
 order_id INTEGER NOT NULL UNIQUE REFERENCES payment_orders(id),
 tier TEXT NOT NULL CHECK(tier IN ('VIP','VIP+')), days INTEGER NOT NULL CHECK(days=7), granted_at TEXT NOT NULL
);
CREATE TRIGGER child_referral_rewards_immutable BEFORE UPDATE ON child_referral_rewards BEGIN SELECT RAISE(ABORT,'Keep referral reward history'); END;
CREATE TRIGGER child_referral_rewards_keep BEFORE DELETE ON child_referral_rewards BEGIN SELECT RAISE(ABORT,'Keep referral reward history'); END;
CREATE TABLE child_referral_periods (
 order_id INTEGER PRIMARY KEY REFERENCES child_referral_rewards(order_id),
 account_id INTEGER NOT NULL REFERENCES accounts(id), tier TEXT NOT NULL,
 starts_at TEXT, ends_at TEXT
);
