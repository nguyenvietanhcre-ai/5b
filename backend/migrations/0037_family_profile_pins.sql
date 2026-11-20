-- Add only capability metadata; historical learner data and PIN hashes survive.
ALTER TABLE family_devices ADD COLUMN active_profile TEXT NOT NULL DEFAULT 'profiles'
 CHECK(active_profile IN ('profiles','parent','child'));
ALTER TABLE family_devices ADD COLUMN pin_setup_until TEXT;
UPDATE family_devices SET active_profile=CASE
 WHEN scope IN ('parent_read','parent_full') THEN 'parent'
 WHEN scope='child' THEN 'child' ELSE 'profiles' END;
CREATE TABLE family_registration_consents (
 family_id INTEGER PRIMARY KEY REFERENCES family_accounts(id),
 version TEXT NOT NULL, representative_name TEXT NOT NULL,
 representative_contact TEXT NOT NULL, representative_role TEXT NOT NULL,
 content_sha256 TEXT NOT NULL, accepted_at TEXT NOT NULL
);
-- This lock covers unauthenticated device replacement, not existing sessions.
CREATE TABLE family_replacement_pin_locks (
 family_id INTEGER PRIMARY KEY REFERENCES family_accounts(id),
 failures INTEGER NOT NULL DEFAULT 0, locked_until TEXT
);
