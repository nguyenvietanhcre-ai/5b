CREATE TABLE referral_reward_confirmations (
    referral_id INTEGER PRIMARY KEY REFERENCES account_referrals(id),
    confirmed_by INTEGER NOT NULL REFERENCES staff_users(id),
    confirmed_at TEXT NOT NULL
);

CREATE TRIGGER referral_reward_confirmation_immutable
BEFORE UPDATE ON referral_reward_confirmations
BEGIN
    SELECT RAISE(ABORT, 'Referral reward confirmation is immutable');
END;

CREATE TRIGGER referral_reward_confirmation_keep_history
BEFORE DELETE ON referral_reward_confirmations
BEGIN
    SELECT RAISE(ABORT, 'Keep referral reward confirmation history');
END;
