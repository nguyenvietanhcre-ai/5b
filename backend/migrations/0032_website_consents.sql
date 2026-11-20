CREATE TABLE website_policy_snapshots (
 version TEXT PRIMARY KEY,
 content_json TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE website_account_consents (
 id INTEGER PRIMARY KEY,
 account_id INTEGER NOT NULL REFERENCES accounts(id),
 version TEXT NOT NULL REFERENCES website_policy_snapshots(version),
 representative_name TEXT NOT NULL,
 representative_contact TEXT NOT NULL,
 representative_role TEXT NOT NULL,
 accepted_at TEXT NOT NULL,
 UNIQUE(account_id, version)
);
