-- A year correction requires a matching, single-use admin permit in the same
-- application transaction. Ordinary SQL updates and student profile writes
-- retain the original immutable-year protection.
CREATE TABLE admin_birth_year_permits (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    old_birth_year INTEGER NOT NULL,
    new_birth_year INTEGER NOT NULL,
    CHECK (old_birth_year <> new_birth_year)
);
CREATE TRIGGER admin_birth_year_permits_validate
BEFORE INSERT ON admin_birth_year_permits
WHEN NOT EXISTS (
    SELECT 1 FROM staff_users u JOIN accounts a ON a.id=NEW.account_id
    WHERE u.id=NEW.staff_id AND u.role='admin' AND u.status='active'
      AND a.birth_year=NEW.old_birth_year AND a.deleted_at IS NULL
)
BEGIN
    SELECT RAISE(ABORT, 'A valid admin correction permit is required');
END;
DROP TRIGGER accounts_birth_year_immutable;
CREATE TRIGGER accounts_birth_year_immutable
BEFORE UPDATE OF birth_year ON accounts
WHEN NEW.birth_year <> OLD.birth_year AND NOT EXISTS (
    SELECT 1 FROM admin_birth_year_permits p JOIN staff_users u ON u.id=p.staff_id
    WHERE p.account_id=OLD.id AND p.old_birth_year=OLD.birth_year AND p.new_birth_year=NEW.birth_year
      AND u.role='admin' AND u.status='active'
)
BEGIN
    SELECT RAISE(ABORT, 'Birth year is immutable without an admin correction');
END;
CREATE TRIGGER accounts_birth_year_permit_consume
AFTER UPDATE OF birth_year ON accounts
WHEN NEW.birth_year <> OLD.birth_year
BEGIN
    DELETE FROM admin_birth_year_permits WHERE account_id=NEW.id;
END;

-- Invalidate a full-profile admin form when another workflow changes fields
-- shown in that form. Revisions are opaque monotonic values, not edit counts.
CREATE TRIGGER companion_admin_profile_revision
AFTER UPDATE OF mascot_id,xp ON student_companions
WHEN NEW.mascot_id <> OLD.mascot_id OR NEW.xp <> OLD.xp
BEGIN
    UPDATE accounts SET revision=revision+1
    WHERE id=(SELECT account_id FROM students WHERE id=NEW.student_id);
END;
CREATE TRIGGER vip_admin_profile_revision
AFTER UPDATE OF vip_expires_at ON accounts
WHEN NEW.vip_expires_at IS NOT OLD.vip_expires_at AND NEW.revision=OLD.revision
BEGIN
    UPDATE accounts SET revision=revision+1 WHERE id=NEW.id;
END;
CREATE TRIGGER entitlement_admin_profile_revision_insert
AFTER INSERT ON access_entitlements
BEGIN
    UPDATE accounts SET revision=revision+1 WHERE id=NEW.account_id;
END;
CREATE TRIGGER entitlement_admin_profile_revision_update
AFTER UPDATE ON access_entitlements
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.enrollment_id IS NOT OLD.enrollment_id
  OR NEW.kind IS NOT OLD.kind OR NEW.starts_at IS NOT OLD.starts_at OR NEW.ends_at IS NOT OLD.ends_at
BEGIN
    UPDATE accounts SET revision=revision+1 WHERE id=NEW.account_id OR id=OLD.account_id;
END;
CREATE TRIGGER entitlement_admin_profile_revision_delete
AFTER DELETE ON access_entitlements
BEGIN
    UPDATE accounts SET revision=revision+1 WHERE id=OLD.account_id;
END;
