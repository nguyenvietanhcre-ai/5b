"""Separate synthetic Duel source. Only explicit marker-verified loopback QA.

Never installed into question_versions, group-games, paid practice or fixed
lessons; normal startup and production Worker packaging do not import it.
"""
from copy import deepcopy
import hashlib,json,secrets
from .answers import matches,requires_choice,validate_choices,validate_rule

class ArenaQAQuestionSource:
    purpose='arena-duel-QA'
    qa_only=True
    revision='arena-duel-qa-v1'
    def __init__(self):
        self._questions={}
        for grade in range(1,6):
            bank=[]
            for index in range(20):
                bot=self.purpose=='arena-bot-qa'
                left,right=(120+index*3+grade,grade+2) if bot else (index*2+grade+3,grade+1)
                total=left+right
                prefix='ARENA-BOT-QA' if bot else 'ARENA-DUEL-QA'
                label='CÂU TEST BOT' if bot else 'CÂU TEST ĐẤU TRÍ'
                q={'id':f'{prefix}-G{grade}-{index:02d}-R1','revision':1,'purpose':self.purpose,
                   'grade':grade,'text':f'[{label}] Tính {left} + {right}.',
                   'answer':str(total),'gradingRule':{'answer':str(total),'answerKind':'number'},
                   'answerKind':'number','responseMode':'typed','difficulty':0,
                   'topicTitle':'Bộ câu test riêng cho Đấu trí','sampleLabel':'Dữ liệu test · chưa duyệt học liệu',
                   'inputGuide':{'instruction':'Nhập một đáp số. Câu test riêng cho Đấu trí.'},
                   'steps':[f'{left} + {right} = {total}.']}
                assert int(q['answer'])==left+right and matches(q['answer'],q['gradingRule'])
                validate_rule(q['answer'],'number')
                if index%5==0:
                    answer=f'a: {total}; b: {total+1}'
                    options=[answer,f'a: {left-right}; b: {left+1-right}',f'a: {total+1}; b: {total}',f'a: {total-1}; b: {total}']
                    reasons=['Cộng đúng từng phép tính và giữ đúng nhãn a, b.',
                             'Lấy phép trừ thay cho phép cộng ở cả hai ý.',
                             'Đổi chỗ kết quả của hai phép tính a và b.',
                             'Bỏ bớt một đơn vị khi cộng ở cả hai ý.']
                    validate_choices(answer,options,reasons,['a','b'])
                    q.update(text=f'[{label}] a) Tính {left} + {right}. b) Tính {left+1} + {right}.',
                             answer=answer,responseMode='choice',answerKind='text',answerShape='parts',answerTargets=['a','b'],
                             options=options,
                             gradingRule={'answer':answer,'answerKind':'text','responseType':'choice','answerTargets':['a','b'],'choiceRationales':reasons},
                             steps=[f'a) {left} + {right} = {total}.',f'b) {left+1} + {right} = {total+1}.'])
                    assert requires_choice(q) and sum(option==answer for option in options)==1
                bank.append(q)
            assert len(bank)==20 and len({q['id'] for q in bank})==20
            self._questions[grade]=bank
        self.sha256=hashlib.sha256(json.dumps(self._questions,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def questions(self,grade,difficulty=0,scope='all'):
        if type(grade) is not int or grade not in self._questions:raise ValueError('QA grade must be1–5')
        bank=deepcopy(self._questions[grade]);secrets.SystemRandom().shuffle(bank)
        for question in bank:
            if question['responseMode']=='choice':secrets.SystemRandom().shuffle(question['options'])
        return bank

    def metadata(self):
        return {'qaOnly':True,'status':'qa-only','purpose':self.purpose,'revision':self.revision,'questionCount':20,
                'label':'Bộ câu test riêng cho Đấu trí · chưa duyệt học liệu','sha256':self.sha256}


class ArenaBotQAQuestionSource(ArenaQAQuestionSource):
    purpose='arena-bot-qa'
    revision='arena-bot-qa-v1'
    def metadata(self):
        return {**super().metadata(),'label':'Luyện với bot · Dữ liệu test · Không tính kinh nghiệm/xếp hạng',
                'gradingMode':'client-demo','ranked':False,'xpAward':0}
