"""Finite public pilot, isolated from student data and all commercial ledgers.

Public keep/claim/history endpoints are retired. Existing claimed history is
retained; SQLite still serializes the temporary demo session and its answers.
"""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
from copy import deepcopy
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

from . import platform_api as api
from .answers import matches, validate_rule
from .arena import Arena, ArenaError
from .group_game_bots import BotGroupGames

BASE = '/api/trial/'
IDLE = 1800_000
WARN = 120_000
DAY = 86400_000
TEN_MINUTES = 600_000
BROWSER_COOKIE = '5bmath_trial_browser'
MODES = ('practice', 'bot', 'capture_flag', 'animal_race')
THEMES = ('garden', 'morning', 'crayon', 'sprout', 'notebook')
MASCOTS = ('cat', 'rabbit', 'horse', 'voi', 'tiger', 'lion', 'gau', 'sparrow', 'eagle',
           'cu-meo', 'butterfly', 'bee', 'ca-map', 'dolphin', 'octopus', 'crab',
           'starfish', 'fox', 'sprout', 'dog')


def clock():
    return int(time.time() * 1000)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fail(message, status=400):
    raise api.APIError(message, status)


def cookie_value(handler, name):
    cookie = SimpleCookie()
    try:
        cookie.load(handler.headers.get('Cookie', ''))
        value = cookie[name].value if name in cookie else ''
        return value if len(value) <= 150 else ''
    except (ValueError, KeyError):
        return ''


def set_cookie(handler, name, token, age):
    handler.api_headers['Set-Cookie'] = api.session_cookie(name, token, age)


def load_content(grade=5):
    """No bank import, selector or seed: one pinned, bounded public file."""
    from .curriculum_samples import trial_content
    samples=trial_content(grade)
    if samples is not None:return samples
    content = json.loads(Path(__file__).with_name('trial-content.json').read_text(encoding='utf-8-sig'))
    questions = content['questions']
    seen = set()
    if not 20 <= len(questions) <= 50:
        fail('Bộ mẫu Toán 5 chưa đủ điều kiện.', 503)
    for q in questions:
        if (q['id'] in seen or q['grade'] != 5 or q['difficulty'] not in (1, 2)
                or q['reviewStatus'] != 'arithmetic_checked' or not q.get('revision')
                or q['answerKind'] != 'number' or not q.get('source')):
            fail('Bộ mẫu chưa đủ thông tin kiểm tra.', 503)
        validate_rule(q['answer'], 'number')
        seen.add(q['id'])
    for section in content['lesson'].get('sections', []):
        content['lesson'][{'detail': 'solution'}.get(section['key'], section['key'])] = section['body']
    return content


def config():
    content = load_content()
    return {'demo': True, 'pilotGrade': 5, 'grades': [
        {'grade': n, 'ready': n == 5 or bool(content.get('curriculumSamples')), 'reason': '' if n == 5 or content.get('curriculumSamples') else 'Đang chuẩn bị bộ mẫu phù hợp.'}
        for n in range(1, 6)], 'pool': {
            'revision': content['revision'], 'count': len(content['questions']),
            'reviewStatus': 'arithmetic_checked', 'teacherReview': 'pending',
            'notice': 'Mẫu tự biên soạn cho pilot localhost; đã kiểm phép tính, chờ giáo viên duyệt.'},
        'modes': [{'key': m, 'title': {'bot': 'Đấu trí với BOT', 'capture_flag': 'Cướp Cờ',
                    'animal_race': 'Đua Thú'}[m], 'minimumQuestions': 20 if m == 'bot' else 5,
                   'ready': len(eligible(content, m)) >= (20 if m == 'bot' else 5)}
                  for m in MODES[1:]],
        'idleSeconds': IDLE // 1000, 'warnSeconds': WARN // 1000,
        'absoluteSeconds': DAY // 1000, 'qaBotCheck': True,
        'botCheckNotice': 'Kiểm tra cục bộ bằng mẫu QA; chưa là chống bot production.',
        'preferences': True, 'orderPreview': True, 'mascots': list(MASCOTS), 'themes': list(THEMES)}


def eligible(content, mode):
    return [q for q in content['questions'] if mode in q.get('purposes', [])
            and q['grade'] == content.get('grade',5) and q['difficulty'] in (1, 2)]


def cleanup(db, at=None):
    at = clock() if at is None else at
    db.execute('DELETE FROM trial_events WHERE occurred_at<?', (at - 7 * DAY,))
    # Claimed history is independent of transient package/state retention.
    db.execute('DELETE FROM trial_keep_packages WHERE expires_at<=?', (at,))
    # Expiry removes transient state at the next cleanup, without an extra day
    # of retention. Keep packages reference session IDs without a foreign key
    # and claimed histories are independent, so AFK must not erase either.
    db.execute('DELETE FROM trial_sessions WHERE absolute_expires_at<=? OR '
               'revoked_at IS NOT NULL OR last_activity_at<=?', (at, at - IDLE))
    db.execute('DELETE FROM trial_counters WHERE expires_at<=?', (at,))
    db.execute('DELETE FROM trial_browsers WHERE expires_at<? AND '
               'id NOT IN (SELECT browser_id FROM trial_sessions) AND '
               'id NOT IN (SELECT browser_id FROM trial_keep_packages) AND '
               'id NOT IN (SELECT browser_id FROM trial_counters)', (at,))


def start_cleanup_worker(database_path, *, interval_seconds=3600, stop_event=None, frozen=None):
    """Root starts once after migrations; removes expired data without traffic.

    Returns (thread, stop_event) for clean shutdown/test isolation. Storage errors
    retry at the next interval; no request data, secrets or exception SQL is logged.
    """
    if not 1 <= interval_seconds <= 86400:
        raise ValueError('Trial cleanup interval must be at most one day')
    stopped = stop_event or threading.Event()
    def run():
        while not stopped.is_set():
            try:
                if frozen is None or not frozen():
                    with api.connect(database_path, True) as db:
                        # Recheck after acquiring the writer, so a cutover
                        # freeze also covers background expiry deletion.
                        if frozen is None or not frozen():cleanup(db)
            except sqlite3.Error:
                pass
            if stopped.wait(interval_seconds):
                break
    worker = threading.Thread(target=run, name='5bmath-trial-cleanup', daemon=True)
    worker.start()
    return worker, stopped


def event(db, at, name):
    # Explicit event vocabulary only; never request bodies, headers, URLs or IDs.
    if name not in ('create', 'reset', 'end', 'limited'):
        raise ValueError('Unknown trial event')
    db.execute('INSERT INTO trial_events(occurred_at,event) VALUES (?,?)', (at, name))


def browser(db, handler, at, create=False):
    token = cookie_value(handler, BROWSER_COOKIE)
    row = db.execute('SELECT * FROM trial_browsers WHERE secret_hash=? AND expires_at>?',
                     (digest(token), at)).fetchone() if token else None
    if row is None and create:
        token, bid, csrf = secrets.token_urlsafe(32), secrets.token_hex(16), secrets.token_urlsafe(32)
        db.execute('INSERT INTO trial_browsers VALUES (?,?,?,?,?,NULL,0)',
                   (bid, digest(token), csrf, at, at + 3 * DAY))
        set_cookie(handler, BROWSER_COOKIE, token, 3 * DAY // 1000)
        row = db.execute('SELECT * FROM trial_browsers WHERE id=?', (bid,)).fetchone()
    elif row is not None and create:
        db.execute('UPDATE trial_browsers SET expires_at=? WHERE id=?', (at + 3 * DAY, row['id']))
        set_cookie(handler, BROWSER_COOKIE, token, 3 * DAY // 1000)
    return row


def counter(db, bid, at):
    db.execute('INSERT OR IGNORE INTO trial_counters(browser_id,expires_at) VALUES (?,?)', (bid, at + DAY))
    return db.execute('SELECT * FROM trial_counters WHERE browser_id=?', (bid,)).fetchone()


def limit(db, handler, b, at, creating=False, body=None):
    row = counter(db, b['id'], at)
    requests = [x for x in json.loads(row['requests_json']) if x > at - 60_000]
    creates = [x for x in json.loads(row['creates_json']) if x > at - TEN_MINUTES]
    reason, until, challenge = '', row['cooldown_until'], False
    if until > at:
        reason = 'Em hãy nghỉ một chút rồi thử lại.'
    elif len(requests) >= 120:
        reason, until = 'Có quá nhiều thao tác. Em thử lại sau một phút.', at + 60_000
    elif creating and len(creates) >= 8:
        reason, until = 'Đã bắt đầu lại nhiều lần. Em thử lại sau 5 phút.', at + 300_000
    elif creating and len(creates) >= 5:
        adapter = getattr(handler.server, 'trial_bot_check', None)
        verified = adapter(handler, body or {}) if adapter else (body or {}).get('challenge') == '5BMath'
        if not verified:
            reason, challenge = 'Mẫu kiểm tra localhost: nhập 5BMath để tiếp tục.', True
    # A fixed process-wide resource bound is not a per-IP/NAT ban.
    if not reason and creating and db.execute('SELECT COUNT(*) FROM trial_sessions WHERE created_at>?',
                                               (at - TEN_MINUTES,)).fetchone()[0] >= 2000:
        reason, until = 'Khu trải nghiệm đang bận. Em thử lại sau một phút.', at + 60_000
    if len(requests) < 121:
        requests.append(at)
    if not reason and creating:
        creates.append(at)
    db.execute('UPDATE trial_counters SET requests_json=?,creates_json=?,cooldown_until=? WHERE browser_id=?',
               (api.packed(requests), api.packed(creates), until, b['id']))
    if reason:
        event(db, at, 'limited')
        handler.api_headers['Retry-After'] = str(max(1, (until - at) // 1000)) if until > at else '1'
        return {'error': reason, 'retryAt': max(at + 1000, until), 'challengeRequired': challenge,
                'qaBotCheck': True, 'csrf': b['csrf']}, 429


def session(db, b, at, body=None):
    row = db.execute('SELECT * FROM trial_sessions WHERE id=? AND browser_id=?',
                     (b['current_session'], b['id'])).fetchone() if b else None
    if not row and b and b['current_session']:
        # Cleanup may already have removed expired/revoked state. The browser's
        # monotonic generation persists independently for the next creation.
        fail('Phiên trải nghiệm đã hết hạn. Em có thể bắt đầu phiên mẫu mới.', 410)
    if not row or row['revoked_at'] is not None:
        fail('Hãy bắt đầu một phiên trải nghiệm mới.', 401)
    if at >= row['absolute_expires_at'] or at >= row['last_activity_at'] + IDLE:
        fail('Phiên trải nghiệm đã hết hạn. Em có thể bắt đầu phiên mẫu mới.', 410)
    if body is not None and (type(body.get('generation')) is not int or body['generation'] != row['generation']):
        fail('Phiên đã thay đổi ở tab khác. Hãy tải lại trạng thái.', 409)
    return row


def new_session(db, b, at, generation=1):
    sid = secrets.token_hex(16)
    generation = db.execute('SELECT generation FROM trial_browsers WHERE id=?', (b['id'],)).fetchone()[0] + 1
    db.execute('INSERT INTO trial_sessions VALUES (?,?,?,?,?,?,NULL,?)',
               (sid, b['id'], generation, at, at, at + DAY,
                api.packed({'lessonComplete': False, 'preferences': {'theme': 'garden', 'mascot': 'sprout'}})))
    db.execute('UPDATE trial_browsers SET current_session=?,generation=? WHERE id=?', (sid, generation, b['id']))
    return db.execute('SELECT * FROM trial_sessions WHERE id=?', (sid,)).fetchone()


def cancel_pending(db, b, at):
    db.execute('UPDATE trial_keep_packages SET cancelled_at=? WHERE browser_id=? '
               'AND claimed_at IS NULL AND cancelled_at IS NULL', (at, b['id']))


def question_view(q):
    return {k: q[k] for k in ('id', 'prompt', 'unit', 'difficulty', 'topic', 'answerKind') if k in q} | {
        'text': q['prompt'], 'responseMode':q.get('responseMode','typed'),
        **({'options':q['options']} if q.get('responseMode')=='choice' else {}),
        **({'sampleDiagram':q['sampleDiagram']} if q.get('sampleDiagram') else {})}


def engine_question(q):
    return {'id': q['id'], 'revision': q['revision'], 'text': q['prompt'], 'prompt': q['prompt'],
            'answer': q['answer'], 'answerKind':q.get('answerKind','number'), 'unit': q.get('unit', ''),
            'difficulty': q['difficulty'], 'responseMode':q.get('responseMode','typed'), 'steps': [q['explanation']],
            **({'options':q['options']} if q.get('responseMode')=='choice' else {})}


class TrialGroup(BotGroupGames):
    """Reuse the real BOT rules, replace every persistence/replay boundary."""
    def __init__(self, room, at):
        super().__init__(clock=lambda: at)
        self.room = room

    def _save(self, db, room, now):
        self.room = room

    def _load(self, db, rid):
        if rid != self.room['id']:
            fail('Phòng mẫu không tồn tại.', 404)
        return self.room

    def _replay(self, *args):
        return None

    def _remember(self, *args):
        pass


def new_duel(questions, aid, at, mascot):
    # Arena's trusted factory receives this finite list only; isolated instance.
    engine = Arena()
    payload = {'action': 'create', 'name': 'Em mẫu', 'grade':questions[0].get('grade',5), 'difficulty': 0,
               'scope': 'all', 'sourcePool': 'qa-separate', 'stats': {'mascot': mascot}}
    first = engine._enter(payload, at / 1000, lambda *_: [engine_question(q) for q in questions])
    engine._enter({**payload, 'action': 'join', 'name': 'BOT mẫu', 'code': first['code'],
                   'stats': {'mascot': 'fox'}}, at / 1000)
    room = engine.rooms[first['code']]
    # Internal tokens are never browser-visible and only identify these two seats.
    room.update(id=aid, status='preparing', readyAt=at / 1000 + 3, trialMe=first['token'])
    room['trialBotAt'] = at / 1000 + 3 + 45
    room['trialBotCorrect'] = secrets.randbelow(2) == 0
    return room


def tick_duel(room, at):
    engine, sec = Arena(), at / 1000
    # Apply every scheduled boundary in order. Background/sparse polling must
    # produce the same battle as polling every second.
    for _ in range(150):
        bot = next(p for key, p in room['players'].items() if key != room['trialMe'])
        if room['status'] == 'preparing':
            boundary, is_bot = room['readyAt'], False
        elif room['status'] != 'playing':
            break
        elif room['resolved']:
            boundary, is_bot = room['nextAt'], False
        else:
            boundary = room.get('defenseUntil') or room['deadline']
            due = room['trialBotAt']
            if room.get('defenseUntil') is not None and room['attacker'] == room['trialMe']:
                due = min(due, room['defenseUntil'] - 1)
            is_bot = bot['answer'] is None and due < boundary
            if is_bot:
                boundary = due
        if boundary > sec:
            break
        previous = room['index']
        if is_bot:
            q = room['questions'][room['index']]
            engine._answer(room, bot, {'answer': q['answer'] if room['trialBotCorrect'] else '−99999999'}, boundary)
        else:
            engine._tick(room, boundary)
        if room['index'] != previous:
            room['trialBotAt'] = room['deadline'] - 15
            room['trialBotCorrect'] = secrets.randbelow(2) == 0
    # Restore integer answer positions after JSON persistence.
    for p in room['players'].values():
        p['answers'] = {int(k): v for k, v in p['answers'].items()}
    view = engine._view(room, room['trialMe'])
    view['serverNow'] = at
    if view.get('result'):
        view['result'].update(points=0, mode='bot', ranked=False)
    if view.get('battle'):
        view['battle']['mode'] = 'bot'
    return view


def new_group(questions, mode, aid, at, mascot, revision):
    room = {'id': aid, 'code': 'TRIAL', 'mode': mode, 'grade':questions[0].get('grade',5), 'createdAt': at,
            'status': 'waiting', 'mapIndex': secrets.randbelow(10), 'round': 0, 'target': 5,
            'players': [], 'questions': [engine_question(q) for q in questions], 'deadline': None,
            'nextAt': None, 'rankings': [], 'winnerId': None, 'endReason': None,
            'sourceRevision': revision, 'playMode': 'bot', 'ranked': False}
    for seat, pet in enumerate((mascot, 'dog', 'cat', 'rabbit', 'sprout')):
        room['players'].append({'studentId': 1 if seat == 0 else -seat,
            'name': 'Em (mẫu)' if seat == 0 else 'BOT mẫu ' + str(seat), 'isBot': seat > 0,
            'mascot': pet, 'xp': 0, 'seat': seat, 'steps': 0, 'correct': 0, 'totalTimeMs': 0,
            'lastStepAt': at, 'answered': False, 'answerCorrect': None, 'forfeited': False})
    TrialGroup(room, at)._start_round(room, at)
    return room


def save_attempt(db, attempt):
    db.execute('UPDATE trial_attempts SET payload_json=? WHERE id=?', (api.packed(attempt), attempt['id']))


def attempt_view(db, attempt, at):
    mode, room = attempt['mode'], attempt.get('room')
    game = None
    if mode == 'bot':
        game = tick_duel(room, at)
        attempt['index'], attempt['status'] = room['index'], room['status']
    elif mode in ('capture_flag', 'animal_race'):
        engine = TrialGroup(room, at)
        engine._tick(None, room, at)
        game = engine.view(room, 1, at)
        attempt['index'], attempt['status'] = room['round'] - 1, room['status']
    save_attempt(db, attempt)
    q = attempt['questions'][attempt['index']] if attempt['index'] < len(attempt['questions']) else None
    if mode == 'bot' and (room['status'] != 'playing' or room['resolved']):
        q = None
    if mode in ('capture_flag', 'animal_race') and room['status'] != 'playing':
        q = None
    results = attempt['results']
    if mode == 'bot' and room['status'] != 'finished' and not room['resolved']:
        current_id = attempt['questions'][attempt['index']]['id']
        results = [r for r in results if r['questionId'] != current_id]
    return {'id': attempt['id'], 'mode': mode, 'status': attempt['status'],
            'total': len(attempt['questions']), 'index': attempt['index'],
            'currentQuestion': question_view(q) if q else None,
            'answers': attempt['draft'], 'scratch': attempt.get('scratch', ''), 'results': results,
            'score': sum(r['correct'] for r in results), 'game': game}


def fixture():
    return {'demo': True, 'label': 'Dữ liệu minh họa — không phải tài khoản hoặc giao dịch thật',
        'family': {'name': 'Gia đình Vườn Toán (mẫu)', 'children': [
            {'id': 'demo-an', 'name': 'An (mẫu)', 'grade': 5, 'plan': 'VIP',
             'progress': [{'title': 'Tiến độ minh họa: 60%', 'description': 'Đã đọc 3 trong 5 bài mẫu.'}]},
            {'id': 'demo-binh', 'name': 'Bình (mẫu)', 'grade': 3, 'plan': 'Free',
             'progress': [{'title': 'Tiến độ minh họa: 35%', 'description': 'Mỗi con giữ bài và gói riêng.'}]}]},
        'classes': [{'title': 'Lớp Toán 5 minh họa', 'schedule': 'Lịch minh họa, không có buổi học thật',
            'description': 'Lịch và lớp minh họa; không có buổi học thật.',
            'homework': 'Ôn phần trăm (mẫu)', 'comment': 'Nhận xét mẫu: nhớ xác định số làm gốc.',
            'fee': 'Học phí minh họa; chưa phát sinh khoản phải thu'}],
        'assignments': [{'title': 'Bài tập minh họa', 'description': 'Ôn phần trăm; không nhận bài nộp thật.'}],
        'comments': [{'title': 'Nhận xét mẫu', 'description': 'Nhớ xác định số làm gốc trước khi tính phần trăm.'}],
        'fees': [{'title': 'Học phí minh họa', 'description': 'Chưa có khoản phải thu hay yêu cầu thanh toán thật.'}],
        'orders': [{'id': 'DEMO-001', 'title': 'Gói VIP mẫu', 'status': 'Minh họa, không thanh toán'}]}


def snapshot(db, b, s, at):
    state = json.loads(s['state_json']);grade=state.get('grade',5);content=load_content(grade)
    activities = {m: None for m in MODES}
    for row in db.execute('SELECT payload_json FROM trial_attempts WHERE session_id=? ORDER BY created_at,id', (s['id'],)):
        attempt = json.loads(row[0])
        if attempt.get('grade',5)!=grade:continue
        activities[attempt['mode']] = attempt_view(db, attempt, at)
    return {'demo': True, 'grade':grade,'gradeRevision':state.get('gradeRevision',0),'csrf': b['csrf'], 'serverTime': at,
        'session': {'id': s['id'], 'generation': s['generation'], 'createdAt': s['created_at'],
            'lastActivityAt': s['last_activity_at'], 'idleWarnAt': s['last_activity_at'] + IDLE - WARN,
            'idleExpiresAt': s['last_activity_at'] + IDLE, 'absoluteExpiresAt': s['absolute_expires_at'],
            'warning': at >= s['last_activity_at'] + IDLE - WARN},
        'lesson': content['lesson'], 'lessonComplete': state['lessonComplete'],
        'activities': activities, 'fixtures': fixture(), 'preferences': state['preferences']}


def claimed_history(db, student_id):
    """Caller must first enforce family/child ACL. No official exam merge."""
    return [{'id': r['id'], 'claimedAt': r['claimed_at'], 'kind': 'trial-history', 'officialGrade': False,
             'snapshot': json.loads(r['snapshot_json'])} for r in db.execute(
        'SELECT * FROM trial_claimed_history WHERE student_id=? ORDER BY id DESC', (student_id,))]


def create_attempt(db, b, s, mode, at):
    grade=json.loads(s['state_json']).get('grade',5)
    prior = db.execute('SELECT payload_json FROM trial_attempts WHERE session_id=? AND mode=? '
                      'AND COALESCE(json_extract(payload_json,\'$.grade\'),5)=? '
                      'ORDER BY created_at DESC,id DESC LIMIT 1', (s['id'], mode,grade)).fetchone()
    if prior:
        existing = json.loads(prior[0])
        if existing.get('grade',5)==grade and existing['status'] not in ('finished', 'completed', 'cancelled'):
            return
    content = load_content(grade)
    questions = eligible(content, mode)
    minimum = 20 if mode == 'bot' else 5
    if len(questions) < minimum:
        fail('Chưa đủ câu mẫu đúng mục đích. Chế độ này chưa mở.', 503)
    count = 5 if mode == 'practice' else 20 if mode == 'bot' else len(questions)
    if content.get('curriculumSamples'):
        count=5 if mode=='practice' else 20
        secrets.SystemRandom().shuffle(questions)
    questions = questions[:count]
    c = counter(db, b['id'], at)
    if c['issued_count'] + len(questions) > 400:
        fail('Đã dùng đủ lượng nội dung mẫu hôm nay. Hãy quay lại sau.', 429)
    aid = secrets.token_hex(16)
    attempt = {'id': aid, 'mode': mode, 'grade':grade,'status': 'playing', 'index': 0, 'questions': questions,
               'draft': {}, 'results': [], 'room': None}
    preferences = json.loads(s['state_json'])['preferences']
    if mode == 'bot':
        attempt['room'] = new_duel(questions, aid, at, preferences['mascot'])
    elif mode in ('capture_flag', 'animal_race'):
        attempt['room'] = new_group(questions, mode, aid, at, preferences['mascot'], content['revision'])
    db.execute('INSERT INTO trial_attempts VALUES (?,?,?,?,?)', (aid, s['id'], mode, at, api.packed(attempt)))
    db.execute('UPDATE trial_counters SET issued_count=issued_count+? WHERE browser_id=?', (len(questions), b['id']))


def answer(db, s, body, at, mode):
    row = db.execute('SELECT payload_json FROM trial_attempts WHERE id=? AND session_id=? AND mode=?',
                     (body.get('attemptId'), s['id'], mode)).fetchone()
    if not row:
        fail('Bài mẫu không thuộc phiên này.', 404)
    attempt = json.loads(row[0])
    if attempt.get('grade',5)!=json.loads(s['state_json']).get('grade',5):fail('Lớp trải nghiệm vừa thay đổi. Hãy mở lại bài đúng lớp.',409)
    value, qid = body.get('answer'), body.get('questionId')
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        fail('Nhập một đáp số hợp lệ, tối đa 500 ký tự.')
    for result in attempt['results']:
        if result['questionId'] == qid:
            if result['answer'] != value:
                fail('Câu này đã nộp một lần.', 409)
            return
    # Tick before validating current question so stale requests cannot answer next.
    attempt_view(db, attempt, at)
    q = attempt['questions'][attempt['index']] if attempt['index'] < len(attempt['questions']) else None
    if not q or q['id'] != qid or attempt['status'] != 'playing':
        fail('Câu hỏi đã đóng hoặc đã chuyển.', 409)
    if q.get('responseMode')=='choice' and value not in q.get('options',[]):fail('Chọn một trong bốn phương án của câu hỏi.')
    if mode == 'bot':
        room = attempt['room']
        player = room['players'][room['trialMe']]
        if room['resolved'] or player['answer'] is not None:
            fail('Câu này đã nộp hoặc đã đóng.', 409)
        Arena()._answer(room, player, {'answer': value}, at / 1000)
    elif mode in ('capture_flag', 'animal_race'):
        room = attempt['room']
        TrialGroup(room, at).mutate(None, {'student_id': 1}, room['id'], {
            'requestKey': secrets.token_hex(12), 'round': room['round'], 'answer': value}, 'answer')
    correct = matches(value, engine_question(q))
    attempt['results'].append({'questionId': qid, 'answer': value, 'correct': correct,
                              'expected': q['answer'], 'explanation': q['explanation']})
    attempt['draft'].pop(qid, None)
    if mode == 'practice':
        attempt['index'] += 1
        if attempt['index'] == len(attempt['questions']):
            attempt['status'] = 'completed'
    save_attempt(db, attempt)


def route(handler, method, path, body=None, database_path=None):
    if not path.startswith(BASE):
        fail('Không tìm thấy.', 404)
    handler.api_headers = getattr(handler, 'api_headers', {})
    handler.api_headers['Cache-Control'] = 'no-store'
    if method == 'GET' and path == BASE + 'config':
        return config(), 200
    if method not in ('GET', 'POST'):
        fail('Phương thức không hỗ trợ.', 405)
    if path[len(BASE):].split('/', 1)[0] in ('keep', 'claim', 'history', 'trial-history'):
        fail('Tính năng lưu và nhận lịch sử trải nghiệm đã dừng.', 410)
    if method == 'POST' and not api.same_origin(handler):
        fail('Yêu cầu phải xuất phát từ website đang mở.', 403)
    body = {} if body is None else body
    if not isinstance(body, dict):
        fail('Dữ liệu không hợp lệ.')
    at = clock()
    error = None
    with api.connect(database_path or handler.server.database_path, True) as db:
        if hasattr(db,'atomic'):
            return _route_db(handler,method,path,body,db,at)
        db.execute('SAVEPOINT trial_request')
        try:
            result = _route_db(handler, method, path, body, db, at)
        except (api.APIError, ArenaError, ValueError, TypeError) as caught:
            db.execute('ROLLBACK TO trial_request')
            error = caught
    if error is not None:
        raise error
    return result


def _route_db(handler, method, path, body, db, at):
    cleanup(db, at)
    b = browser(db, handler, at, create=method == 'POST' and path == BASE + 'session')
    if not b:
        fail('Hãy bắt đầu trải nghiệm.', 401)
    creating = method == 'POST' and path == BASE + 'reset'
    if method == 'POST' and path == BASE + 'session':
        active = db.execute('SELECT 1 FROM trial_sessions WHERE id=? AND revoked_at IS NULL '
            'AND absolute_expires_at>? AND last_activity_at>?',
            (b['current_session'], at, at - IDLE)).fetchone()
        creating = not bool(active)
    limited = limit(db, handler, b, at, creating, body)
    if limited:
        return limited
    # Native DO storage uses a nested synchronous transaction. Return expected
    # rejection as a response after rollback so outer resource counters commit.
    if callable(getattr(db,'atomic',None)):
        try:return db.atomic(lambda:_mutate_trial(handler,method,path,body,db,at,b))
        except (api.APIError,ArenaError) as error:return {'error':str(error)},error.status
        except (ValueError,TypeError):return {'error':'Dữ liệu trải nghiệm không hợp lệ.'},400
    db.execute('SAVEPOINT trial_request')
    return _mutate_trial(handler,method,path,body,db,at,b)


def _mutate_trial(handler,method,path,body,db,at,b):
    if method == 'POST' and path == BASE + 'session':
        # Resume does not consume creation quota or extend meaningful activity.
        try:
            existing = session(db, b, at)
        except api.APIError as error:
            if error.status not in (401, 410):
                raise
        else:
            if not hmac.compare_digest(handler.headers.get('X-Trial-CSRF', ''), b['csrf']):
                fail('Phiên đang mở. Hãy tải lại trạng thái.', 403)
            return snapshot(db, b, existing, at), 200
        s = new_session(db, b, at)
        event(db, at, 'create')
        return snapshot(db, b, s, at), 200
    if method == 'POST' and not hmac.compare_digest(handler.headers.get('X-Trial-CSRF', ''), b['csrf']):
        fail('Phiên cần tải lại mã bảo vệ.', 403)
    s = session(db, b, at, body if method == 'POST' else None)
    if method == 'GET' and path == BASE + 'state':
        return snapshot(db, b, s, at), 200
    if method != 'POST':
        fail('Không tìm thấy.', 404)
    if path in (BASE + 'reset', BASE + 'end'):
        cancel_pending(db, b, at)
        db.execute('UPDATE trial_sessions SET revoked_at=?,state_json=? WHERE id=?', (at, '{}', s['id']))
        db.execute('DELETE FROM trial_attempts WHERE session_id=?', (s['id'],))
        event(db, at, 'reset' if path.endswith('/reset') else 'end')
        if path.endswith('/end'):
            return {'ended': True, 'demo': True}, 200
        browser(db, handler, at, create=True)
        fresh = new_session(db, b, at, s['generation'] + 1)
        return snapshot(db, b, fresh, at), 200
    elif path == BASE + 'activity':
        pass
    elif path == BASE + 'grade':
        grade=body.get('grade')
        if type(grade) is not int or grade not in range(1,6) or not any(x['grade']==grade and x['ready'] for x in config()['grades']):fail('Khối này chưa có bộ mẫu phù hợp.')
        state=json.loads(s['state_json'])
        completed=state.setdefault('lessonCompleteByGrade',{})
        completed[str(state.get('grade',5))]=state.get('lessonComplete',False)
        state['grade']=grade;state['gradeRevision']=state.get('gradeRevision',0)+1
        state['lessonComplete']=completed.get(str(grade),False)
        db.execute('UPDATE trial_sessions SET state_json=? WHERE id=?',(api.packed(state),s['id']))
    elif path == BASE + 'lesson/complete':
        state = json.loads(s['state_json'])
        state['lessonComplete'] = True
        state.setdefault('lessonCompleteByGrade',{})[str(state.get('grade',5))]=True
        db.execute('UPDATE trial_sessions SET state_json=? WHERE id=?', (api.packed(state), s['id']))
    elif path in (BASE + 'practice/start', BASE + 'bot/start', BASE + 'game/start'):
        mode = body.get('mode') if path.endswith('game/start') else path.split('/')[-2]
        if mode not in MODES or path.endswith('game/start') and mode not in MODES[2:]:
            fail('Chế độ mẫu không hợp lệ.')
        create_attempt(db, b, s, mode, at)
    elif path in (BASE + 'practice/answer', BASE + 'bot/answer', BASE + 'game/answer'):
        mode = path.split('/')[-2]
        if mode == 'game':
            row = db.execute('SELECT mode FROM trial_attempts WHERE id=? AND session_id=?',
                             (body.get('attemptId'), s['id'])).fetchone()
            mode = row[0] if row and row[0] in MODES[2:] else ''
        answer(db, s, body, at, mode)
    elif path == BASE + 'draft':
        row = db.execute('SELECT payload_json FROM trial_attempts WHERE id=? AND session_id=?',
                         (body.get('attemptId'), s['id'])).fetchone()
        if not row:
            fail('Bài mẫu không thuộc phiên này.', 404)
        attempt = json.loads(row[0])
        if attempt.get('grade',5)!=json.loads(s['state_json']).get('grade',5):fail('Lớp trải nghiệm vừa thay đổi. Hãy mở lại bài đúng lớp.',409)
        values = body.get('answers')
        permitted = {q['id'] for q in attempt['questions']}
        if (not isinstance(values, dict) or len(values) > 50 or any(
                k not in permitted or not isinstance(v, str) or len(v) > 500 for k, v in values.items())):
            fail('Nháp không hợp lệ.')
        attempt['draft'] = values
        scratch = body.get('scratch', attempt.get('scratch', ''))
        if not isinstance(scratch, str) or len(scratch) > 10000:
            fail('Nháp quá dài.')
        attempt['scratch'] = scratch
        save_attempt(db, attempt)
    elif path == BASE + 'preferences':
        if body.get('theme') not in THEMES or body.get('mascot') not in MASCOTS:
            fail('Giao diện hoặc linh vật không hợp lệ.')
        state = json.loads(s['state_json'])
        state['preferences'] = {k: body[k] for k in ('theme', 'mascot')}
        db.execute('UPDATE trial_sessions SET state_json=? WHERE id=?', (api.packed(state), s['id']))
    elif path == BASE + 'order/preview':
        if body.get('plan') not in ('vip', 'vip_plus') or body.get('period') not in ('month', 'year'):
            fail('Gói mẫu không hợp lệ.')
        return {'demo': True, 'previewOnly': True, 'plan': body['plan'], 'period': body['period'],
                'label': 'Đơn minh họa — không tạo giao dịch, QR hoặc quyền sử dụng thật',
                'paymentEnabled': False}, 200
    else:
        fail('Không tìm thấy thao tác trải nghiệm.', 404)
    db.execute('UPDATE trial_sessions SET last_activity_at=? WHERE id=?', (at, s['id']))
    s = db.execute('SELECT * FROM trial_sessions WHERE id=?', (s['id'],)).fetchone()
    return snapshot(db, b, s, at), 200


def dispatch(handler, database_path=None):
    """HTTP adapter requested by integration contract; no shared route mutation."""
    path = urlsplit(handler.path).path
    if not path.startswith(BASE):
        return False
    handler.api_headers = {}
    try:
        body = None
        method = handler.command
        if method == 'POST':
            if handler.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                fail('Use application/json', 415)
            lengths = handler.headers.get_all('Content-Length', []) if hasattr(handler.headers, 'get_all') else [handler.headers.get('Content-Length', '')]
            if (handler.headers.get('Transfer-Encoding') or len(lengths) != 1
                    or not re.fullmatch(r'[0-9]+', lengths[0])):
                fail('Invalid content length')
            length = int(lengths[0])
            if not 0 < length <= 32768:
                fail('Dữ liệu trải nghiệm quá lớn.', 413)
            raw = handler.rfile.read(length)
            if len(raw) != length:
                fail('Dữ liệu chưa đầy đủ.')
            body = json.loads(raw.decode('utf-8'))
        payload, status = route(handler, method, path, body, database_path)
    except (api.APIError, ArenaError) as error:
        payload, status = {'error': str(error)}, error.status
    except sqlite3.Error:
        payload, status = {'error': 'Kho trải nghiệm tạm bận. Em hãy thử lại sau.'}, 503
    except (ValueError, TypeError, UnicodeError, RecursionError):
        payload, status = {'error': 'Dữ liệu trải nghiệm không hợp lệ.'}, 400
    handler.json_response(status, payload)
    return True
