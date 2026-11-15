"""Literal60second Duel boundaries and non-mutating authoritative live ranks."""
import json,unittest
from copy import deepcopy
from unittest.mock import patch
import test_local_test_games as native
from backend import platform_api as api
from backend.arena import question_seconds
from backend.group_games import GroupGames

class DuelSixtyTests(unittest.TestCase):
    setUp=native.NativeLocalTestGamesTests.setUp
    tearDown=native.NativeLocalTestGamesTests.tearDown
    actor=native.NativeLocalTestGamesTests.actor
    def pair(self):
        a,b=self.actor(5),self.actor(5)
        room=a.call('arena',{'action':'create','scope':'all','public':False})
        friend=b.call('arena',{'action':'join','code':room['code']})
        a.call('arena',{'action':'accept',**room});self.clock+=3
        state=a.call('arena',{'action':'state',**room})['battle']
        self.assertEqual(state['deadline']-self.clock*1000,60000)
        return a,b,room,friend,self.server.arena.rooms[room['code']]
    def test_all_grades_all_difficulties_literal60(self):
        for grade in range(1,6):
            for difficulty in range(4):self.assertEqual(question_seconds(grade,difficulty),60)
    def test_actual_deadline_exact60000_rejects_answer(self):
        self.clock=1000
        with patch('backend.arena.time.time',side_effect=lambda:self.clock):
            a,b,r,f,raw=self.pair();self.clock=raw['deadline']
            view=a.call('arena',{'action':'answer',**r,'index':0,'answer':raw['questions'][0]['answer']})['battle']
            self.assertEqual(raw['players'][r['token']]['correct'],0);self.assertTrue(view['resolved'])
            self.assertEqual(view['roundReason'],'timeout');self.assertEqual(view['nextAt'],self.clock*1000+3000)
    def test_59999_correct_keeps_full_defense10_and_replay(self):
        self.clock=1000
        with patch('backend.arena.time.time',side_effect=lambda:self.clock):
            a,b,r,f,raw=self.pair();self.clock=raw['deadline']-.001;answer=raw['questions'][0]['answer']
            a.call('arena',{'action':'answer',**r,'index':0,'answer':answer});defense=raw['defenseUntil']
            self.assertAlmostEqual(defense-self.clock,3)
            self.clock=defense-.001;b.call('arena',{'action':'answer',**f,'index':0,'answer':answer})
            self.assertEqual(raw['damage'],10);self.assertEqual(raw['players'][f['token']]['hp'],90)
            before=deepcopy(raw);a.call('arena',{'action':'answer',**r,'index':0,'answer':answer})
            self.assertEqual(raw['players'][r['token']]['correct'],1);self.assertEqual(raw['damage'],before['damage'])
    def test_59999_correct_exact_defense_boundary20(self):
        self.clock=1000
        with patch('backend.arena.time.time',side_effect=lambda:self.clock):
            a,b,r,f,raw=self.pair();self.clock=raw['deadline']-.001;answer=raw['questions'][0]['answer']
            a.call('arena',{'action':'answer',**r,'index':0,'answer':answer});self.clock=raw['defenseUntil']
            b.call('arena',{'action':'answer',**f,'index':0,'answer':answer})
            self.assertEqual(raw['damage'],20);self.assertEqual(raw['players'][f['token']]['hp'],80)
            self.assertEqual(raw['nextAt'],self.clock+3)
    def test_bot_bank_and_claim_lease_derive60_no_quota_change(self):
        c=self.actor(5);self.server.game_claim_clock=lambda:1000000
        out=c.call('bot/start',{'scope':'all','requestKey':'polish-sixty-bot'})
        self.assertEqual(len(out['questions']),20);self.assertEqual(out['botRules']['level'],1)
        with api.connect(self.path) as db:
            row=db.execute('SELECT * FROM game_claims WHERE student_id=?',(c.sid,)).fetchone();data=json.loads(row['payload_json'])
            self.assertEqual(data['idleGraceMs'],120000);self.assertEqual(row['expires_at'],1120000)
            self.assertEqual(data['hardExpiresAt'],1000000+5000+20*63000+120000)
            self.assertEqual(db.execute('SELECT count(*) FROM daily_usage WHERE student_id=?',(c.sid,)).fetchone()[0],1)

class LiveRankTests(unittest.TestCase):
    def room(self):
        players=[{'studentId':i+1,'name':'Mầm Xanh','mascot':'dog','xp':0,'seat':i,'steps':2,'correct':2,'totalTimeMs':200,'lastStepAt':10,'answered':False,'answerCorrect':None,'forfeited':False} for i in range(5)]
        return {'id':'x','code':'ABCDEFGH','mode':'capture_flag','grade':5,'status':'playing','createdAt':0,'round':1,'players':players,'questions':[{'id':'q','revision':1,'text':'Test','responseMode':'typed'}],'rankings':[]}
    def test_active_ties_progress_forfeit_and_seat_array_stable(self):
        room=self.room();room['players'][0]['lastStepAt']=20;room['players'][3]['correct']=3;room['players'][4].update(correct=5,forfeited=True)
        original=deepcopy(room);view=GroupGames.view(room,1,100)
        self.assertEqual([p['studentId'] for p in view['players']],[1,2,3,4,5]);self.assertEqual([p['liveRank'] for p in view['players']],[4,2,3,1,5]);self.assertEqual(room,original)
        room['players'][2].update(correct=4,steps=4)
        self.assertEqual(GroupGames.view(room,1,100)['players'][2]['liveRank'],1)
    def test_finished_uses_persisted_winner_rank_over_cumulative_time(self):
        room=self.room();room['status']='finished';room['players'][0].update(correct=5,steps=5,totalTimeMs=250,lastStepAt=100);room['players'][1].update(correct=5,steps=5,totalTimeMs=200,lastStepAt=110)
        room['rankings']=[{'studentId':i+1,'rank':i+1,'points':0,'correct':p['correct'],'totalTimeMs':p['totalTimeMs']} for i,p in enumerate(room['players'])]
        original=deepcopy(room);view=GroupGames.view(room,1,100)
        self.assertEqual(view['players'][0]['liveRank'],1);self.assertEqual(view['players'][1]['liveRank'],2);self.assertEqual(room,original)
