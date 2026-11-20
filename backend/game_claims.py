"""Atomic main-student occupancy and nonce ledger for every authenticated game.

Callers hold the same SQLite writer transaction as admission/consumption. Room
state determines human occupancy; BOT checkpoints are explicitly unranked demo.
"""
import hashlib,hmac,json,re,secrets,time,math
from copy import deepcopy
from urllib.parse import urlsplit,parse_qs
from . import platform_api as api

ACTIVE=('waiting','challenged','preparing','playing','intermission')
BOT_STATE=frozenset(('index','hp','opponentHp','answer','resolved','correct','feedback','review','readyAt','deadline','botAt','botAnswered','defenseUntil','attacking','damage','draftAnswer','nextAt','roundOutcome','roundReason','lastAttack','botForcedCorrect','forcedReason'))

def now(handler):return int(getattr(handler.server,'game_claim_clock',lambda:time.time()*1000)())
def arena_for(handler):
    if not hasattr(handler.server,'arena'):
        from .arena import Arena
        handler.server.arena=Arena()
    return handler.server.arena
def pool(handler,db):
    if api.native_test_games(handler) is not None:return 'local-test'
    if api.qa_arena_source(handler,db) is not None:return 'qa-separate'
    return 'legacy'
def key(body):
    value=body.get('requestKey')
    if value is None:return 'legacy:'+secrets.token_hex(16)
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,100}',value):raise api.APIError('Mã yêu cầu trò chơi không hợp lệ.')
    return value
def signature(game,action,body,source):
    value={k:body[k] for k in ('mode','playMode','public','code','scope','difficulty') if k in body}
    if isinstance(value.get('code'),str):value['code']=value['code'].upper()
    return hashlib.sha256(api.packed([game,action,source,value]).encode()).hexdigest()
def _row(db,sid):return db.execute('SELECT * FROM game_claims WHERE student_id=?',(sid,)).fetchone()
def _close(db,row,status='finished'):
    db.execute('DELETE FROM game_claims WHERE student_id=? AND claim_id=?',(row['student_id'],row['claim_id']))
    db.execute('UPDATE game_claim_requests SET status=? WHERE student_id=? AND claim_id=?',(status,row['student_id'],row['claim_id']))

def public(handler,db,row):
    if row is None:return None
    value=json.loads(row['payload_json']);accessible=row['source_pool']==pool(handler,db)
    result={'claimId':row['claim_id'],'game':row['game'],'playMode':row['play_mode'],'roomId':row['room_id'],
        'sourcePool':row['source_pool'],'sourceAvailable':accessible,'expiresAt':row['expires_at'],
        'resumeUrl':value['resumeUrl'],'checkpointRevision':value.get('checkpointRevision',0)}
    if value.get('code'):result['code']=value['code']
    result['serverTime']=now(handler)
    if row['game']!='duel':
        from .group_games import WAITING_MS
        record=db.execute('SELECT payload_json FROM group_game_rooms WHERE id=?',(row['room_id'],)).fetchone()
        if record:
            room=json.loads(record[0]);result['roomStatus']=room['status']
            result['waitingExpiresAt']=room['createdAt']+WAITING_MS
            result['serverTime']=_group_service(handler).clock()
    if accessible and row['game']=='duel' and row['play_mode']=='human':
        with handler.server.arena.lock:
            room=next((r for r in handler.server.arena.rooms.values() if r['id']==row['room_id']),None)
            if room:
                result['roomStatus']=room['status']
                token=next((t for t,p in room['players'].items() if p['accountId']==row['account_id']),None)
                if token:result['credentials']={'code':room['code'],'token':token}
    if accessible and row['game']=='duel' and row['play_mode']=='bot':
        result['botBattle']={**deepcopy(value['initial']),**deepcopy(value.get('state',{})),
            'id':row['claim_id'],'gameClaimId':row['claim_id'],'mode':'bot','botLevel':1,
            'grade':value['initial']['grade'],'questions':deepcopy(value['initial']['questions'])}
    return result

def conflict(handler,db,session,message='Em đang có một phòng chơi. Hãy tiếp tục hoặc rời phòng đó trước.',row=None):
    error=api.APIError(message,409);error.gameClaim=public(handler,db,row if row is not None else _row(db,session['student_id']));raise error

def bind(handler,db,session,game,play_mode,room_id,source,payload,expires):
    existing=_row(db,session['student_id']);clock=now(handler)
    if existing and (existing['game'],existing['room_id'],existing['play_mode'])==(game,room_id,play_mode):return existing
    if existing:conflict(handler,db,session,row=existing)
    cid=secrets.token_hex(16)
    db.execute('INSERT INTO game_claims VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (session['student_id'],session['account_id'],cid,game,play_mode,room_id,source,api.packed(payload),clock,clock,expires))
    return _row(db,session['student_id'])

def sync_group(db,room):
    for row in db.execute('SELECT * FROM game_claims WHERE game=? AND room_id=?',(room['mode'],room['id'])).fetchall():
        player=next((p for p in room['players'] if p['studentId']==row['student_id']),None)
        if room['status'] not in ACTIVE or player is None or player['forfeited']:_close(db,row,'left' if player and player['forfeited'] else 'finished')

def sync_duel(db,arena):
    for row in db.execute("SELECT * FROM game_claims WHERE game='duel' AND play_mode='human'").fetchall():
        record=db.execute('SELECT d.status FROM duels d JOIN arena_members m ON m.duel_id=d.id WHERE m.room_id=? AND m.student_id=?',(row['room_id'],row['student_id'])).fetchone()
        if not record or record[0] not in ('waiting','active'):_close(db,row)

def _group_service(handler):
    runtime=getattr(handler.server,'local_test_games',None)
    if runtime is not None:return runtime.group_games
    service=getattr(handler.server,'group_games',None)
    if service is not None:return service
    from .group_game_bots import BotGroupGames
    return BotGroupGames()

def current(handler,db,session):
    """Reconcile before admission. Never frees a live human room by lease alone."""
    sid=session['student_id'];arena=arena_for(handler);credentials=None;source=pool(handler,db)
    with arena.lock:
        for r in arena.rooms.values():
            if r['status'] not in ACTIVE:continue
            token=next((t for t,p in r['players'].items() if p['accountId']==session['account_id']),None)
            if token and r.get('sourcePool','legacy')==source:
                credentials={'code':r['code'],'token':token,'sourcePool':source};break
    api._arena_preflight(db,arena,session,credentials)
    sync_duel(db,arena)
    legacy=[]
    with arena.lock:
        for room in arena.rooms.values():
            if room['status'] in ACTIVE and any(p['accountId']==session['account_id'] for p in room['players'].values()):
                legacy.append(('duel','human',room['id'],room.get('sourcePool','legacy'),
                    {'code':room['code'],'resumeUrl':'/phong-dau/'},int(room['expiresAt']*1000)))
    service=_group_service(handler)
    rows=db.execute("SELECT payload_json FROM group_game_rooms WHERE status IN ('waiting','playing','intermission') AND EXISTS(SELECT 1 FROM json_each(payload_json,'$.players') WHERE json_extract(value,'$.studentId')=? AND json_extract(value,'$.forfeited')=0)",(sid,)).fetchall()
    for record in rows:
        room=json.loads(record[0]);service._tick(db,room,service.clock());sync_group(db,room)
        player=next((p for p in room['players'] if p['studentId']==sid),None)
        if room['status'] in ACTIVE and player and not player['forfeited']:
            legacy.append((room['mode'],room.get('playMode','human'),room['id'],room.get('sourcePool',source),
                {'code':room['code'],'resumeUrl':'/dau-tri/?game='+room['mode']+'&room='+room['id']},room['createdAt']+300000+len(room['questions'])*63000))
    row=_row(db,sid)
    if row and row['game']=='duel' and row['play_mode']=='bot':
        if now(handler)>=row['expires_at']:_close(db,row,'expired');row=None
        else:legacy.append(('duel','bot',row['room_id'],row['source_pool'],json.loads(row['payload_json']),row['expires_at']))
    if len(legacy)>1:
        error=api.APIError('Tài khoản có phòng cũ chưa khép lại. Hãy rời một phòng trước khi bắt đầu trò chơi khác.',409)
        error.gameClaim=public(handler,db,row);error.gameConflicts=[{'game':g,'playMode':p,'roomId':rid,'resumeUrl':data['resumeUrl']} for g,p,rid,_,data,_ in legacy];raise error
    if row and not any((g,rid)==(row['game'],row['room_id']) for g,_,rid,_,_,_ in legacy):_close(db,row);row=None
    if not row and legacy:
        game,mode,rid,source,data,expires=legacy[0];row=bind(handler,db,session,game,mode,rid,source,data,expires)
    return row

def begin(handler,db,session,game,action,body):
    row=current(handler,db,session);nonce=key(body);sig=signature(game,action,body,pool(handler,db))
    old=db.execute('SELECT * FROM game_claim_requests WHERE student_id=? AND request_key=?',(session['student_id'],nonce)).fetchone()
    if old:
        if old['signature']!=sig:conflict(handler,db,session,'Mã yêu cầu đã được dùng cho lựa chọn trò chơi khác.',row)
        if old['status']!='active' or row is None or row['claim_id']!=old['claim_id']:conflict(handler,db,session,'Lượt chơi này đã kết thúc; hãy bắt đầu một lượt mới.',row)
        result=json.loads(old['response_json']);result['gameClaim']=public(handler,db,row)
        if game=='duel' and row['play_mode']=='human':result.update(result['gameClaim'].get('credentials',{}))
        if game=='duel' and row['play_mode']=='bot':result['botBattle']=result['gameClaim'].get('botBattle')
        return nonce,sig,result
    if row:conflict(handler,db,session,row=row)
    return nonce,sig,None

def remember(handler,db,session,nonce,sig,row,result):
    from .game_limits import require_new_admission
    clock=now(handler)
    require_new_admission(db,session['student_id'],row['game'],row['room_id'],clock)
    stored=deepcopy(result);stored.pop('token',None);stored.pop('gameClaim',None)
    db.execute('INSERT INTO game_claim_requests VALUES (?,?,?,?,?,?,?,?,?)',
        (session['student_id'],nonce,sig,row['claim_id'],row['game'],row['room_id'],'active',api.packed(stored),clock))
    result['gameClaim']=public(handler,db,row);return result

def guard_generation(handler,db,session,body,room_id):
    expected=body.get('claimId')
    if expected is None:return
    row=_row(db,session['student_id'])
    if row is None or row['claim_id']!=expected or row['room_id']!=room_id:conflict(handler,db,session,'Phiên phòng đã thay đổi. Hãy tiếp tục phòng hiện tại.',row)

def occupants_available(handler,db,game,room_id,student_ids):
    for sid in student_ids:
        row=_row(db,sid)
        if row and row['game']=='duel' and row['play_mode']=='bot' and now(handler)>=row['expires_at']:_close(db,row,'expired');row=None
        if row and row['game']=='duel' and row['play_mode']=='human':
            duel=db.execute('SELECT d.status FROM duels d JOIN arena_members m ON m.duel_id=d.id WHERE m.room_id=? AND m.student_id=?',(row['room_id'],sid)).fetchone()
            if not duel or duel[0] not in ('waiting','active'):_close(db,row);row=None
        if row and row['game']!='duel':
            record=db.execute('SELECT payload_json FROM group_game_rooms WHERE id=?',(row['room_id'],)).fetchone()
            room=json.loads(record[0]) if record else None
            player=next((p for p in room['players'] if p['studentId']==sid),None) if room else None
            if not room or room['status'] not in ACTIVE or not player or player['forfeited']:_close(db,row);row=None
        if row and (row['game'],row['room_id'])!=(game,room_id):return False
    return True

def group_admission(handler,db,session,service,body,action,grade):
    mode=body.get('mode')
    if action!='join' and mode not in ('capture_flag','animal_race'):raise api.APIError('Game không hợp lệ.')
    source=pool(handler,db)
    if 'public' in body and type(body['public']) is not bool:raise api.APIError('Lựa chọn phòng công khai không hợp lệ.')
    if action=='quick' and body.get('playMode','human')!='human':raise api.APIError('Tìm nhanh chỉ ghép người chơi thật.')
    nonce,sig,replay=begin(handler,db,session,mode if action!='join' else 'group-join',action,body)
    if replay:
        row=_row(db,session['student_id']);room=service._load(db,row['room_id']);service._tick(db,room,service.clock());sync_group(db,room)
        return {'room':service.view(room,session['student_id'],service.clock()),'gameClaim':public(handler,db,_row(db,session['student_id']))}
    candidate=None
    if action=='quick':
        choices=[]
        for record in db.execute("SELECT payload_json FROM group_game_rooms WHERE mode=? AND grade=? AND status='waiting'",(mode,grade)).fetchall():
            room=json.loads(record[0]);service._tick(db,room,service.clock());sync_group(db,room)
            if (room['status']=='waiting' and room.get('public',True) and room.get('playMode','human')=='human' and len(room['players'])<5
                    and room.get('sourcePool',source)==source and room['sourceRevision'] in getattr(service,'accepted_source_revisions',{service.source.revision})
                    and occupants_available(handler,db,mode,room['id'],[p['studentId'] for p in room['players']])):choices.append(room)
        candidate=min(choices,key=lambda room:(-len(room['players']),room['createdAt'],room['id'])) if choices else None
    elif action=='join':
        code=body.get('code');record=db.execute('SELECT payload_json FROM group_game_rooms WHERE code=?',((code.upper() if isinstance(code,str) else ''),)).fetchone()
        if record:candidate=json.loads(record[0]);service._tick(db,candidate,service.clock());sync_group(db,candidate)
    if candidate:
        if candidate.get('sourcePool',source)!=source:raise api.APIError('Nguồn phòng không mở ở địa chỉ truy cập này.',403)
        if not occupants_available(handler,db,candidate['mode'],candidate['id'],[p['studentId'] for p in candidate['players']]):raise api.APIError('Phòng đang có phiên người chơi cần được khép lại trước.',409)
    entering='join' if candidate else 'create' if action=='quick' else action
    data={**body,'requestKey':nonce}
    if candidate:data['code']=candidate['code']
    view=service.enter(db,session,data,entering,grade);room=service._load(db,view['id'])
    if entering=='create':room.update(sourcePool=source,public=False if room.get('playMode')=='bot' else body.get('public',True));service._save(db,room,service.clock())
    row=bind(handler,db,session,room['mode'],room.get('playMode','human'),room['id'],room.get('sourcePool',source),
        {'code':room['code'],'resumeUrl':'/dau-tri/?game='+room['mode']+'&room='+room['id']},room['createdAt']+300000+len(room['questions'])*63000)
    # Adopt pre-existing authoritative members in the same transaction.
    for player in room['players']:
        if player.get('isBot') or player['studentId']==session['student_id']:continue
        principal=db.execute('SELECT id student_id,account_id FROM students WHERE id=?',(player['studentId'],)).fetchone()
        if principal and _row(db,principal['student_id']) is None:bind(handler,db,principal,room['mode'],'human',room['id'],source,{'code':room['code'],'resumeUrl':'/dau-tri/?game='+room['mode']+'&room='+room['id']},row['expires_at'])
    return remember(handler,db,session,nonce,sig,row,{'room':service.view(room,session['student_id'],service.clock())})

def bot_start(handler,db,session,body,questions,source_metadata=None):
    nonce,sig,replay=begin(handler,db,session,'duel','bot-start',body)
    if replay:return replay
    bank=questions() # must be ready before quota consumption or claim insertion
    if len(bank)!=20:raise api.APIError('Chưa đủ câu BOT cho phiên luyện tập.',503)
    from .learning_update import consume
    from .arena import question_seconds
    consume(db,session,'bot',nonce)
    clock=now(handler);grade=api.grade_for_student(db,session['student_id'],session['birth_year'])
    grace=max(question_seconds(grade,q['difficulty']) for q in bank)*1000+60000
    hard=clock+5000+sum(question_seconds(grade,q['difficulty'])*1000+3000 for q in bank)+grace
    room_id=secrets.token_hex(16);initial={'grade':grade,'questions':bank,'index':0,'hp':100,'opponentHp':100,'opponent':'BOT',
        'botLevel':1,'readyAt':clock+5000,'answer':None,'resolved':False,'correct':0,'feedback':'','review':[]}
    row=bind(handler,db,session,'duel','bot',room_id,pool(handler,db),
        {'resumeUrl':'/tran-dau/?bot='+room_id,'initial':initial,'state':{},'checkpointRevision':0,'idleGraceMs':grace,'hardExpiresAt':hard},min(clock+grace,hard))
    # Use claim identity for the URL and immutable browser checkpoint identity.
    payload=json.loads(row['payload_json']);payload['resumeUrl']='/tran-dau/?bot='+row['claim_id']
    db.execute('UPDATE game_claims SET payload_json=? WHERE student_id=?',(api.packed(payload),session['student_id']));row=_row(db,session['student_id'])
    result={'status':'started','questions':bank,'botRules':{'level':1,'ranked':False,'xpAward':0,'normalAccuracy':'existing-neutral-level'},'gradingMode':'client-demo','ranked':False,'xpAward':0}
    if source_metadata:result['questionSource']=source_metadata
    result['botBattle']=public(handler,db,row)['botBattle']
    return remember(handler,db,session,nonce,sig,row,result)

def checkpoint(handler,db,session,body,row):
    payload=json.loads(row['payload_json']);state=body.get('state')
    if state is not None:
        if not isinstance(state,dict) or len(api.packed(state))>100000:raise api.APIError('Bản lưu BOT không hợp lệ.')
        if type(body.get('expectedRevision')) is not int or body['expectedRevision']!=payload['checkpointRevision']:conflict(handler,db,session,'Bản lưu BOT đã được cập nhật ở phiên khác.',row)
        clean={k:deepcopy(v) for k,v in state.items() if k in BOT_STATE}
        for name in ('readyAt','deadline','botAt','defenseUntil','nextAt'):
            value=clean.get(name)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=now(handler)+172800000):raise api.APIError('Thời gian bản lưu BOT không hợp lệ.')
        for name in ('resolved','botAnswered','attacking','botForcedCorrect'):
            if name in clean and type(clean[name]) is not bool:raise api.APIError('Trạng thái bản lưu BOT không hợp lệ.')
        for name in ('feedback','draftAnswer','roundOutcome','roundReason','forcedReason'):
            value=clean.get(name)
            if value is not None and (not isinstance(value,str) or len(value)>(2000 if name=='feedback' else 500)):raise api.APIError('Nội dung bản lưu BOT không hợp lệ.')
        if clean.get('answer') is not None and (not isinstance(clean['answer'],str) or len(clean['answer'])>500):raise api.APIError('Đáp án bản lưu BOT không hợp lệ.')
        if clean.get('damage') is not None and (type(clean['damage']) is not int or not 0<=clean['damage']<=20):raise api.APIError('Sát thương bản lưu BOT không hợp lệ.')
        attack=clean.get('lastAttack')
        if attack is not None:
            if not isinstance(attack,dict) or set(attack)-{'id','spell','index','attacker','damage','defended'}:raise api.APIError('Hiệu ứng bản lưu BOT không hợp lệ.')
            if any(name in attack and (not isinstance(attack[name],str) or len(attack[name])>120) for name in ('id','spell','attacker')):raise api.APIError('Hiệu ứng bản lưu BOT không hợp lệ.')
            if 'attacker' in attack and attack['attacker'] not in ('me','opponent'):raise api.APIError('Người tấn công bản lưu BOT không hợp lệ.')
            if 'index' in attack and (type(attack['index']) is not int or not 0<=attack['index']<20):raise api.APIError('Câu hiệu ứng BOT không hợp lệ.')
            if 'damage' in attack and (type(attack['damage']) is not int or not 0<=attack['damage']<=20):raise api.APIError('Sát thương hiệu ứng BOT không hợp lệ.')
            if 'defended' in attack and type(attack['defended']) is not bool:raise api.APIError('Phòng thủ hiệu ứng BOT không hợp lệ.')
        if 'review' in clean:
            if not isinstance(clean['review'],list) or len(clean['review'])>20:raise api.APIError('Lời giải bản lưu BOT không hợp lệ.')
            from .answers import question_correct
            reviews=[]
            for n,item in enumerate(clean['review']):
                if not isinstance(item,dict) or item.get('myAnswer') is not None and (not isinstance(item['myAnswer'],str) or len(item['myAnswer'])>500):raise api.APIError('Đáp án xem lại BOT không hợp lệ.')
                question=deepcopy(payload['initial']['questions'][n]);answer=item.get('myAnswer');reviews.append({**question,'myAnswer':answer,'correct':question_correct(question,answer)})
            clean['review']=reviews
        index=clean.get('index',payload.get('state',{}).get('index',0));previous=payload.get('state',{}).get('index',0)
        if type(index) is not int or not 0<=index<len(payload['initial']['questions']) or index<previous:conflict(handler,db,session,'Bản lưu BOT cũ không thể ghi đè tiến độ mới.',row)
        for k in ('hp','opponentHp','correct'):
            limit=len(payload['initial']['questions']) if k=='correct' else 100
            if k in clean and (type(clean[k]) is not int or not 0<=clean[k]<=limit):raise api.APIError('Thông số bản lưu BOT không hợp lệ.')
        previous_state=payload.get('state',{})
        if any(k in clean and k in previous_state and clean[k]>previous_state[k] for k in ('hp','opponentHp')) or ('correct' in clean and clean['correct']<previous_state.get('correct',0)):
            conflict(handler,db,session,'Bản lưu BOT cũ không thể khôi phục máu hoặc ghi lùi kết quả.',row)
        if index==previous and previous_state.get('resolved') is True and clean.get('resolved') is False:conflict(handler,db,session,'Câu BOT đã chốt không thể mở lại.',row)
        payload['state']={**payload.get('state',{}),**clean};payload['checkpointRevision']+=1
    clock=now(handler);expires=min(clock+payload['idleGraceMs'],payload['hardExpiresAt'])
    db.execute('UPDATE game_claims SET payload_json=?,updated_at=?,expires_at=? WHERE student_id=? AND claim_id=?',
        (api.packed(payload),clock,expires,session['student_id'],row['claim_id']))

def dispatch(handler,method,path,body):
    with api.connect(handler.server.database_path,True) as db:
        session=api.read_session(handler,db)
        if not session:raise api.APIError('Em hãy đăng nhập để tiếp tục.',401)
        if method=='POST' and (not api.same_origin(handler) or not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),session['csrf_token'])):raise api.APIError('Phiên đăng nhập cần tải lại.',403)
        if path=='/api/v1/bot/adopt':
            if method!='POST':raise api.APIError('Phương thức không hợp lệ.',405)
            row=current(handler,db,session)
            if row and row['game']=='duel' and row['play_mode']=='bot' and body.get('claimId')==row['claim_id']:return {'claim':public(handler,db,row)},200
            conflict(handler,db,session,'Lượt BOT cũ chưa có bằng chứng phiên máy chủ nên không thể tiếp tục theo quy tắc một phòng. Bản lưu cục bộ được giữ; em có thể chủ động bắt đầu lượt mới theo hạn mức hiện có.',row)
        row=current(handler,db,session)
        if method=='GET':return {'claim':public(handler,db,row)},200
        if method!='POST':raise api.APIError('Phương thức không hợp lệ.',405)
        if row is None and body.get('action') in ('release','leave'):
            old=db.execute("SELECT 1 FROM game_claim_requests WHERE student_id=? AND claim_id=? AND status!='active'",(session['student_id'],body.get('claimId'))).fetchone()
            if old:return {'claim':None,'left':True,'alreadyReleased':True},200
        if row is None or body.get('claimId')!=row['claim_id']:conflict(handler,db,session,'Phiên phòng đã thay đổi; thao tác cũ không được áp dụng.',row)
        action=body.get('action')
        if action=='leave':
            if row['game']=='duel' and row['play_mode']=='human':
                with handler.server.arena.lock:
                    room=next((r for r in handler.server.arena.rooms.values() if r['id']==row['room_id']),None)
                    token=next((t for t,p in room['players'].items() if p['accountId']==session['account_id']),None) if room else None
                if token:api.arena_request(handler,db,session,{'action':'leave','code':room['code'],'token':token,'claimId':row['claim_id']})
                else:_close(db,row)
            elif row['game']!='duel':
                service=_group_service(handler);service.mutate(db,session,row['room_id'],{'requestKey':'claim-leave:'+row['claim_id']},'leave');sync_group(db,service._load(db,row['room_id']))
            else:_close(db,row,'left')
            return {'claim':public(handler,db,_row(db,session['student_id'])),'left':True},200
        if row['game']!='duel' or row['play_mode']!='bot':
            if action=='touch':return {'claim':public(handler,db,row)},200
            raise api.APIError('Hãy rời phòng thực tế trước; không thể xóa riêng quyền giữ chỗ.',409)
        if action=='touch':checkpoint(handler,db,session,body,row)
        elif action=='release':
            if body.get('reason') not in ('finish','leave'):raise api.APIError('Lý do kết thúc BOT không hợp lệ.')
            if body.get('state') is not None:checkpoint(handler,db,session,body,row)
            _close(db,row,'finished' if body['reason']=='finish' else 'left')
        else:raise api.APIError('Thao tác phiên trò chơi không hợp lệ.')
        return {'claim':public(handler,db,_row(db,session['student_id']))},200
