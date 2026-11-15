"""Learning tables share the tenant transaction, with an explicit SQL namespace.

Only schema identifiers from the sealed empty-store schema are rewritten. SQL
parameters, user text, JSON payloads and question/answer identities are retained.
"""
import json
import re
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from sqlite_storage import Connection, Cursor

PREFIX = 'native_learning_'
HERE = Path(__file__).resolve().parent
NAMES = frozenset(json.loads((HERE / 'learning-names.json').read_text())) | {'content_retirement_policy','group_games_qa_owner'}
TOKEN = re.compile(r"--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9]*", re.S)


def rewrite(statement, parameters=()):
    metadata = bool(re.search(r'\bsqlite_master\b|\bPRAGMA\b', statement, re.I))
    masked=TOKEN.sub(lambda m:' ' if m[0].startswith(("'",'--','/*')) else m[0],statement)
    aliases=set(re.findall(r'(?i)(?:\bWITH|,)\s*([a-z_][a-z_0-9]*)\s+AS\s*\(',masked))
    for reference in re.finditer(r'(?i)\b(?:FROM|JOIN|INTO|UPDATE|REFERENCES)\s+(?:OR\s+[a-z]+\s+)?["`\[]?([a-z_][a-z_0-9]*)',masked):
        name=reference[1].lower()
        if name not in NAMES and name not in aliases and name not in ('sqlite_master','json_each','json_tree','set','of','on'):
            raise sqlite3.OperationalError('Learning SQL references an unregistered table: '+name)
    def token(match):
        value = match[0]
        if value.startswith(('--', '/*')):
            return value
        if value.startswith("'"):
            plain = value[1:-1].replace("''", "'")
            return "'" + PREFIX + plain + "'" if metadata and plain in NAMES else value
        quote = value[0] if value[0] in ('"', '`', '[') else ''
        plain = value[1:-1] if quote else value
        plain=plain.lower()
        if plain not in NAMES:
            return value
        return quote + PREFIX + plain + (']' if quote == '[' else quote) if quote else PREFIX + plain
    sql = TOKEN.sub(token, statement)
    values = tuple(PREFIX + v if metadata and isinstance(v, str) and v in NAMES else v for v in parameters)
    if metadata:
        # Missing optional tables must never resolve to a table in main.
        sql=re.sub(r"(?i)(\b(?:name|tbl_name)\s*=\s*)'([^']*)'",lambda m:m[1]+"'"+(m[2] if m[2].startswith(PREFIX) else PREFIX+m[2])+"'",sql)
        if len(values)==1 and isinstance(values[0],str) and re.search(r'(?i)\b(?:name|tbl_name)\s*=\s*\?',statement):
            value=values[0];values=(value if value.startswith(PREFIX) else PREFIX+value,)
    return sql, values


class LearningConnection(Connection):
    def execute(self, statement, parameters=()):
        sql, values = rewrite(statement, parameters)
        result = super().execute(sql, values)
        # Schema discovery exposes logical names only within this store.
        if re.search(r'\bFROM\s+sqlite_master\b', statement, re.I) and result.description:
            names = [c[0] for c in result.description]
            rows = []
            for row in result.fetchall():
                values = list(row)
                if 'name' in names:
                    i = names.index('name')
                    if not isinstance(values[i], str) or not values[i].startswith(PREFIX):
                        continue
                    values[i] = values[i][len(PREFIX):]
                rows.append(values)
            return Cursor(names, rows)
        return result


class LearningDatabase:
    def __init__(self, parent):
        self.parent = parent
        self.storage = parent.storage

    @contextmanager
    def connect(self, write=False):
        # Use the parent's preflight and replay; never open a second transaction.
        with self.parent.connect(write):
            yield LearningConnection(self)

    def transaction(self, callback):
        return self.parent.transaction(callback)

    def initialize(self):
        with self.connect(True) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_environment'").fetchone():
                from backend.database import execute_sql
                execute_sql(db, (HERE / 'learning-seed.sql').read_text(encoding='utf-8'))
