"""Durable, server-authoritative five-player games, separately gated question source.

All mutations, timer advances and XP settlement occur in one SQLite writer
transaction. No client clock, result, rank, identity or reward is trusted.
"""
import hashlib
import hmac
import json
import re
import secrets
import time
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

from . import platform_api as api
from .answers import matches, validate_rule, validate_choices, requires_choice, MAX_ANSWER
from .nickname_policy import safe_nickname

BASE = '/api/v1/group-games'
MODES = {'capture_flag': 'Cướp Cờ', 'animal_race': 'Đua Thú'}
ACTIVE = ('waiting', 'playing', 'intermission')
ROUND_MS = 60_000
BREAK_MS = 3_000
TARGET = 5
PLAYERS = 5


def fail(message, status=400):
    raise api.APIError(message, status)


def request_key(body):
    value = body.get('requestKey')
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,100}', value):
        fail('Mã yêu cầu không hợp lệ.')
    return value


class QuestionSource:
    """Explicit separate bank. Never discovers old, paid, fixed or demo sources."""
    def __init__(self, questions=(), *, approved=False, qa_only=False, revision='unconfigured'):
        self.approved = approved
        self.qa_only = qa_only
        self.revision = revision
        self.questions = []
        seen = set()
        for raw in questions:
            q = deepcopy(raw)
            if q.get('purpose') != 'group-games' or type(q.get('grade')) is not int or q.get('grade') not in range(1, 6):
                raise ValueError('Separate group-games purpose and grade required')
            if not isinstance(q.get('id'), str) or not q['id'] or type(q.get('revision')) is not int or q['revision'] < 1:
                raise ValueError('Pinned source identity/revision required')
            identity = (q['id'], q['revision'])
            if identity in seen:
                raise ValueError('Duplicate source question identity')
            if not isinstance(q.get('text'), str) or not q['text'] or len(q['text']) > 10000:
                raise ValueError('Question text required')
            modes = q.get('modes', list(MODES))
            if not isinstance(modes, list) or not modes or any(not isinstance(mode,str) or mode not in MODES for mode in modes) or len(modes)!=len(set(modes)):
                raise ValueError('Invalid source modes')
            if q.get('responseMode') == 'choice':
                options = q.get('options')
                if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4 or any(not isinstance(x, str) or not x.strip() for x in options) or q.get('answer') not in options:
                    raise ValueError('Four distinct complete choices required')
                # Production source review must verify distractor rationale.
                if not qa_only:
                    validate_choices(q['answer'], options, q.get('choiceRationales'), q.get('answerTargets'))
            elif q.get('responseMode') == 'typed' and not requires_choice(q):
                validate_rule(q.get('answer'), q.get('answerKind', 'number'))
            else:
                raise ValueError('Single result typed, multiple results complete choice')
            q['modes'] = q.get('modes', list(MODES))
            self.questions.append(q)
            seen.add(identity)

    def select(self, grade, mode):
        result = [deepcopy(q) for q in self.questions if q['grade'] == grade and mode in q['modes']]
        if len(result) < TARGET:
            fail('Chưa đủ nguồn câu riêng đã được duyệt cho game này.', 503)
        secrets.SystemRandom().shuffle(result)
        return result


class GroupGames:
    def __init__(self, source=None, *, policy_approved=False, qa_only=False, clock=None):
        self.source = source or QuestionSource()
        self.policy_approved = policy_approved
        self.qa_only = qa_only
        self.clock = clock or (lambda: int(time.time() * 1000))

    def enabled(self):
        return bool(self.policy_approved and (self.source.approved or self.qa_only and self.source.qa_only))

    def catalogue(self, grade):
        source_ready = self.source.approved or self.qa_only and self.source.qa_only
        modes = []
        for key, title in MODES.items():
            enough = sum(q['grade'] == grade and key in q['modes'] for q in self.source.questions) >= TARGET
            modes.append({'key': key, 'title': title, 'mapCount': 10, 'ready': self.enabled() and enough})
        ready = self.enabled() and any(m['ready'] for m in modes)
        return {'enabled': self.enabled(), 'ready': ready,
                'reason': '' if ready else 'Game đang chờ nguồn câu hỏi và chính sách lượt chơi được duyệt.',
                'modes': modes, 'rules': {'players': PLAYERS, 'target': TARGET, 'roundSeconds': 60, 'intermissionSeconds': 3},
                'policyStatus': 'qa-only' if self.qa_only else 'approved' if self.policy_approved else 'pending',
                'sourceStatus': 'qa-only' if self.source.qa_only else 'approved' if source_ready else 'pending'}

    @staticmethod
    def _save(db, room, now):
        db.execute('UPDATE group_game_rooms SET status=?,payload_json=?,updated_at=? WHERE id=?',
                   (room['status'], api.packed(room), now, room['id']))

    @staticmethod
    def _load(db, rid):
        row = db.execute('SELECT payload_json FROM group_game_rooms WHERE id=?', (rid,)).fetchone()
        if not row:
            fail('Phòng không tồn tại.', 404)
        return json.loads(row['payload_json'])

    @staticmethod
    def _member(room, sid):
        player = next((p for p in room['players'] if p['studentId'] == sid), None)
        if player is None:
            fail('Em không thuộc phòng này.', 403)
        return player

    @staticmethod
    def _signature(action, body):
        filtered = {k: v for k, v in body.items() if k in ('mode', 'code', 'round', 'answer')}
        canonical = json.dumps([action, filtered], ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _replay(self, db, sid, key, signature):
        row = db.execute('SELECT * FROM group_game_requests WHERE student_id=? AND request_key=?', (sid, key)).fetchone()
        if row:
            if row['signature'] != signature:
                fail('Mã yêu cầu đã được dùng cho lựa chọn khác.', 409)
            return self._load(db, row['room_id'])

    @staticmethod
    def _remember(db, sid, key, signature, rid):
        db.execute('INSERT INTO group_game_requests VALUES (?,?,?,?)', (sid, key, signature, rid))

    def _start_round(self, room, start):
        room['status'] = 'playing'
        room['round'] += 1
        room['startedAt'] = start
        room['deadline'] = start + ROUND_MS
        room['nextAt'] = None
        for player in room['players']:
            player['answered'] = False
            player['answerCorrect'] = None

    @staticmethod
    def _account_time(room, end):
        for p in room['players']:
            if not p['answered']:
                p['totalTimeMs'] += min(ROUND_MS, max(0, end - room['startedAt']))
                p['answered'] = True
                p['answerCorrect'] = False

    def _finish(self, db, room, now, reason, winner=None):
        if room['status'] == 'playing':
            self._account_time(room, now)
        room.update(status='finished', endReason=reason, winnerId=winner, finishedAt=now, nextAt=None)
        ranked = sorted(room['players'], key=lambda p: (p['studentId'] != winner if winner is not None else False,
                         p['forfeited'], -p['correct'], p['totalTimeMs'], p['lastStepAt'], p['seat']))
        room['rankings'] = []
        for rank, p in enumerate(ranked, 1):
            points = 6-rank if winner is not None and reason == 'target_reached' and not p['forfeited'] else 0
            room['rankings'].append({'studentId': p['studentId'], 'rank': rank, 'points': points,
                                    'correct': p['correct'], 'totalTimeMs': p['totalTimeMs']})
        # Persist result and rewards in this same DB transaction. Duplicate
        # polls/retries/restarts find either both or neither, never half an award.
        self._save(db, room, now)
        for result in room['rankings']:
            if not result['points']:
                continue
            inserted = db.execute('INSERT OR IGNORE INTO group_game_rewards VALUES (?,?,?,?,?,?)',
                (room['id'], result['studentId'], room['mode'], result['rank'], result['points'], now)).rowcount
            if inserted:
                db.execute('UPDATE student_companions SET xp=MIN(1000000000,xp+?) WHERE student_id=?',
                           (result['points'], result['studentId']))

    def _tick(self, db, room, now):
        if room['status'] == 'waiting' and now - room['createdAt'] >= 300_000:
            room.update(status='cancelled', endReason='waiting_expired', winnerId=None)
        # Advance from server boundaries, never from a poll-dependent new clock.
        while True:
            if room['status'] == 'playing' and now >= room['deadline']:
                self._account_time(room, room['deadline'])
                room.update(status='intermission', nextAt=room['deadline'] + BREAK_MS)
            elif room['status'] == 'intermission' and now >= room['nextAt']:
                if room['round'] >= len(room['questions']):
                    self._finish(db, room, room['nextAt'], 'source_exhausted')
                    break
                self._start_round(room, room['nextAt'])
            else:
                break
        self._save(db, room, now)

    def _active(self, db, sid, now):
        for row in db.execute("SELECT payload_json FROM group_game_rooms WHERE status IN ('waiting','playing','intermission')").fetchall():
            room = json.loads(row[0])
            self._tick(db, room, now)
            if room['status'] in ACTIVE and any(p['studentId'] == sid and not p['forfeited'] for p in room['players']):
                return room

    def enter(self, db, session, body, action, grade):
        if not self.enabled():
            fail('Game chưa mở: cần duyệt nguồn câu hỏi và chính sách lượt chơi.', 503)
        now, sid = self.clock(), session['student_id']
        key = request_key(body)
        signature = self._signature(action, body)
        repeated = self._replay(db, sid, key, signature)
        if repeated:
            self._member(repeated, sid)
            self._tick(db, repeated, now)
            return self.view(repeated, sid, now)
        if self._active(db, sid, now):
            fail('Em đang có phòng chơi. Hãy quay lại hoặc rời phòng trước.', 409)
        if action == 'create':
            mode = body.get('mode')
            if mode not in MODES:
                fail('Game không hợp lệ.')
            questions = self.source.select(grade, mode)
            rid, code = secrets.token_hex(16), secrets.token_hex(4).upper()
            room = {'id': rid, 'code': code, 'mode': mode, 'grade': grade, 'createdAt': now,
                    'status': 'waiting', 'mapIndex': secrets.randbelow(10), 'round': 0, 'target': TARGET,
                    'players': [], 'questions': questions, 'deadline': None, 'nextAt': None,
                    'rankings': [], 'winnerId': None, 'endReason': None, 'sourceRevision': self.source.revision}
            db.execute('INSERT INTO group_game_rooms VALUES (?,?,?,?,?,?,?)',
                       (rid, code, mode, grade, 'waiting', api.packed(room), now))
        else:
            code = body.get('code')
            if not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9]{8}', code):
                fail('Mã phòng không hợp lệ.')
            row = db.execute('SELECT id FROM group_game_rooms WHERE code=?', (code.upper(),)).fetchone()
            if not row:
                fail('Phòng không tồn tại.', 404)
            room = self._load(db, row['id'])
            self._tick(db, room, now)
            if room['status'] != 'waiting' or len(room['players']) >= PLAYERS:
                fail('Phòng đã bắt đầu hoặc đã đủ người.', 409)
            if grade != room['grade']:
                fail('Người chơi cần cùng khối lớp.', 403)
        pet = db.execute('SELECT m.name,c.xp FROM student_companions c JOIN mascots m ON m.id=c.mascot_id WHERE c.student_id=?', (sid,)).fetchone()
        if not pet:
            fail('Hồ sơ linh vật chưa sẵn sàng.', 409)
        room['players'].append({'studentId': sid, 'name': safe_nickname(session['full_name']),
            'mascot': api.mascot_code(pet['name']), 'xp': pet['xp'], 'seat': len(room['players']),
            'steps': 0, 'correct': 0, 'totalTimeMs': 0, 'lastStepAt': now,
            'answered': False, 'answerCorrect': None, 'forfeited': False})
        if len(room['players']) == PLAYERS:
            self._start_round(room, now)
        self._save(db, room, now)
        self._remember(db, sid, key, signature, room['id'])
        return self.view(room, sid, now)

    def mutate(self, db, session, rid, body, action):
        now, sid = self.clock(), session['student_id']
        key = request_key(body)
        signature = self._signature(action + ':' + rid, body)
        room = self._load(db, rid)
        repeated = self._replay(db, sid, key, signature)
        # A successful waiting-room leave removed membership. Its durable,
        # student-bound request row remains the proof for idempotent retry.
        if repeated and action == 'leave':
            self._tick(db, room, now)
            return self.view(room, sid, now)
        player = self._member(room, sid)
        self._tick(db, room, now)
        if repeated:
            return self.view(room, sid, now)
        if action == 'leave':
            if room['status'] == 'waiting':
                room['players'] = [p for p in room['players'] if p['studentId'] != sid]
                for seat, p in enumerate(room['players']):
                    p['seat'] = seat
                if not room['players']:
                    room.update(status='cancelled', endReason='cancelled')
            elif room['status'] in ('playing', 'intermission'):
                player['forfeited'] = True
                if all(p['forfeited'] for p in room['players']):
                    self._finish(db, room, now, 'cancelled')
            self._save(db, room, now)
        else:
            if room['status'] != 'playing' or type(body.get('round')) is not int or body['round'] != room['round']:
                fail('Câu hỏi đã đóng hoặc chưa bắt đầu.', 409)
            if player['forfeited'] or player['answered']:
                fail('Em đã trả lời hoặc đã rời trận này.', 409)
            answer = body.get('answer')
            if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER:
                fail('Nhập đáp án hợp lệ.')
            question = room['questions'][room['round'] - 1]
            correct = answer == question['answer'] if question['responseMode'] == 'choice' else matches(answer, question)
            player['answered'] = True
            player['answerCorrect'] = correct
            player['totalTimeMs'] += max(0, min(ROUND_MS, now - room['startedAt']))
            if correct:
                player['correct'] += 1
                player['steps'] = player['correct']
                player['lastStepAt'] = now
            if player['steps'] == TARGET:
                self._finish(db, room, now, 'target_reached', sid)
            elif all(p['answered'] or p['forfeited'] for p in room['players']):
                self._account_time(room, now)
                room.update(status='intermission', nextAt=now + BREAK_MS)
            self._save(db, room, now)
        self._remember(db, sid, key, signature, rid)
        return self.view(room, sid, now)

    @staticmethod
    def view(room, sid, now):
        public = {k: deepcopy(room.get(k)) for k in ('id', 'code', 'mode', 'grade', 'status', 'createdAt', 'mapIndex', 'round', 'deadline', 'nextAt', 'target', 'winnerId', 'endReason', 'rankings')}
        public['serverTime'] = now
        public['meStudentId'] = sid
        # Project rank without changing seat order, engine state or rewards.
        # Match the existing final comparator; a finished winner retains its
        # persisted winner-priority position.
        ordered=sorted(room['players'],key=lambda p:(p['forfeited'],-p['correct'],p['totalTimeMs'],p['lastStepAt'],p['seat']))
        live_ranks={p['studentId']:rank for rank,p in enumerate(ordered,1)}
        if room['status'] in ('finished','cancelled') and room['rankings']:
            live_ranks.update({p['studentId']:p['rank'] for p in room['rankings']})
        public['players'] = []
        for p in room['players']:
            value = {k: p[k] for k in ('studentId', 'name', 'mascot', 'xp', 'seat', 'steps', 'correct', 'totalTimeMs', 'answered', 'forfeited')}
            if p['studentId'] == sid:
                value['answerCorrect'] = p['answerCorrect']
            value['mine'] = p['studentId'] == sid
            value['liveRank'] = live_ranks[p['studentId']]
            value['mascotXp'] = min(1000000000,p['xp'] + next((r['points'] for r in room['rankings'] if r['studentId'] == p['studentId']), 0))
            public['players'].append(value)
        for row in public['rankings']:
            row['mine'] = row['studentId'] == sid
            row['xpAward'] = row['points']
            member = next(p for p in public['players'] if p['studentId']==row['studentId'])
            row.update({k:member[k] for k in ('name','mascot','mascotXp','xp','forfeited')})
        public['question'] = None
        if room['status'] == 'playing':
            q = room['questions'][room['round']-1]
            public['question'] = {k: deepcopy(q[k]) for k in ('id', 'revision', 'text', 'responseMode', 'options', 'inputGuide') if k in q}
        return public


def leaderboard(db, query):
    kind = query.get('kind', ['mascot'])[0]
    if kind not in ('mascot', 'duel', *MODES):
        fail('Loại bảng xếp hạng không hợp lệ.')
    try:
        offset = int(query.get('offset', ['0'])[0])
        limit = int(query.get('limit', ['20'])[0])
        if offset < 0 or not 1 <= limit <= 50:
            raise ValueError()
    except (ValueError, TypeError):
        fail('Phân trang không hợp lệ.')
    if kind == 'mascot':
        metric, params = 'SELECT student_id,xp points FROM student_companions', ()
    elif kind == 'duel':
        metric, params = 'SELECT student_id,SUM(delta) points FROM xp_events WHERE duel_player_id IS NOT NULL GROUP BY student_id', ()
    else:
        metric, params = 'SELECT student_id,SUM(points) points FROM group_game_rewards WHERE mode=? GROUP BY student_id', (kind,)
    rows = db.execute('WITH metric AS (' + metric + ') SELECT s.id,s.full_name,m.name mascot,c.xp,metric.points '
        'FROM metric JOIN students s ON s.id=metric.student_id '
        'JOIN student_companions c ON c.student_id=s.id JOIN mascots m ON m.id=c.mascot_id '
        'ORDER BY metric.points DESC,s.id ASC', params).fetchall()
    results = [{'rank': n, 'studentId': row['id'], 'name': safe_nickname(row['full_name']),
                'mascot': api.mascot_code(row['mascot']), 'xp': row['xp'], 'points': row['points']} for n, row in enumerate(rows, 1)]
    return {'kind': kind, 'top3': results[:3], 'items': results[3+offset:3+offset+limit],
            'offset': offset, 'limit': limit, 'total': len(results), 'hasMore': 3+offset+limit < len(results),
            'metricNotice': 'Đấu trí chỉ tính các sự kiện điểm có duel_player_id; không suy từ tổng XP linh vật.' if kind == 'duel' else ''}


def dispatch(handler, method, path, body):
    from . import game_claims as claims
    # Even state GET advances authoritative timers and may settle a match.
    with api.connect(handler.server.database_path, True) as db:
        session = api.read_session(handler, db)
        if not session:
            fail('Em hãy đăng nhập để tiếp tục.', 401)
        if method == 'POST' and (not api.same_origin(handler) or not hmac.compare_digest(handler.headers.get('X-CSRF-Token', ''), session['csrf_token'])):
            fail('Phiên đăng nhập cần được tải lại.', 403)
        from .system_settings import require_feature
        require_feature(db, 'leaderboard_open' if path == BASE + '/leaderboard' else 'arena_open')
        service = getattr(handler.server, 'group_games', None) or GroupGames()
        grade = api.academic()[0] - session['birth_year'] - 5
        grade = max(1, min(5, grade))
        query = parse_qs(urlsplit(handler.path).query)
        local_runtime=getattr(handler.server,'local_test_games',None)
        if local_runtime is not None and path!=BASE+'/leaderboard':
            if local_runtime.allowed(handler):
                service=local_runtime.group_games
            elif method=='GET' and path==BASE+'/catalogue':
                return {**GroupGames().catalogue(grade),'localTest':True,'sourceStatus':'localhost-required',
                        'reason':'Chế độ thử cục bộ chỉ mở nguồn game qua địa chỉ localhost đã cấu hình.',
                        'policyStatus':'pending-commercial'},200
            else:
                fail('Nguồn game thử cục bộ chỉ mở qua địa chỉ localhost đã cấu hình.',403)
        if method == 'GET' and path == BASE + '/catalogue':
            return service.catalogue(grade), 200
        if method == 'GET' and path == BASE + '/leaderboard':
            return leaderboard(db, query), 200
        if method == 'GET' and path == BASE + '/rooms':
            mode = query.get('mode', ['capture_flag'])[0]
            if mode not in MODES:
                fail('Game không hợp lệ.')
            rooms = []
            for row in db.execute("SELECT payload_json FROM group_game_rooms WHERE mode=? AND grade=? AND status='waiting'", (mode, grade)).fetchall():
                room = json.loads(row[0]); service._tick(db, room, service.clock())
                if (room['status'] == 'waiting' and room.get('public',True) and room.get('playMode','human')=='human'
                        and room.get('sourcePool',claims.pool(handler,db))==claims.pool(handler,db) and room['sourceRevision']==service.source.revision
                        and not any(p['studentId'] == session['student_id'] and not p.get('forfeited',False) for p in room['players'])):
                    rooms.append({k: room[k] for k in ('id', 'code', 'mode', 'status', 'grade')} | {'playerCount': len(room['players'])})
            return {'rooms': rooms}, 200
        if method == 'POST' and path in (BASE + '/rooms', BASE + '/join',BASE+'/quick'):
            return claims.group_admission(handler,db,session,service,body,'quick' if path.endswith('/quick') else 'create' if path.endswith('/rooms') else 'join',grade),200
        match = re.fullmatch(re.escape(BASE) + r'/rooms/([a-f0-9]{32})(?:/(answer|leave))?', path)
        if match:
            rid, action = match.groups()
            if method == 'GET' and not action:
                room = service._load(db, rid); service._member(room, session['student_id'])
                if room['status'] in ACTIVE and room.get('sourcePool',claims.pool(handler,db))!=claims.pool(handler,db):fail('Nguồn câu của phòng không mở ở địa chỉ truy cập này.',403)
                service._tick(db, room, service.clock())
                claims.sync_group(db,room)
                return {'room': service.view(room, session['student_id'], service.clock()),'gameClaim':claims.public(handler,db,claims._row(db,session['student_id']))}, 200
            if method == 'POST' and action:
                room=service._load(db,rid);service._member(room,session['student_id'])
                if room['status'] in ACTIVE and room.get('sourcePool',claims.pool(handler,db))!=claims.pool(handler,db):fail('Nguồn câu của phòng không mở ở địa chỉ truy cập này.',403)
                claims.guard_generation(handler,db,session,body,rid)
                view=service.mutate(db,session,rid,body,action);room=service._load(db,rid);claims.sync_group(db,room)
                return {'room':view,'gameClaim':claims.public(handler,db,claims._row(db,session['student_id']))},200
        fail('Đường dẫn game không tồn tại.', 404)
