"""Explicit practice opponents, persisted server schedules, never ranked rewards."""
import secrets
from .group_games import GroupGames,request_key,fail,PLAYERS,TARGET,ROUND_MS,BREAK_MS,ACTIVE
from . import platform_api as api

class BotGroupGames(GroupGames):
    def __init__(self,*args,rng=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.rng=rng or secrets.SystemRandom()
    def catalogue(self,grade):
        return {**super().catalogue(grade),'playModes':['human','bot'],
            'botRules':{'humanPlayers':1,'botPlayers':4,'ranked':False,'xpAward':0,
                'answerWindowStartSeconds':42,'answerWindowEndSeconds':60,
                'correctProbability':0.5,'humanAnswer':'settle-persisted-plans-immediately','timingMode':'accelerated-planned','intermissionSeconds':3}}

    @staticmethod
    def _is_bot_room(room):return room.get('playMode')=='bot'

    @staticmethod
    def _signature(action,body):
        # Old human request signatures remain byte-compatible for reconnects.
        if body.get('playMode','human')=='human':return GroupGames._signature(action,body)
        return GroupGames._signature(action+':bot',body)

    def enter(self,db,session,body,action,grade):
        play_mode=body.get('playMode','human')
        if play_mode not in ('human','bot'):fail('Chế độ chơi không hợp lệ.')
        if play_mode!='bot':return super().enter(db,session,body,action,grade)
        if action!='create':fail('Phòng BOT chỉ dành cho học sinh đã tạo phòng.',403)
        view=super().enter(db,session,body,action,grade)
        room=self._load(db,view['id'])
        if room.get('playMode')=='bot':return self.view(room,session['student_id'],self.clock())
        # super entered exactly one real, authenticated member; synthetic IDs
        # never enter accounts/students/companions or reward foreign keys.
        assert room['status']=='waiting' and len(room['players'])==1
        room.update(playMode='bot',ranked=False)
        for seat,mascot in enumerate(('dog','cat','rabbit','sprout'),1):
            room['players'].append({'studentId':-seat,'name':'BOT '+str(seat),'isBot':True,
                'mascot':mascot,'xp':0,'seat':seat,'steps':0,'correct':0,'totalTimeMs':0,
                'lastStepAt':room['createdAt'],'answered':False,'answerCorrect':None,'forfeited':False})
        self._start_round(room,self.clock());self._save(db,room,self.clock())
        return self.view(room,session['student_id'],self.clock())

    def _start_round(self,room,start):
        super()._start_round(room,start)
        if self._is_bot_room(room):
            room['lastRoundReason']=None
            for p in room['players']:
                if p.get('isBot'):
                    p['botAt']=start+self.rng.randrange(42_000,60_000)
                    p['botPlannedCorrect']=self.rng.random()<0.5

    def _bot_answer(self,room,player,at):
        if player['answered']:return
        correct=player['botPlannedCorrect']
        player.update(answered=True,answerCorrect=correct)
        if correct:
            player['lastStepAt']=at;player['correct']+=1;player['steps']=player['correct']
        player['totalTimeMs']+=min(ROUND_MS,max(0,at-room['startedAt']))

    def _settle_round(self,db,room,at):
        winners=[p for p in room['players'] if p['steps']>=TARGET]
        if winners:
            winner=min(winners,key=lambda p:(p['lastStepAt'],p['seat']))
            self._finish(db,room,at,'target_reached',winner['studentId'])
        elif all(p['answered'] or p['forfeited'] for p in room['players']):
            self._account_time(room,at);room.update(status='intermission',nextAt=at+BREAK_MS)

    def _tick(self,db,room,now):
        if not self._is_bot_room(room):return super()._tick(db,room,now)
        while True:
            if room['status']=='playing':
                pending=sorted((p for p in room['players'] if p.get('isBot') and not p['answered']),key=lambda p:(p['botAt'],p['seat']))
                if pending and pending[0]['botAt']<=now and pending[0]['botAt']<room['deadline']:
                    p=pending[0];at=p['botAt'];self._bot_answer(room,p,at);self._settle_round(db,room,at);continue
                if now>=room['deadline']:
                    self._account_time(room,room['deadline']);room.update(status='intermission',nextAt=room['deadline']+BREAK_MS);continue
            elif room['status']=='intermission' and now>=room['nextAt']:
                if room['round']>=len(room['questions']):self._finish(db,room,room['nextAt'],'source_exhausted');break
                self._start_round(room,room['nextAt']);continue
            break
        self._save(db,room,now)

    def mutate(self,db,session,rid,body,action):
        initial=self._load(db,rid)
        if not self._is_bot_room(initial):return super().mutate(db,session,rid,body,action)
        sid=session['student_id'];key=request_key(body);signature=self._signature(action+':'+rid,body)
        replay=self._replay(db,sid,key,signature)
        # In bot practice, leaving the only human cancels the whole practice.
        if action=='leave' and not replay:
            self._member(initial,sid);self._tick(db,initial,self.clock())
            if initial['status'] in ACTIVE:
                self._member(initial,sid)['forfeited']=True
                self._finish(db,initial,self.clock(),'cancelled')
            self._remember(db,sid,key,signature,rid)
            return self.view(initial,sid,self.clock())
        result=super().mutate(db,session,rid,body,action)
        if action!='answer' or replay:return result
        room=self._load(db,rid);player=self._member(room,sid)
        if room['status'] in ('playing','intermission') and player['answered']:
            at=self.clock()
            for bot in room['players']:
                if bot.get('isBot'):self._bot_answer(room,bot,bot['botAt'])
            room['lastRoundReason']='human_answer_planned_bots'
            self._settle_round(db,room,at);self._save(db,room,at)
        return self.view(room,sid,self.clock())

    def _finish(self,db,room,now,reason,winner=None):
        if not self._is_bot_room(room):return super()._finish(db,room,now,reason,winner)
        if room['status']=='playing':self._account_time(room,now)
        room.update(status='finished',endReason=reason,winnerId=winner,finishedAt=now,nextAt=None)
        ranked=sorted(room['players'],key=lambda p:(p['studentId']!=winner if winner is not None else False,
            p['forfeited'],-p['correct'],p['totalTimeMs'],p['lastStepAt'],p['seat']))
        room['rankings']=[{'studentId':p['studentId'],'rank':n,'points':0,'correct':p['correct'],'totalTimeMs':p['totalTimeMs']} for n,p in enumerate(ranked,1)]
        self._save(db,room,now) # deliberately no ledger or XP mutation

    @staticmethod
    def view(room,sid,now):
        public=GroupGames.view(room,sid,now)
        bot_room=room.get('playMode')=='bot'
        public.update(playMode='bot' if bot_room else 'human',ranked=not bot_room,
            rewardNotice='Luyện với BOT · Không tính kinh nghiệm hoặc bảng xếp hạng.' if bot_room else '',
            botTimingMode='accelerated-planned' if bot_room else None,
            botSimulationNotice='BOT được chốt theo kết quả đã lập lịch; thời gian BOT là thời gian mô phỏng trong 18 giây cuối câu, không phải thời gian chờ thực tế.' if bot_room else '',
            lastRoundReason=room.get('lastRoundReason'))
        for player in public['players']:
            raw=next(p for p in room['players'] if p['studentId']==player['studentId'])
            player['isBot']=raw.get('isBot',False)
            # Outcome only after that BOT has answered this round. Never expose
            # its scheduled time, future plan, chosen value or another human.
            if player['isBot'] and raw['answered']:
                player['answerCorrect']=raw['answerCorrect']
        for row in public['rankings']:row['isBot']=next(p.get('isBot',False) for p in room['players'] if p['studentId']==row['studentId'])
        return public
