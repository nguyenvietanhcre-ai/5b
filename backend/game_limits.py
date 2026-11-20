"""Daily parental caps on distinct successful room admissions in Vietnam time."""
from datetime import datetime, timedelta

from . import platform_api as api


GAMES = {'duel': 'Đấu trí', 'capture_flag': 'Cướp Cờ', 'animal_race': 'Đua Thú'}
MAX_LIMIT = 1000


def _day_window(clock_ms):
    local = datetime.fromtimestamp(clock_ms / 1000, api.VN)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.date().isoformat(), int(start.timestamp() * 1000), int((start + timedelta(days=1)).timestamp() * 1000)


def _used(db, student_id, start_ms, end_ms):
    # A waiting-room member may leave and rejoin on a fresh nonce. Attribute
    # that room only to its first successful admission day for this student.
    return dict(db.execute('''
        SELECT admission.game, count(DISTINCT admission.room_id)
        FROM game_claim_requests AS admission
        WHERE admission.student_id=? AND admission.created_at>=? AND admission.created_at<?
          AND NOT EXISTS (
              SELECT 1 FROM game_claim_requests AS earlier
              WHERE earlier.student_id=admission.student_id AND earlier.game=admission.game
                AND earlier.room_id=admission.room_id AND earlier.created_at<?
          )
        GROUP BY admission.game
    ''', (student_id, start_ms, end_ms, start_ms)))


def _games(db, student_id, start_ms, end_ms):
    limits = dict(db.execute('SELECT game,daily_limit FROM child_game_limits WHERE student_id=?', (student_id,)))
    used = _used(db, student_id, start_ms, end_ms)
    games = []
    for game, label in GAMES.items():
        count, limit = used.get(game, 0), limits.get(game)
        games.append({'id': game, 'label': label, 'limit': limit, 'used': count,
                      'remaining': None if limit is None else max(0, limit - count)})
    return games


def view(db, student_id, clock_ms):
    day, start_ms, end_ms = _day_window(clock_ms)
    return {'childId': student_id, 'day': day, 'maxLimit': MAX_LIMIT,
            'games': _games(db, student_id, start_ms, end_ms)}


def _clock_view(day, clock_ms, end_ms):
    return {'day': day, 'timeZone': 'Asia/Ho_Chi_Minh',
            'serverTime': datetime.fromtimestamp(clock_ms / 1000, api.VN).isoformat(timespec='milliseconds'),
            'resetsAt': datetime.fromtimestamp(end_ms / 1000, api.VN).isoformat(timespec='milliseconds')}


def student_view(db, student_id, clock_ms):
    day, start_ms, end_ms = _day_window(clock_ms)
    return {**_clock_view(day, clock_ms, end_ms), 'childId': student_id,
            'games': _games(db, student_id, start_ms, end_ms)}


def family_view(db, student_ids, clock_ms):
    day, start_ms, end_ms = _day_window(clock_ms)
    return {**_clock_view(day, clock_ms, end_ms),
            'children': [{'childId': student_id, 'games': _games(db, student_id, start_ms, end_ms)}
                         for student_id in student_ids]}


def save(db, student_id, values):
    if not isinstance(values, dict) or set(values) != GAMES.keys() or any(
            value is not None and (type(value) is not int or not 0 <= value <= MAX_LIMIT)
            for value in values.values()):
        raise api.APIError(f'Nhập số lượt nguyên từ 0 đến {MAX_LIMIT} hoặc để trống cho từng trò chơi.')
    for game in GAMES:
        db.execute('''INSERT INTO child_game_limits(student_id,game,daily_limit) VALUES (?,?,?)
                      ON CONFLICT(student_id,game) DO UPDATE SET daily_limit=excluded.daily_limit''',
                   (student_id, game, values[game]))


def require_new_admission(db, student_id, game, room_id, clock_ms):
    """Called before inserting a successful nonce under the same writer lock."""
    rule = db.execute('SELECT daily_limit FROM child_game_limits WHERE student_id=? AND game=?',
                      (student_id, game)).fetchone()
    if rule is None or rule[0] is None:
        return
    known = db.execute('SELECT 1 FROM game_claim_requests WHERE student_id=? AND game=? AND room_id=? LIMIT 1',
                       (student_id, game, room_id)).fetchone()
    if known:
        return
    _, start_ms, end_ms = _day_window(clock_ms)
    if rule[0] == 0 or _used(db, student_id, start_ms, end_ms).get(game, 0) >= rule[0]:
        error = api.APIError(f'Em đã dùng hết lượt {GAMES[game]} hôm nay theo giới hạn của phụ huynh.', 429)
        error.code = 'parent_game_limit'
        raise error
