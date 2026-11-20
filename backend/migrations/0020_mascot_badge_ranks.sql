-- Rebuild the three legacy XP tables, retaining IDs and all earned XP.
-- Deferred checks allow parent tables to be replaced inside this transaction.
PRAGMA defer_foreign_keys = ON;
CREATE TABLE mascot_levels_new (
    level INTEGER PRIMARY KEY CHECK (level > 0),
    min_xp INTEGER NOT NULL UNIQUE CHECK (min_xp >= 0)
);
INSERT INTO mascot_levels_new SELECT level, MAX(0,min_xp-1000) FROM mascot_levels;
DROP TABLE mascot_levels;
ALTER TABLE mascot_levels_new RENAME TO mascot_levels;
CREATE TABLE student_companions_new (
    student_id INTEGER PRIMARY KEY REFERENCES students(id),
    mascot_id INTEGER NOT NULL REFERENCES mascots(id),
    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0)
);
INSERT INTO student_companions_new SELECT student_id,mascot_id,MAX(0,xp-1000) FROM student_companions;
DROP TABLE student_companions;
ALTER TABLE student_companions_new RENAME TO student_companions;
CREATE INDEX student_companions_ranking ON student_companions(xp DESC,student_id);
CREATE TRIGGER companion_admin_profile_revision
AFTER UPDATE OF mascot_id,xp ON student_companions
WHEN NEW.mascot_id <> OLD.mascot_id OR NEW.xp <> OLD.xp
BEGIN
    UPDATE accounts SET revision=revision+1 WHERE id=(SELECT account_id FROM students WHERE id=NEW.student_id);
END;
UPDATE accounts SET revision=revision+1 WHERE id IN (SELECT account_id FROM students WHERE id IN (SELECT student_id FROM student_companions));
CREATE TABLE bots_new (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('training','matchmaking')),
    display_name TEXT NOT NULL,
    skill_level INTEGER NOT NULL CHECK (skill_level BETWEEN 1 AND 3),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0)
);
INSERT INTO bots_new SELECT id,kind,display_name,skill_level,active,MAX(0,xp-1000) FROM bots;
DROP TABLE bots;
ALTER TABLE bots_new RENAME TO bots;
-- Never clear deferred enforcement until the replacement schema is valid.
CREATE TEMP TABLE mascot_rank_fk_check (violations INTEGER CHECK (violations=0));
INSERT INTO mascot_rank_fk_check SELECT COUNT(*) FROM pragma_foreign_key_check;
DROP TABLE mascot_rank_fk_check;
PRAGMA defer_foreign_keys = OFF;
