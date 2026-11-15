"""Ten mechanical adapter fixtures, completely separate from authored learning packages."""
from copy import deepcopy
from datetime import date,timedelta


def fixture():
    sources={'questions':[]}; questions=[]
    for i in range(10):
        ck=f'qa.mcq.{i:02}'
        skill=('g5.parts','g5.unit','g5.reverse')[i%3]
        sources['questions'].append({'contentKey':ck,'revision':1,'grade':5,'skillKey':skill,'prompt':f'QA MCQ GIẢ #{i}: {i} + 2 = ?'})
        questions.append({'contentKey':ck,'revision':2,'sourceContentKey':ck,'sourceRevision':1,
            'lineageRelationship':'equivalent','changeReason':'QA mechanical format conversion only',
            'quotaKey':ck,'grade':5,'skillKey':skill,'proposedAccess':'Free' if i<5 else 'VIP',
            'difficultyOriginal':{'value':i+1,'scale':'1-10','reason':'QA fixture only'},'prerequisites':[],
            'responseType':'single-choice','prompt':f'QA MCQ GIẢ #{i}: {i} + 2 = ?',
            'choices':[{'id':c,'text':str(i+j+2)} for j,c in enumerate('ABCD')],
            'correctChoiceId':'A','choiceRationales':{c:'QA correct' if c=='A' else 'QA distractor' for c in 'ABCD'},
            'hints':['QA only hint'],'solutionSteps':[f'QA: {i}+2={i+2}'],'answerExplanation':'QA correct sum',
            'verification':{'status':'self-checked'},'origin':{'kind':'synthetic-fixture'},
            'sourceLocator':{'role':'metadata-only','path':'QA fixture'},
            'reviewStatus':{'stage':'draft-self-checked','independentTeacherApproved':False}})
    package={'schemaVersion':'mcq-draft-v1','packageId':'qa-mcq-fixture','qaOnly':True,'questions':questions}
    manifest={'schemaVersion':'mcq-draft-v1','qaOnly':True,'setKey':'qa.mcq.set', 'grade':5,
        'windowStart':'2026-11-16T00:00:00+07:00','windowEnd':'2026-11-23T00:00:00+07:00',
        'timeZone':'Asia/Saigon','windowEndExclusive':True,
        'orderedContentKeys':[q['contentKey'] for q in questions[:5]],
        'contentRevisions':{q['contentKey']:q['revision'] for q in questions[:5]},
        'vipSupplementContentKeys':[q['contentKey'] for q in questions[5:]],
        'reviewStatus':{'stage':'draft-self-checked','independentTeacherApproved':False}}
    return deepcopy(package),deepcopy(manifest),deepcopy(sources)
