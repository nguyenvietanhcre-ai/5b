"""Explicitly installed, self-authored localhost curriculum samples.

This module never seeds a database on startup. The registry authorizes use as
samples and explicitly retains teacher_review=pending. Existing wallet, owner,
CSRF, quota, immutable exam and purchased-credit paths remain authoritative.
"""
import base64
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import secrets
from functools import lru_cache

from . import platform_api as api
from . import purchased_credits as credits
from . import wallet_qa as wallet
from .practice_catalogue import Practice

BATCH='5bmath.curriculum.samples.20261119'
BANDS={'free-basic':(10,'free',1),'free-advanced':(10,'free',2),'paid-78':(10,'paid',3),'paid-hsg':(3,'paid',4)}
DDL='''
CREATE TABLE IF NOT EXISTS curriculum_sample_batches(batch_id TEXT PRIMARY KEY,package_sha256 TEXT NOT NULL,authorization_json TEXT NOT NULL,status TEXT NOT NULL CHECK(status='active'),teacher_review TEXT NOT NULL CHECK(teacher_review='pending'),installed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS curriculum_sample_versions(content_key TEXT PRIMARY KEY,version_id INTEGER NOT NULL UNIQUE REFERENCES question_versions(id),batch_id TEXT NOT NULL REFERENCES curriculum_sample_batches(batch_id),grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),topic_key TEXT NOT NULL,skill_key TEXT NOT NULL,band TEXT NOT NULL,access TEXT NOT NULL CHECK(access IN ('free','paid')),score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10),content_sha256 TEXT NOT NULL,payload_sha256 TEXT NOT NULL,diagram_sha256 TEXT,metadata_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS curriculum_sample_grade_pool ON curriculum_sample_versions(grade,access,band);
CREATE TABLE IF NOT EXISTS curriculum_sample_assets(sha256 TEXT PRIMARY KEY,svg BLOB NOT NULL,alt TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL);
'''


def exists(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='curriculum_sample_versions'").fetchone())


def packed(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()


def loaded_package():
    if os.environ.get('MAM_TOAN_CURRICULUM_SAMPLES')!='1':return None
    path=Path(__file__).with_name('curriculum-samples.json')
    return _read_package(str(path),path.stat().st_mtime_ns) if path.is_file() else None


@lru_cache(maxsize=2)
def _read_package(path,modified):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def level(question):
    return BANDS[question['band']][2]


def validate_package(package):
    if package.get('id')!=BATCH or package.get('revision')!=1:raise ValueError('Unknown sample package')
    if package.get('teacherReview')!='pending' or not package.get('authorization',{}).get('localhostUse'):raise ValueError('Explicit sample-use authorization required')
    if package.get('validation',{}).get('status')!='pass':raise ValueError('Independent validation must pass before install')
    topics={t['id']:t for t in package['topics']};counts=Counter();seen=set()
    for q in package['questions']:
        if q['id'] in seen or q['topicId'] not in topics or q['grade']!=topics[q['topicId']]['grade']:raise ValueError('Identity/grade/topic mismatch')
        seen.add(q['id']);counts[q['topicId'],q['band']]+=1
        _,access,_=BANDS[q['band']]
        if q['access']!=access or q['responseType']!='choice':raise ValueError('Access/response mismatch')
        ranges={'free-basic':range(1,4),'free-advanced':range(4,7),'paid-78':range(7,9),'paid-hsg':range(9,11)}
        if type(q['difficultyScore']) is not int or q['difficultyScore'] not in ranges[q['band']]:raise ValueError('Difficulty band mismatch')
        options=q['options']
        if len(options)!=4 or {o['id'] for o in options}!={'A','B','C','D'} or len({o['text'] for o in options})!=4:raise ValueError('Exactly four distinct choices required')
        if sum(o['id']==q['correctOptionId'] for o in options)!=1 or any(not o.get('rationale') for o in options):raise ValueError('Choice key/rationale missing')
        if q['review']['teacher']!='pending' or not all(q.get(x) for x in ('thinking','keyPoint','solutionSteps','check','gradeFit')):raise ValueError('Incomplete editorial record')
    if len(topics)!=75 or len(seen)!=2475:raise ValueError('Full 75-topic / 2475-question package required')
    for tid in topics:
        for band,(expected,_,_) in BANDS.items():
            if counts[tid,band]!=expected:raise ValueError('Wrong per-topic allocation')
    return digest(package)


def install(db,package,*,pilot):
    """Caller supplies a writable transaction and backup; no old rows updated."""
    from .database import execute_sql
    from .question_access import digest as pin_digest,version
    from .local_pilot import safe_svg
    package_hash=validate_package(package)
    execute_sql(db,DDL)
    old=db.execute('SELECT package_sha256 FROM curriculum_sample_batches WHERE batch_id=?',(BATCH,)).fetchone()
    if old and old[0]!=package_hash:raise ValueError('Immutable sample package conflict')
    db.execute('INSERT OR IGNORE INTO curriculum_sample_batches VALUES (?,?,?,\'active\',\'pending\',?)',
               (BATCH,package_hash,packed(package['authorization']),api.stamp()))
    topics={t['id']:t for t in package['topics']};inserted=0
    for q in package['questions']:
        # Main game selectors receive only Free items. Paid contents stay in the
        # native attempt store, behind its existing quote/grant/wallet controls.
        if not pilot and q['access']!='free':continue
        current=db.execute('SELECT version_id,payload_sha256 FROM curriculum_sample_versions WHERE content_key=?',(q['id'],)).fetchone()
        if current:
            if current['payload_sha256']!=digest(q):raise ValueError('Immutable question payload conflict')
            row=version(db,current['version_id'])
            if not row or pin_digest(row)!=db.execute('SELECT content_sha256 FROM curriculum_sample_versions WHERE content_key=?',(q['id'],)).fetchone()[0]:raise ValueError('Installed question changed')
            continue
        tid=q['topicId'];topic=topics[tid]
        existing=db.execute('SELECT id,title FROM topics WHERE grade_id=? AND client_key=?',(q['grade'],tid)).fetchone()
        if existing and existing['title']!=topic['title']:raise ValueError('Topic identity conflict')
        topic_id=existing['id'] if existing else db.execute('INSERT INTO topics(grade_id,title,client_key) VALUES (?,?,?)',(q['grade'],topic['title'],tid)).lastrowid
        qid=db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (?,?,?)',(q['grade'],topic_id,q['id'])).lastrowid
        prompt=[{'type':'text','text':q['stem']}]
        diagram_sha=None
        if q.get('diagram'):
            diagram=q['diagram'];svg=safe_svg(diagram['svg'].encode('utf-8'));diagram_sha=hashlib.sha256(svg).hexdigest()
            db.execute('INSERT OR IGNORE INTO curriculum_sample_assets VALUES (?,?,?,?,?)',(diagram_sha,svg,diagram['alt'],diagram['width'],diagram['height']))
            if pilot:db.execute("INSERT OR IGNORE INTO local_lesson_assets VALUES (?,'image/svg+xml',?)",(diagram_sha,svg))
            prompt.append({'type':'media','sha256':diagram_sha,'alt':diagram['alt']})
        options=[o['text'] for o in q['options']]
        answer=next(o['text'] for o in q['options'] if o['id']==q['correctOptionId'])
        rule={'answer':answer,'answerKind':'text','responseType':'choice','answerShape':'single',
              'choiceRationales':[o['rationale'] for o in q['options']]}
        steps=[{'type':'text','text':s} for s in q['solutionSteps']]
        status='draft' if pilot else 'published'
        vid=db.execute('INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,status,options_json) VALUES (?,1,?,1,?,?,?,?,?,?)',
                       (qid,level(q),api.packed(prompt),api.packed(rule),api.packed(steps),api.packed([{'type':'text','text':q['thinking']}]),status,api.packed(options))).lastrowid
        if pilot:
            db.execute('INSERT INTO pilot_content VALUES (?,?,?)',(q['id'],qid,'free' if q['access']=='free' else 'vip'))
            sections=[{'key':'thinking','title':'Định hướng tư duy','blocks':[{'type':'text','text':q['thinking']}]},
                      {'key':'key','title':'Điểm mấu chốt','blocks':[{'type':'text','text':q['keyPoint']}]},
                      {'key':'detail','title':'Bài giải chi tiết','blocks':steps+[{'type':'text','text':'Đáp số: '+q['answerText']},{'type':'text','text':'Thử lại: '+q['check']},
                           {'type':'text','text':'Vận dụng: '+q['extension']['prompt']},{'type':'text','text':'Đối chiếu: '+q['extension']['answer']}]}]
            lesson={'schemaVersion':1,'id':q['id'],'revision':1,'grade':q['grade'],'title':'Giải câu '+q['id'],
                    'status':'draft','reviewerType':'assistant','sourceLabel':'Mẫu tự biên soạn · đã tự kiểm · chờ giáo viên duyệt',
                    'source':{'kind':'original-authored','contentKey':q['id'],'independentTeacherReview':'pending'},'prompt':prompt,'overview':[], 'sections':sections}
            db.execute('INSERT INTO local_lesson_versions VALUES (?,1,?,?)',(q['id'],digest(lesson),api.packed(lesson)))
            db.execute('INSERT INTO local_lesson_pins VALUES (?,?,1)',(vid,q['id']))
        row=version(db,vid)
        db.execute('INSERT INTO curriculum_sample_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (q['id'],vid,BATCH,q['grade'],tid,q['skillId'],q['band'],q['access'],q['difficultyScore'],pin_digest(row),digest(q),diagram_sha,api.packed(q)))
        inserted+=1
    return {'inserted':inserted,'packageHash':package_hash,'pilot':pilot,'teacherReview':'pending'}


def valid_rows(db,grade=None,*,access=None):
    if not exists(db):return []
    from .question_access import digest as pin_digest
    query=('SELECT s.content_key,s.access,s.version_id,s.grade,s.content_sha256,v.*,q.grade_id,q.topic_id,q.question_code FROM curriculum_sample_versions s '
           'JOIN curriculum_sample_batches b ON b.batch_id=s.batch_id JOIN question_versions v ON v.id=s.version_id '
           'JOIN questions q ON q.id=v.question_id WHERE b.status=\'active\' AND v.status IN (\'draft\',\'published\')')
    params=[]
    if grade is not None:query+=' AND s.grade=?';params.append(grade)
    if access is not None:query+=' AND s.access=?';params.append(access)
    rows=db.execute(query,params).fetchall()
    return [r for r in rows if r['grade']==r['grade_id'] and r['content_sha256']==pin_digest(r)]


def active(db,grade):
    return bool(valid_rows(db,grade))


def registered(db,identity):
    if not exists(db):return None
    from .question_access import version,digest as pin_digest
    info=db.execute('SELECT s.* FROM curriculum_sample_versions s JOIN curriculum_sample_batches b ON b.batch_id=s.batch_id WHERE s.version_id=? AND b.status=\'active\'',(identity,)).fetchone()
    if not info:return None
    row=version(db,identity)
    return dict(info) if row and info['content_sha256']==pin_digest(row) and info['grade']==row['grade_id'] else False


def main_allowed(db,identity,*,session=None,purpose='practice',public_game=False):
    info=registered(db,identity)
    if info is None:return None
    if not info or info['access']!='free':return False
    if purpose in ('arena','group-games') and info['diagram_sha256']:return False
    return bool(purpose in ('arena','group-games') and public_game or purpose in ('practice','premium') and session and session['student_id'])


def free_keys(db):
    return {r['content_key'] for r in valid_rows(db,access='free')}


def paid_keys(db):
    return {r['content_key'] for r in valid_rows(db,access='paid')}


def export_lesson(db,identity):
    """Private PDF snapshot for the already-authorized question version."""
    info=registered(db,identity)
    if not info:return None
    q=json.loads(info['metadata_json'])
    if digest(q)!=info['payload_sha256']:raise api.APIError('Bản mẫu đã thay đổi; chưa thể tải đúng phiên bản.',409)
    blocks=lambda text:[{'type':'text','text':text}]
    return {'schemaVersion':1,'id':q['id'],'revision':q['revision'],'grade':q['grade'],
            'sourceLabel':'Mẫu tự biên soạn · chờ giáo viên duyệt','sections':[
                {'key':'thinking','title':'Định hướng tư duy','blocks':blocks(q['thinking'])},
                {'key':'key','title':'Điểm mấu chốt','blocks':blocks(q['keyPoint'])},
                {'key':'detail','title':'Bài giải chi tiết','blocks':
                 [{'type':'text','text':s} for s in q['solutionSteps']]+blocks('Đáp số: '+q['answerText'])+
                 blocks('Thử lại: '+q['check'])+blocks('Vận dụng: '+q['extension']['prompt'])+blocks('Đối chiếu: '+q['extension']['answer'])}]}


def export_asset(db,identity,sha):
    info=registered(db,identity)
    if not info or info['diagram_sha256']!=sha:return None
    row=db.execute('SELECT svg,alt FROM curriculum_sample_assets WHERE sha256=?',(sha,)).fetchone()
    if not row or hashlib.sha256(row['svg']).hexdigest()!=sha:raise api.APIError('Hình của bản mẫu đã thay đổi.',409)
    return {'mime':'image/svg+xml','payload':row['svg'],'alt':row['alt']}


def annotate(db,identity,question,*,submitted=False):
    info=registered(db,identity)
    if not info:return
    question.update(sampleLabel='Mẫu tự biên soạn · chờ giáo viên duyệt',contentKey=info['content_key'],
                    sampleBand=info['band'],difficultyScore=info['score'],teacherReview='pending')
    if info['diagram_sha256']:
        asset=db.execute('SELECT * FROM curriculum_sample_assets WHERE sha256=?',(info['diagram_sha256'],)).fetchone()
        if not asset or hashlib.sha256(asset['svg']).hexdigest()!=info['diagram_sha256']:raise api.APIError('Hình minh họa cần được kiểm tra lại.',503)
        question['sampleDiagram']={'dataUrl':'data:image/svg+xml;base64,'+base64.b64encode(asset['svg']).decode(),
                                   'alt':asset['alt'],'width':asset['width'],'height':asset['height']}
    if submitted:
        q=json.loads(info['metadata_json'])
        question.update(thinking=q['thinking'],keyPoint=q['keyPoint'],check=q['check'],extension=q['extension'],
                        choiceRationales={o['text']:o['rationale'] for o in q['options']})


class CurriculumPractice(Practice):
    def __init__(self,provider,legacy,package):
        self.provider=provider;self.legacy=legacy;self.package=package
        self.questions={q['id']:q for q in package['questions']}
        self.topics={t['id']:t for t in package['topics']}
        self.mapping={q['id']:{'contentKey':q['id'],'quotaKey':q['id'],'proposedTopicKey':q['topicId'],
                                'topicTitle':self.topics[q['topicId']]['title'],'grade':q['grade']} for q in package['questions']}
        self.original={q['id']:{'contentKey':q['id'],'proposedAccess':'Free' if q['access']=='free' else 'VIP',
                                'difficultyOriginal':{'value':q['difficultyScore']}} for q in package['questions']}
        self.revision=digest({'package':digest(package),'policy':'curriculum-samples-choice-v1'})

    def supports_grade(self,grade):return grade in range(1,6)

    def pinned_source(self,db,config):
        return {r['content_key']:{'scope':'free' if r['access']=='free' else 'vip','in_window':True,'version_id':r['version_id']}
                for r in valid_rows(db,config.grade) if r['content_key'] in self.questions}

    def paid_inventory(self,db,config):
        rows=self.pinned_source(db,config)
        return sum(x['scope']=='vip' for x in rows.values()),len(rows)

    def create(self,db,session,body,config,*,balances=None,bank_db=None,bank_student_id=None):
        result=super().create(db,session,body,config,balances=balances,bank_db=bank_db,bank_student_id=bank_student_id)
        # The inherited selector supports mixed legacy representations. The
        # new batch is entirely MCQ, including the exam-level metadata. A replay
        # of an older request must retain its original representation.
        if result.get('questions') and all(q.get('sampleBand') and q.get('responseMode')=='choice' for q in result['questions']):
            db.execute("UPDATE exams SET response_mode='choice' WHERE id=? AND owner_student_id=? AND response_mode='typed'",
                       (int(result['id']),session['student_id']))
            result=api.exam_view(db,api.owned_attempt(db,session,int(result['id'])))
        return result

    def pool(self,db,session,config,*,funding=None,balances=None,_wallet=None):
        state=wallet.balance(db,session,config) if _wallet is None else _wallet
        budget=10000 if config.internal_unlimited else state['vip']['available']
        if funding:
            if balances is None:credits.unavailable()
            remaining=credits.amount_left(balances,funding)
            budget=remaining if funding==credits.QUESTIONS else credits.COMPLETE_COUNT if remaining else 0
        grants=dict(db.execute('SELECT content_key,version_id FROM pilot_grants WHERE student_id=?',(session['student_id'],)))
        items=[]
        for key,pin in self.pinned_source(db,config).items():
            q=self.questions[key];cost=0
            if key in grants:
                if grants[key]!=pin['version_id']:continue
            elif q['access']=='paid':
                if not budget:continue
                cost=1
            items.append({'contentKey':key,'versionId':pin['version_id'],'responseMode':'choice','topicKey':q['topicId'],
                          'topicTitle':self.topics[q['topicId']]['title'],'difficulty':level(q),
                          'access':'Free' if q['access']=='free' else 'VIP','cost':cost})
        return items,budget

    def metadata(self,db,session,config,*,_pool=None):
        pool,budget=self.pool(db,session,config) if _pool is None else _pool;result=[]
        for key,t in self.topics.items():
            if t['grade']!=config.grade:continue
            items=[x for x in pool if x['topicKey']==key]
            result.append({'key':key,'title':t['title'],'totalCount':33,'availableCount':self.capacity(items,budget),
                           'freeCount':sum(x['access']=='Free' for x in items),'paidCount':self.capacity([x for x in items if x['access']=='VIP'],budget),
                           'typedCount':0,'choiceCount':self.capacity(items,budget),
                           'difficulties':{str(n):self.capacity([x for x in items if x['difficulty']==n],budget) for n in range(1,5)}})
        return result

    def allocation(self,db,session,selection,config,*,funding=None,balances=None):
        valid=self.pinned_source(db,config);selected=[]
        for item in selection:
            pin=valid.get(item['contentKey'])
            if not pin or pin['version_id']!=item['versionId'] or item['responseMode']!='choice':raise api.APIError('Phiên bản mẫu đã đổi; chưa cấp hoặc trừ lượt.',409)
            selected.append({'content_key':item['contentKey'],'version_id':item['versionId']})
        a=wallet.plan(db,session,selected,{x['content_key']:x for x in selected},config,{'contentKeys':[x['contentKey'] for x in selection],'responseMode':'choice'},purchased_sku=funding)
        if funding:
            if balances is None:credits.unavailable()
            a['purchased']=credits.allocation(funding,balances,[x['quotaKey'] for x in a['allocations'] if x['source']=='purchased'])
        return a

    def catalogue(self,db,session,config,result):
        pool,budget=self.pool(db,session,config,_wallet=result['wallet']);eligible={x['contentKey']:x for x in pool};rows=[]
        for q in self.questions.values():
            if q['grade']!=config.grade:continue
            entry=eligible.get(q['id'])
            rows.append({'contentKey':q['id'],'title':self.topics[q['topicId']]['title'],'access':'Free' if q['access']=='free' else 'VIP',
                         'typed':False,'choiceRequired':True,'skillKey':q['skillId'],'topicKey':q['topicId'],'responseMode':'choice',
                         'difficulty':level(q),'difficultyScore':q['difficultyScore'],'band':q['band'],
                         'eligible':entry is not None,'cost':entry['cost'] if entry else None})
        result.update(grade=config.grade,curriculumSamples=True,questions=rows,typedEligible=[],responsePolicy='all-mcq-user-request-20261119',
                      topics=self.metadata(db,session,config,_pool=(pool,budget)),catalogueRevision=self.revision,availableFreeKeys=[q['contentKey'] for q in rows if q['access']=='Free'],
                      practiceBudget={'newPaidAvailable':budget,'internalUnlimited':config.internal_unlimited},
                      notice='Bộ mẫu Toán lớp '+str(config.grade)+' · tự biên soạn, đã tự kiểm, chờ giáo viên duyệt.')
        if config.grade!=5:result.update(knowledge={'topics':[],'lessons':[]},sets=[])
        return result


def activate_provider(provider,legacy):
    package=loaded_package()
    if not package:return legacy
    package_hash=validate_package(package)
    with api.connect(provider.path) as db:
        if not exists(db):return legacy
        row=db.execute('SELECT package_sha256 FROM curriculum_sample_batches WHERE batch_id=?',(BATCH,)).fetchone()
        if not row:return legacy
        if row[0]!=package_hash:raise ValueError('Runtime sample package does not match installed registry')
    return CurriculumPractice(provider,legacy,package)


class SampleArenaSource:
    """Free-only choices in the existing localhost game namespace."""
    qa_only=True
    def __init__(self,package,purpose):
        self.purpose=purpose;self.revision='curriculum-samples-'+digest(package)[:20]
        self.rows=[]
        topics={t['id']:t for t in package['topics']}
        for q in package['questions']:
            if q['access']!='free' or q.get('diagram'):continue
            self.rows.append({'id':q['id'],'revision':q['revision'],'grade':q['grade'],'text':q['stem'],
                              'answer':next(o['text'] for o in q['options'] if o['id']==q['correctOptionId']),
                              'options':[o['text'] for o in q['options']], 'responseMode':'choice','answerKind':'text',
                              'difficulty':level(q)-1,'steps':q['solutionSteps'],'topicTitle':topics[q['topicId']]['title'],
                              'sampleLabel':'Mẫu tự biên soạn · chờ giáo viên duyệt','choiceRationales':[o['rationale'] for o in q['options']]})
    def questions(self,grade,difficulty=0,scope='all'):
        bank=[deepcopy(q) for q in self.rows if q['grade']==grade]
        if len(bank)<20:raise ValueError('Not enough Free samples for this grade')
        secrets.SystemRandom().shuffle(bank)
        return bank[:20]
    def metadata(self):
        return {'revision':self.revision,'questionCount':len(self.rows),'countsByGrade':dict(Counter(q['grade'] for q in self.rows)),
                'teacherReview':'pending','freeOnly':True,'label':'Mẫu tự biên soạn · chờ giáo viên duyệt'}


def install_game_sources(runtime,package):
    from .group_games import QuestionSource
    runtime.arena=SampleArenaSource(package,'arena-duel-QA')
    runtime.bot=SampleArenaSource(package,'arena-bot-qa')
    previous=runtime.group_games.source.revision
    raw=[{**q,'purpose':'group-games','modes':['capture_flag','animal_race'],'tier':'free','reviewStatus':'self-checked'} for q in runtime.arena.rows]
    runtime.group_games.source=QuestionSource(raw,qa_only=True,revision=runtime.arena.revision)
    runtime.group_games.accepted_source_revisions={previous,runtime.arena.revision}
    runtime.curriculum_samples=True


def trial_content(grade):
    package=loaded_package()
    if not package:return None
    if type(grade) is not int or grade not in range(1,6):raise api.APIError('Chọn lớp từ 1 đến 5.')
    topics={t['id']:t for t in package['topics']};questions=[]
    for q in package['questions']:
        if q['access']!='free' or q['grade']!=grade:continue
        item={'id':q['id'],'revision':q['revision'],'grade':grade,'difficulty':level(q),'prompt':q['stem'],
              'topic':topics[q['topicId']]['title'],'answerKind':'text','responseMode':'choice',
              'options':[o['text'] for o in q['options']],
              'answer':next(o['text'] for o in q['options'] if o['id']==q['correctOptionId']),
              'reviewStatus':'arithmetic_checked','source':'Mẫu tự biên soạn · chờ giáo viên duyệt',
              'purposes':['practice']+([] if q.get('diagram') else ['bot','capture_flag','animal_race']),
              'explanation':'\n'.join(['Định hướng tư duy: '+q['thinking'],'Điểm mấu chốt: '+q['keyPoint'],
                  'Bài giải chi tiết: '+ ' '.join(q['solutionSteps']),'Đáp số: '+q['answerText'],'Thử lại: '+q['check']])}
        if q.get('diagram'):
            diagram=q['diagram'];item['sampleDiagram']={'dataUrl':'data:image/svg+xml;base64,'+base64.b64encode(diagram['svg'].encode('utf-8')).decode(),
                      'alt':diagram['alt'],'width':diagram['width'],'height':diagram['height']}
        questions.append(item)
    first=next(q for q in package['questions'] if q['grade']==grade and q['band']=='free-basic')
    sections=[{'key':k,'title':title,'body':body} for k,title,body in [
        ('thinking','Định hướng tư duy',first['thinking']),('key','Điểm mấu chốt',first['keyPoint']),
        ('detail','Bài giải chi tiết','\n'.join(first['solutionSteps']+['Đáp số: '+first['answerText'],'Thử lại: '+first['check']]))]]
    lesson={'id':first['id'],'revision':first['revision'],'title':topics[first['topicId']]['title'],'prompt':first['stem'],'sections':sections,
            'thinking':sections[0]['body'],'key':sections[1]['body'],'solution':sections[2]['body'],
            'options':[o['text'] for o in first['options']]}
    if first.get('diagram'):
        diagram=first['diagram']
        lesson['sampleDiagram']={'dataUrl':'data:image/svg+xml;base64,'+base64.b64encode(diagram['svg'].encode('utf-8')).decode(),
                                'alt':diagram['alt'],'width':diagram['width'],'height':diagram['height']}
    return {'id':BATCH,'revision':1,'curriculumSamples':True,'grade':grade,'questions':questions,'lesson':lesson}


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Explicitly install a validated localhost sample package. Never seeds at startup.')
    parser.add_argument('package',type=Path)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--scope',choices=['main-free','native'],required=True)
    parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--confirm-local-samples',action='store_true',required=True)
    args=parser.parse_args()
    package=json.loads(args.package.read_text(encoding='utf-8'))
    actual=validate_package(package)
    if actual!=args.expected_sha256:raise ValueError('Package hash differs from reviewed manifest')
    if not args.database.is_file():raise ValueError('Existing, explicitly selected database required')
    with api.connect(args.database,True) as db:
        is_pilot=bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_environment'").fetchone())
        if is_pilot!=(args.scope=='native'):raise ValueError('Database scope does not match requested target')
        result=install(db,package,pilot=is_pilot)
        if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Foreign-key check failed')
    print(json.dumps(result))


if __name__=='__main__':main()
