CREATE TABLE lesson_material_files (
    resource_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK(provider IN ('main','native')),
    lesson_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL CHECK(mime='application/pdf'),
    size INTEGER NOT NULL CHECK(size>0 AND size<=5242880),
    sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    created_at TEXT NOT NULL,
    storage_version INTEGER NOT NULL CHECK(storage_version=1)
);
CREATE TABLE lesson_material_bindings (
    provider TEXT NOT NULL CHECK(provider IN ('main','native')),
    lesson_key TEXT NOT NULL,
    lesson_revision INTEGER NOT NULL CHECK(lesson_revision>0),
    resource_id TEXT NOT NULL REFERENCES lesson_material_files(resource_id),
    grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),
    published INTEGER NOT NULL CHECK(published IN (0,1)),
    PRIMARY KEY(provider,lesson_key,lesson_revision,resource_id)
);
CREATE TRIGGER lesson_material_files_immutable_update BEFORE UPDATE ON lesson_material_files
BEGIN SELECT RAISE(ABORT,'Lesson material files are immutable'); END;
CREATE TRIGGER lesson_material_files_immutable_delete BEFORE DELETE ON lesson_material_files
BEGIN SELECT RAISE(ABORT,'Lesson material files are immutable'); END;
