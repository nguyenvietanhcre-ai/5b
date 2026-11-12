"""Settings shared by the student API and staff controls."""
import json
from .platform_api import APIError


def settings(db):
    row = db.execute("SELECT value_json,revision FROM system_settings WHERE name='platform'").fetchone()
    return {**json.loads(row['value_json']), 'revision': row['revision']}


def require_feature(db, name):
    if not settings(db).get(name, True):
        raise APIError('Chức năng đang được quản trị viên tạm dừng. Vui lòng quay lại sau.', 403)
