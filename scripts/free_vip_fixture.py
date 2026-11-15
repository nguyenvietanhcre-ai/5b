"""Synthetic load fixture, never imported by application seed/startup."""
from datetime import date, timedelta
from pathlib import Path

from backend import platform_api as api
from backend.database import initialize, execute_sql
from backend.free_vip_pilot import SCHEMA, clock_window


def initialize_qa(path):
    path = Path(path).resolve()
    # Exclusive claim before normal initialization; never reuse/copy a real DB.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb'):
        pass
    initialize(path)
    api.seed_catalog(path)
    with api.connect(path, True) as db:
        execute_sql(db, SCHEMA)
        topic = db.execute("SELECT id FROM topics WHERE grade_id=5 LIMIT 1").fetchone()[0]
        versions = {}
        for i in range(220):
            key = f'qa-fixture-{i:03}'
            question = db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (5,?,?)',
                                  (topic,key)).lastrowid
            # Mechanical values exercise quota/versions only; not a product question bank.
            answer = str(i+2)
            version = db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,"
                "prompt_json,grading_rule_json,solution_steps_json,hints_json,status,options_json) "
                "VALUES (?,1,1,1,?,?,?,?,'published',?)", (question,
                api.packed([{'type':'text','text':f'QA GIẢ #{i}: {i} + 2 = ?'}]), api.packed({'answer':answer}),
                api.packed([{'type':'text','text':f'QA GIẢ: {i} + 2 = {answer}.'}]), '[]',
                api.packed([answer,str(i+3),str(i+4),str(i+5)]))).lastrowid
            db.execute('INSERT INTO pilot_content VALUES (?,?,?)',(key,question,'free' if i<90 else 'vip'))
            versions[i] = version
        monday = date.fromisoformat(clock_window()[1])
        # Three distinct fixture windows demonstrate the Monday boundary, never a fallback.
        for window, offset in enumerate((-7,0,7)):
            start = monday + timedelta(days=offset)
            end = start + timedelta(days=7)
            for slot in range(1,4):
                set_key = f'qa-g5-{start}-{slot}'
                db.execute('INSERT INTO pilot_sets VALUES (?,5,?,?,?,1)', (set_key,str(start),str(end),slot))
                for pos in range(1,11):
                    i = window*30 + (slot-1)*10 + pos-1
                    db.execute('INSERT INTO pilot_set_items VALUES (?,?,?,?)', (set_key,pos,f'qa-fixture-{i:03}',versions[i]))
    return path
