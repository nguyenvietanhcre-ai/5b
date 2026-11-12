"""Apply versioned migrations and read the database demo."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

BACKEND = Path(__file__).resolve().parent


def execute_sql(connection, sql):
    statement = ''
    for line in sql.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ''
    if statement.strip():
        raise ValueError('Incomplete SQL statement')


def initialize(path: Path):
    if hasattr(path, 'initialize'):
        path.initialize()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=15)) as connection:
        connection.execute('PRAGMA journal_mode = WAL')
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        with connection:
            connection.execute(
                'CREATE TABLE IF NOT EXISTS schema_migrations '
                '(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)'
            )
            applied = {row[0] for row in connection.execute('SELECT name FROM schema_migrations')}
            for migration in sorted((BACKEND / 'migrations').glob('*.sql')):
                if migration.name not in applied:
                    execute_sql(connection, migration.read_text(encoding='utf-8'))
                    connection.execute('INSERT INTO schema_migrations (name) VALUES (?)', (migration.name,))


def count_published_exams(path: Path) -> int:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        return connection.execute("SELECT COUNT(*) FROM exams WHERE status = 'published'").fetchone()[0]


def demo_samples(path: Path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        payload = connection.execute((BACKEND / 'demo-report.sql').read_text(encoding='utf-8')).fetchone()[0]
    return json.loads(payload)
