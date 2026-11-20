ALTER TABLE payment_orders ADD COLUMN subscription_period TEXT NOT NULL DEFAULT 'month' CHECK(subscription_period IN ('month','year'));
ALTER TABLE payment_orders ADD COLUMN subscription_starts_at TEXT;
ALTER TABLE payment_orders ADD COLUMN subscription_ends_at TEXT;
