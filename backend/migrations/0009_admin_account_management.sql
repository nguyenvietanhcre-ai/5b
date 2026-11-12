ALTER TABLE accounts ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0);
ALTER TABLE accounts ADD COLUMN deleted_at TEXT;
ALTER TABLE arena_members ADD COLUMN revoked_at TEXT;
CREATE INDEX accounts_admin_status ON accounts(deleted_at, status, id DESC);
