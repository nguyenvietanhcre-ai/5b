-- Additive evidence only. Legacy orders stay NULL; no invented historical consent.
ALTER TABLE payment_orders ADD COLUMN accepted_policy_version TEXT;
ALTER TABLE payment_orders ADD COLUMN accepted_policy_at TEXT;
ALTER TABLE payment_orders ADD COLUMN purchaser_json TEXT;
ALTER TABLE payment_orders ADD COLUMN checkout_snapshot_json TEXT;
CREATE INDEX payment_orders_owner_history ON payment_orders(account_id,id DESC);
