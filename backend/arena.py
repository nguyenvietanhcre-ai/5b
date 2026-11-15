"""In-memory two-player rooms for the local learning preview."""
import random
import secrets
import string
import threading
import time
from copy import deepcopy

from .nickname_policy import safe_nickname, validate_nickname
from .answers import matches, MAX_ANSWER, question_correct


class ArenaError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def question_seconds(grade, difficulty):
    """Every Duel question is exactly 60 seconds, including client BOT demo."""
    return 60


class Arena:
    def __init__(self):
        self.rooms = {}
        self.retired = {}
        self.lock = threading.RLock()
        self.random = random.SystemRandom()

    def handle(self, payload, question_provider=None):
        with self.lock:
            now = time.time()
            action = payload.get("action")
            code, token = payload.get("code"), payload.get("token")
            requested_room = self.rooms.get(code) if isinstance(code, str) else None
            if (requested_room and isinstance(token,str) and token in requested_room['players']
                    and action!='leave' and requested_room.get('sourcePool','legacy')!=payload.get('sourcePool','legacy')):
                raise ArenaError('Nguồn câu của phòng không mở ở địa chỉ truy cập này.',403)
            # A resumed browser is present now. Renew it before checking idle
            # players so its first request cannot disconnect itself.
            if requested_room and isinstance(token, str) and token in requested_room["players"]:
                requested_room["players"][token]["seen"] = now
            self._cleanup(now)
            if action=='list':
                return {'rooms':[{'code':r['code'],'name':safe_nickname(next(iter(r['players'].values()))['name']),
                    'grade':r['grade'],'scope':r['scope'],**next(iter(r['players'].values()))['stats']}
                    for r in self.rooms.values() if r['public'] and r['status']=='waiting' and r['grade']==payload.get('grade')
                    and r.get('sourcePool','legacy')==payload.get('sourcePool','legacy')
                    and not any(p.get('accountId') == payload.get('accountId') for p in r['players'].values())]}
            if action in ("create", "quick", "join"):
                return self._enter(payload, now, question_provider)
            code, token = payload.get("code"), payload.get("token")
            room = self.rooms.get(code) if isinstance(code, str) else None
            if not room or not isinstance(token, str) or token not in room["players"]:
                raise ArenaError("Phòng đã hết hạn hoặc mã tham gia không hợp lệ.", 404)
            player = room["players"][token]
            if action!='leave' and room.get('sourcePool','legacy')!=payload.get('sourcePool','legacy'):
                raise ArenaError('Nguồn câu của phòng không mở ở địa chỉ truy cập này.',403)
            player["seen"] = now
            if action=='accept':
                if token!=room['host'] or room['status']!='challenged':
                    raise ArenaError('Chỉ chủ phòng có thể chấp nhận thách đấu.',403)
                room.update(status='preparing',readyAt=now+3)
            elif action=='emote':
                value=payload.get('emote')
                if room['status']=='playing' and now>=player['emoteAvailableAt'] and type(value) is int and 0<=value<10:
                    player.update(emote=value,emoteUntil=now+4,emoteAvailableAt=now+5)
                return self._view(room,token)
            if action in ("answer", "next") and payload.get("index") != room["index"]:
                return self._view(room, token)
            if action == "answer":
                self._answer(room, player, payload, now)
            elif action == "next":
                self._tick(room,now)
            elif action == "leave":
                if room['status'] in ('waiting', 'challenged', 'preparing'):
                    room.update(status='cancelled', interrupted=True)
                elif room['status'] == 'playing':
                    if self._decided(room):
                        room['status'] = 'finished'
                    else:
                        room.update(status='finished', interrupted=True,
                                    endReason='forfeit', abandonedTokens=[token])
            elif action not in ("state",'accept'):
                raise ArenaError("Thao tác phòng không hợp lệ.")
            return self._view(room, token)

    @staticmethod
    def _decided(room):
        return room['resolved'] and (room['index'] == 19 or
                                    any(p['hp'] == 0 for p in room['players'].values()))

    def _cleanup(self, now):
        for code, room in list(self.rooms.items()):
            gone = [key for key, p in room['players'].items()
                    if now - p['seen'] > room['disconnectAfter']]
            if now > room['expiresAt']:
                if room['status'] == 'playing':
                    if self._decided(room):
                        room['status'] = 'finished'
                    else:
                        room.update(status='finished', interrupted=True,
                                    endReason='disconnect', abandonedTokens=gone or list(room['players']))
                elif room['status'] in ('waiting', 'challenged', 'preparing'):
                    room.update(status='cancelled', interrupted=True)
                # Keep an expired room for durable settlement, while its public
                # token still expires immediately as before.
                self.retired[room['id']] = room
                del self.rooms[code]
            elif room['status'] == 'waiting' and now - room['created'] >= 300:
                room.update(status='cancelled')
            elif room['status'] == 'challenged' and now >= room['challengeUntil']:
                room.update(status='cancelled')
            elif room['status'] == 'preparing' and gone:
                room.update(status='cancelled', interrupted=True)
            elif room['status'] == 'playing' and gone and not self._decided(room):
                room.update(status='finished', interrupted=True,
                            endReason='disconnect', abandonedTokens=gone)
            else:
                self._tick(room, now)

    def _enter(self, payload, now, question_provider=None):
        name, grade = payload.get("name"), payload.get("grade")
        difficulty, scope = payload.get("difficulty", 0), payload.get("scope", "weekly")
        source_pool=payload.get('sourcePool','legacy')
        if source_pool not in ('legacy','local-test','qa-separate'):
            raise ArenaError('Nguồn câu phòng không hợp lệ.')
        try:
            name = validate_nickname(name)
        except ValueError as error:
            raise ArenaError(str(error)) from error
        if type(grade) is not int or grade not in range(1, 6):
            raise ArenaError("Khối lớp cần nằm trong khoảng 1–5.")
        if type(difficulty) is not int or difficulty not in range(4) or scope not in ("weekly", "all"):
            raise ArenaError("Tùy chọn trận không hợp lệ.")
        room = None
        own=next((r for r in self.rooms.values() if r['status'] in ('waiting','challenged','preparing','playing')
                  and any(p['accountId']==payload.get('accountId') for p in r['players'].values()) and payload.get('accountId') is not None),None)
        if own: raise ArenaError('Em đang có phòng. Hãy quay lại hoặc rời phòng trước.')
        if payload["action"] == "join":
            code = payload.get("code", "")
            room = self.rooms.get(code.upper()) if isinstance(code, str) else None
            if not room or room["status"] != "waiting":
                raise ArenaError("Phòng không tồn tại, đã đủ người hoặc đã kết thúc.", 404)
            if room["grade"] != grade:
                raise ArenaError("Hai người chơi cần cùng khối.")
            if room.get('sourcePool','legacy')!=source_pool:
                raise ArenaError('Nguồn câu của phòng không mở ở địa chỉ truy cập này.',403)
            if '_eligibleRoomIds' in payload and room['id'] not in payload['_eligibleRoomIds']:
                raise ArenaError('Phòng đang có người chơi giữ chỗ ở trò khác.',409)
        elif payload["action"] == "quick":
            candidates=[r for r in self.rooms.values() if r["public"] and r["status"] == "waiting" and len(r['players'])<2
                         and (r["grade"], r["difficulty"], r["scope"]) == (grade, difficulty, scope)
                         and r.get('sourcePool','legacy')==source_pool]
            if '_eligibleRoomIds' in payload:candidates=[r for r in candidates if r['id'] in payload['_eligibleRoomIds']]
            if '_quickRoomId' in payload:candidates=[r for r in candidates if r['id']==payload['_quickRoomId']]
            room=min(candidates,key=lambda r:(-len(r['players']),r['created'],r['id'])) if candidates else None
        if room is None:
            if len(self.rooms) >= 500:
                raise ArenaError("Các phòng thử đang đầy. Em hãy thử lại sau.", 503)
            code = self._code()
            while code in self.rooms:
                code = self._code()
            # The authenticated API supplies a trusted database-backed factory.
            # A withdrawal/empty DB must never fall back to a public/demo bank.
            questions = deepcopy(question_provider(grade, difficulty, scope) if question_provider else
                                 self._questions(grade, difficulty, scope))
            if len(questions) != 20:
                raise ArenaError('Chưa đủ câu hỏi đã phát hành cho trận đấu.', 503)
            # Mobile browsers may pause polling while a child reads a whole
            # question. Allow that duration plus one minute, still bounded by
            # the room lifetime and explicit leave handling.
            disconnect_after = max(question_seconds(grade, q['difficulty']) for q in questions) + 60
            room = {
                "code": code, "id": secrets.token_hex(16), "grade": grade,
                "sourcePool":source_pool,
                "difficulty": difficulty, "scope": scope, "public": payload["action"] == "quick" or payload.get('public') is True,
                "created": now, "status": "waiting", "players": {}, "index": 0,
                "questions": questions, "resolved": False, 'roundReason':None, 'lastAttack':None,
                'defenseUntil':None, 'attacker':None, 'damage':None,
                "deadline": now + question_seconds(grade, questions[0]['difficulty']), "interrupted": False, 'nextAt':None,
                'disconnectAfter':disconnect_after,
                # Waiting, challenge, preparation, every question/transition and
                # a disconnect grace period all fit within the room lifetime.
                'expiresAt': now + 300 + 30 + 3 + disconnect_after + sum(question_seconds(grade, q['difficulty']) + 6 for q in questions),
            }
            self.rooms[code] = room
        token = secrets.token_urlsafe(32)
        room["players"][token] = {"name": name.strip(), "hp": 100, "correct": 0,
                                  "answer": None, "feedback": "", "seen": now, 'answers':{},'emote':None,'emoteUntil':0,'emoteAvailableAt':0,
                                  'accountId':payload.get('accountId'),'stats':payload.get('stats',{})}
        if len(room['players'])==1: room['host']=token
        if len(room["players"]) == 2:
            if room['public'] and payload.get('_autoStartPublic') is True:
                room.update(status='preparing',readyAt=now+3)
            else:
                room.update(status='challenged',challengeUntil=now+30)
        return {"code": room["code"], "token": token}

    @staticmethod
    def _resolve(room, now, reason):
        if not room['resolved']:
            room.update(resolved=True,nextAt=now+3,roundReason=reason)
            if reason == 'timeout':
                for player in room['players'].values():
                    player['feedback'] = 'Hết thời gian câu này. Hai bên giữ nguyên máu.'
            elif reason == 'both_wrong':
                for player in room['players'].values():
                    player['feedback'] = 'Hai bạn chưa trả lời đúng. Hai bên giữ nguyên máu.'

    def _tick(self,room,now):
        if room['status']=='preparing' and now>=room['readyAt']:
            room.update(status='playing',deadline=now+question_seconds(room['grade'], room['questions'][room['index']]['difficulty']))
        if room['status']!='playing': return
        if not room['resolved']:
            if room.get('defenseUntil') is not None:
                if now >= room['defenseUntil']:
                    self._settle_attack(room, room['defenseUntil'], False)
            elif now>=room['deadline']:
                self._resolve(room,now,'timeout')
        if room['resolved'] and now>=room['nextAt']:
            if room['index']==19 or any(p['hp']==0 for p in room['players'].values()):
                room['status']='finished'
            else:
                index = room['index'] + 1
                room.update(index=index,deadline=now+question_seconds(room['grade'], room['questions'][index]['difficulty']),resolved=False,nextAt=None,roundReason=None,defenseUntil=None,attacker=None,damage=None)
                for p in room['players'].values(): p.update(answer=None,feedback='')

    @staticmethod
    def _code():
        return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

    def _questions(self, grade, difficulty, scope='weekly'):
        """Unranked standalone preview only; authenticated matches inject a DB factory."""
        from .question_bank import sample_problem
        topics = {1:('add','subtract','compare','missing'),
                  2:('add','subtract','multiply','divide'),
                  3:('multiply','divide','perimeter','missing'),
                  4:('multiply','divide','area','fraction'),
                  5:('decimal','percent','area','fraction')}[grade]
        questions, seen = [], set()
        for index in range(20):
            for attempt in range(1000):
                question = sample_problem(grade, topics[index % len(topics)], min(3, difficulty), index, self.random)
                if question['text'] not in seen:
                    break
            else:
                raise ArenaError('Chưa đủ câu hỏi mẫu khác nhau.', 503)
            seen.add(question['text'])
            questions.append({**question, 'id':'preview-' + secrets.token_hex(12),
                              'topicTitle':'Luyện tập mẫu khối ' + str(grade)})
        return questions

    def _answer(self, room, player, payload, now):
        if room["status"] != "playing" or room["resolved"] or player["answer"] is not None:
            return
        answer = payload.get("answer")
        question = room["questions"][room["index"]]
        if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER:
            raise ArenaError("Nhập đáp án từ 1 đến 500 ký tự.")
        if question.get('responseMode')=='choice' and answer not in question.get('options',[]):
            raise ArenaError('Em hãy chọn một phương án của câu hỏi.')
        deadline = room.get('defenseUntil') or room['deadline']
        if now >= deadline:
            return
        player["answer"] = answer
        player['answers'][room['index']]=answer
        correct = question_correct(question,answer)
        if correct:
            player["correct"] += 1
        if room.get('defenseUntil') is not None:
            self._settle_attack(room, now, correct)
        elif correct:
            opponent = next(p for p in room['players'].values() if p is not player)
            room['attacker'] = next(token for token, member in room['players'].items() if member is player)
            room['defenseUntil'] = now + 3
            if opponent['answer'] is not None:
                self._settle_attack(room, now, False)
            else:
                player['feedback'] = 'Em trả lời đúng! Chờ đối thủ phòng thủ.'
                opponent['feedback'] = 'Đối thủ chuẩn bị tấn công! Trả lời đúng để giảm sát thương.'
        else:
            player["feedback"] = "Câu trả lời chưa đúng. Đang chờ đối thủ."
            if all(p['answer'] is not None for p in room['players'].values()): Arena._resolve(room,now,'both_wrong')

    def _settle_attack(self, room, now, defended):
        if room['resolved']:
            return
        attacker = room['players'][room['attacker']]
        defender = next(p for p in room['players'].values() if p is not attacker)
        damage = 10 if defended else 20
        defender['hp'] = max(0, defender['hp'] - damage)
        attacker['feedback'] = ('Đối thủ đỡ đòn! ' if defended else '') + f'Em gây {damage} sát thương.'
        defender['feedback'] = ('Đỡ đòn! ' if defended else 'Trúng đòn! ') + f'Em mất {damage} máu.'
        room['damage'] = damage
        room['lastAttack'] = {'id':room['id'] + ':' + str(room['index']),
            'spell':self.random.choice(('rock','vine','lightning')), 'index':room['index'],
            'attacker':room['attacker'], 'damage':damage, 'defended':defended}
        self._resolve(room, now, 'correct')

    @staticmethod
    def _view(room, token):
        player = room["players"][token]
        opponent = next((p for key, p in room["players"].items() if key != token), None)
        now = time.time()
        timing={'serverNow':now*1000}
        attack = room['lastAttack']
        last_attack = {**attack, 'attacker':'me' if attack['attacker'] == token else 'opponent'} if attack else None
        if room['status']=='cancelled': return {'status':'cancelled',**timing}
        if room['status']=='challenged':
            return {'status':'challenged','code':room['code'],'host':token==room['host'],
                    'opponent':safe_nickname(opponent['name']),'opponentStats':{key:opponent['stats'].get(key, 'sprout' if key=='mascot' else 0) for key in ('mascot','xp','level','wins','losses')},'opponentGrade':room['grade'],'challengeUntil':room['challengeUntil']*1000,**timing}
        if room['status']=='preparing':
            return {'status':'preparing','readyAt':room['readyAt']*1000,**timing}
        if room["status"] == "finished":
            reason = room.get('endReason', 'disconnect' if room['interrupted'] else 'completed')
            if reason == 'forfeit':
                outcome, points = ('lose', -1) if token in room['abandonedTokens'] else ('win', 0)
            elif room["interrupted"]:
                outcome, points = "left", 0
            elif player["hp"] == 0:
                outcome, points = "lose", -1
            elif opponent and opponent["hp"] == 0:
                outcome, points = "win", 2
            else:
                outcome, points = "draw", 0
            return {"status": "finished", "result": {
                "id": room["id"], "grade": room["grade"], "mode": "player",
                "completed": not room['interrupted'], "reason": reason,
                "outcome": outcome, "points": points, "correct": player["correct"],
                "hp": player["hp"], "opponentHp": opponent["hp"] if opponent else 100,
                'lastAttack':last_attack,
                "opponentMascot": opponent['stats'].get('mascot','fox') if opponent else 'fox',
                "opponentXp": opponent['stats'].get('xp',0) if opponent else 0,
                "rounds": room["index"] + 1, "review": [{**q,'myAnswer':player['answers'].get(i),
                    'correct':question_correct(q,player['answers'].get(i))} for i,q in enumerate(room['questions'][:room['index']+1])],
            }}
        if room["status"] == "waiting":
            return {"status": "waiting", "code": room["code"],
                    'expiresAt':(room['created']+300)*1000,'public':room['public'],**timing,
                    "players": [safe_nickname(p["name"]) for p in room["players"].values()]}
        # Keep round positions/count for the client, but disclose only the
        # current prompt/options. Future questions and all answers stay server-side.
        questions = [{key: value for key, value in q.items() if key not in ("answer", "steps", "gradingRule", "thinking", "solution") and (key!="options" or q.get("responseMode")=="choice")}
                     if index == room['index'] else {'id':'round-' + str(index), 'difficulty':q['difficulty']}
                     for index, q in enumerate(room["questions"])]
        if player['answer'] is not None:
            q = room['questions'][room['index']]
            round_outcome = 'correct' if question_correct(q,player['answer']) else 'wrong'
        elif room['roundReason'] == 'correct':
            round_outcome = 'opponent'
        elif room['roundReason'] == 'timeout':
            round_outcome = 'timeout'
        else:
            round_outcome = 'waiting'
        return {"status": "playing", **timing, "battle": {
            "id": room["id"], "grade": room["grade"], "mode": "player",
            "index": room["index"], "questions": questions,
            'lastAttack':last_attack,
            'defenseUntil':room.get('defenseUntil') * 1000 if room.get('defenseUntil') and not room['resolved'] else None,
            'attacking':room.get('attacker') == token, 'damage':room.get('damage'),
            "hp": player["hp"], "opponentHp": opponent["hp"], "opponent": safe_nickname(opponent["name"]),
            "correct": player["correct"], "answer": player["answer"],
            "deadline": room["deadline"] * 1000, "resolved": room["resolved"],
            'roundOutcome':round_outcome, 'roundReason':room['roundReason'],
            "feedback": player["feedback"], 'nextAt':room['nextAt']*1000 if room['nextAt'] else None,
            'opponentMascot':opponent['stats'].get('mascot','fox'),
            'opponentXp':opponent['stats'].get('xp',0),
            'myEmote':player['emote'] if now<player['emoteUntil'] else None,
            'opponentEmote':opponent['emote'] if now<opponent['emoteUntil'] else None,
            'emoteAvailableAt':player['emoteAvailableAt']*1000,
            'emoteUsed':now<player['emoteAvailableAt'],
        }}
