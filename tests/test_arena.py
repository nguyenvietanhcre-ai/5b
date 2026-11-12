import time
import unittest
from unittest.mock import patch
from backend.arena import Arena, ArenaError


class ArenaTests(unittest.TestCase):
    def test_question_timeouts_follow_grade_and_actual_question_difficulty(self):
        for grade, expected in [(1, 60), (2, 60), (3, 120), (4, 120), (5, 240)]:
            with self.subTest(grade=grade):
                arena = Arena()
                questions = [{'id':str(i),'text':'Câu thử','answer':'2','options':['1','2'],
                              'difficulty':2 if i==0 else 0,'steps':[]} for i in range(20)]
                with patch.object(arena, '_questions', return_value=questions), patch('backend.arena.time.time', return_value=1000):
                    owner = arena.handle({'action':'create','name':'Chủ phòng','grade':grade})
                    friend = arena.handle({'action':'join','name':'Bạn','grade':grade,'code':owner['code']})
                    arena.handle({**owner,'action':'accept'})
                room = arena.rooms[owner['code']]

                def at(clock, player=owner, action='state', **body):
                    # Both browsers keep polling throughout a long question.
                    for p in room['players'].values():
                        p['seen'] = clock
                    with patch('backend.arena.time.time', return_value=clock):
                        return arena.handle({**player,'action':action,**body})['battle']

                first = at(1003)
                deadline = 1003 + expected
                self.assertEqual(first['deadline'], deadline * 1000)
                self.assertEqual(at(1004, friend)['deadline'], first['deadline'])
                self.assertFalse(at(deadline - 0.01)['resolved'])
                expired = at(deadline, action='answer', index=0, answer='2')
                self.assertTrue(expired['resolved'])
                self.assertEqual(expired['opponentHp'], 100)
                self.assertEqual(at(deadline + 2.99)['index'], 0)
                second = at(deadline + 3)
                self.assertEqual(second['index'], 1)
                self.assertEqual(second['deadline'], (deadline + 3 + (180 if grade==5 else expected)) * 1000)

    def test_long_match_lifetime_covers_all_rounds(self):
        arena = Arena()
        questions = [{'id':str(i),'text':'Câu thử','answer':'2','options':['1','2'],
                      'difficulty':2,'steps':[]} for i in range(20)]
        with patch.object(arena, '_questions', return_value=questions), patch('backend.arena.time.time', return_value=1000):
            owner = arena.handle({'action':'create','name':'Chủ phòng','grade':5})
            friend = arena.handle({'action':'join','name':'Bạn','grade':5,'code':owner['code']})
            arena.handle({**owner,'action':'accept'})
        room = arena.rooms[owner['code']]
        self.assertEqual(room['expiresAt'] - room['created'], 20 * (240 + 3) + 300 + 30 + 3 + 300)
        room.update(status='playing', deadline=3240)
        for player in room['players'].values():
            player['seen'] = 3000
        with patch('backend.arena.time.time', return_value=3000):
            self.assertEqual(arena.handle({**owner,'action':'state'})['status'], 'playing')

    def setUp(self):
        self.arena = Arena()
        self.owner = self.arena.handle({"action": "create", "name": "Minh Anh", "grade": 5})
        self.friend = self.arena.handle({"action": "join", "name": "Gia Huy", "grade": 5,
                                         "code": self.owner["code"]})
        self.call(self.owner,'accept')
        self.arena.rooms[self.owner['code']]['readyAt']=time.time()-1
        self.call(self.owner)

    def advance(self):
        self.arena.rooms[self.owner['code']]['nextAt']=time.time()-1
        return self.call(self.owner)

    def call(self, player, action="state", **values):
        return self.arena.handle({**player, "action": action, **values})

    def timed_pair(self):
        arena = Arena()
        questions = [{'id':str(i),'text':'Câu thử','answer':'2','options':['1','2'],
                      'difficulty':2 if i == 0 else 0,'steps':[]} for i in range(20)]
        with patch.object(arena, '_questions', return_value=questions), patch('backend.arena.time.time', return_value=1000):
            owner = arena.handle({'action':'create','name':'Chủ phòng','grade':5})
            friend = arena.handle({'action':'join','name':'Bạn','grade':5,'code':owner['code']})
        room = arena.rooms[owner['code']]

        def at(clock, player=owner, action='state', **body):
            with patch('backend.arena.time.time', return_value=clock):
                return arena.handle({**player,'action':action,**body})

        return arena, owner, friend, room, at

    def test_accept_starts_after_three_seconds_and_rejects_early_answers(self):
        _, owner, _, room, at = self.timed_pair()
        preparing = at(1000, action='accept')
        self.assertEqual(preparing['readyAt'], 1003000)
        early = at(1002.999, action='answer', index=0, answer='2')
        self.assertEqual(early['status'], 'preparing')
        self.assertIsNone(room['players'][owner['token']]['answer'])
        started = at(1003)['battle']
        self.assertEqual(started['deadline'], 1243000)
        self.assertEqual(started['roundOutcome'], 'waiting')
        self.assertIsNone(started['roundReason'])

    def test_both_idle_players_advance_every_timeout_and_finish_without_reward(self):
        _, _, friend, room, at = self.timed_pair()
        at(1000, action='accept')
        at(1003)
        at(1003, friend)
        started = 1003
        for index in range(20):
            duration = 240 if index == 0 else 180
            deadline = started + duration
            # Neither browser has to submit or poll while reading a question.
            self.assertFalse(at(deadline - 0.001)['battle']['resolved'])
            expired = at(deadline)['battle']
            self.assertEqual(expired['index'], index)
            self.assertTrue(expired['resolved'])
            self.assertEqual(expired['roundOutcome'], 'timeout')
            self.assertEqual(expired['roundReason'], 'timeout')
            self.assertEqual(expired['nextAt'], (deadline + 3) * 1000)
            self.assertEqual((expired['hp'], expired['opponentHp']), (100, 100))
            self.assertEqual(at(deadline + 2.999, friend)['battle']['index'], index)
            next_state = at(deadline + 3)
            if index == 19:
                self.assertEqual(next_state['status'], 'finished')
                self.assertEqual(next_state['result']['outcome'], 'draw')
                self.assertEqual(next_state['result']['points'], 0)
                self.assertEqual(next_state['result']['rounds'], 20)
            else:
                self.assertEqual(next_state['battle']['index'], index + 1)
                self.assertFalse(next_state['battle']['resolved'])
                self.assertEqual(next_state['battle']['roundOutcome'], 'waiting')
                self.assertIsNone(next_state['battle']['roundReason'])
            started = deadline + 3
        self.assertFalse(room['interrupted'])

    def test_long_question_allows_throttled_peer_and_resumed_requester(self):
        _, _, friend, room, at = self.timed_pair()
        at(1000, action='accept')
        at(1003)
        at(1003, friend)
        self.assertEqual(room['disconnectAfter'], 300)
        for clock in (1064, 1124, 1184):
            self.assertEqual(at(clock)['status'], 'playing')
        self.assertTrue(at(1243)['battle']['resolved'])
        self.assertEqual(at(1246, friend)['battle']['index'], 1)

        # The returning browser's request renews its own presence before the
        # old last-seen value is considered, even beyond the grace period.
        _, _, friend, room, at = self.timed_pair()
        at(1000, action='accept')
        at(1003)
        at(1003, friend)
        for clock in (1064, 1124, 1184, 1243, 1303):
            self.assertEqual(at(clock)['status'], 'playing')
        returned = at(1303.001, friend)
        self.assertEqual(returned['status'], 'playing')
        self.assertEqual(room['players'][friend['token']]['seen'], 1303.001)
        self.assertFalse(room['interrupted'])

    def test_gone_opponent_interrupts_after_bounded_grace_without_reward(self):
        _, _, friend, room, at = self.timed_pair()
        at(1000, action='accept')
        at(1003)
        at(1003, friend)
        for clock in (1063, 1123, 1183, 1243, 1303):
            self.assertEqual(at(clock)['status'], 'playing')
        result = at(1303.001)['result']
        self.assertEqual(result['outcome'], 'left')
        self.assertEqual(result['points'], 0)
        self.assertTrue(room['interrupted'])
        self.assertEqual(at(1304, friend)['result']['points'], 0)

    def test_expired_abandoned_room_cannot_be_revived_by_returning_player(self):
        arena, _, _, room, at = self.timed_pair()
        at(1000, action='accept')
        with self.assertRaises(ArenaError) as error:
            at(room['expiresAt'] + 0.001)
        self.assertEqual(error.exception.status, 404)
        self.assertNotIn(room['code'], arena.rooms)

    def test_round_outcomes_distinguish_wrong_opponent_and_timeout(self):
        room = self.arena.rooms[self.owner['code']]
        self.assertEqual(self.call(self.owner)['battle']['roundOutcome'], 'waiting')
        question = room['questions'][0]
        wrong = next(option for option in question['options'] if option != question['answer'])
        answered = self.call(self.owner, 'answer', index=0, answer=wrong)['battle']
        self.assertEqual(answered['roundOutcome'], 'wrong')
        self.assertFalse(answered['resolved'])
        self.assertIsNone(answered['roundReason'])
        correct = self.call(self.friend, 'answer', index=0, answer=question['answer'])['battle']
        self.assertEqual((correct['roundOutcome'], correct['roundReason']), ('correct', 'correct'))
        incorrect = self.call(self.owner)['battle']
        self.assertEqual((incorrect['roundOutcome'], incorrect['roundReason']), ('wrong', 'correct'))
        self.advance()
        question = room['questions'][1]
        self.call(self.owner, 'answer', index=1, answer=question['answer'])
        opponent = self.call(self.friend)['battle']
        self.assertEqual((opponent['roundOutcome'], opponent['roundReason']), ('opponent', 'correct'))
        self.assertNotIn('answer', opponent['questions'][1])
        self.assertNotIn('steps', opponent['questions'][1])
        self.advance()
        question = room['questions'][2]
        wrong = next(option for option in question['options'] if option != question['answer'])
        self.call(self.owner, 'answer', index=2, answer=wrong)
        both_wrong = self.call(self.friend, 'answer', index=2, answer=wrong)['battle']
        self.assertEqual((both_wrong['roundOutcome'], both_wrong['roundReason']), ('wrong', 'both_wrong'))
        self.assertTrue(both_wrong['resolved'])
        self.advance()
        question = room['questions'][3]
        wrong = next(option for option in question['options'] if option != question['answer'])
        self.call(self.owner, 'answer', index=3, answer=wrong)
        room['deadline'] = time.time() - 0.001
        expired = self.call(self.friend)['battle']
        self.assertEqual((expired['roundOutcome'], expired['roundReason']), ('timeout', 'timeout'))
        self.assertEqual(self.call(self.owner)['battle']['roundOutcome'], 'wrong')

    def test_emotes_repeat_after_five_seconds_independently_and_bubbles_last_four(self):
        _, _, friend, _, at = self.timed_pair()
        at(1000, action='accept')
        initial = at(1003)['battle']
        self.assertEqual(initial['emoteAvailableAt'], 0)
        self.assertFalse(initial['emoteUsed'])
        first = at(1003, action='emote', emote=1)['battle']
        self.assertEqual(first['myEmote'], 1)
        self.assertTrue(first['emoteUsed'])
        self.assertEqual(first['emoteAvailableAt'], 1008000)
        other = at(1004, friend, action='emote', emote=2)['battle']
        self.assertEqual((other['myEmote'], other['opponentEmote']), (2, 1))
        self.assertEqual(other['emoteAvailableAt'], 1009000)
        self.assertEqual(at(1006.999)['battle']['myEmote'], 1)
        expired = at(1007)['battle']
        self.assertIsNone(expired['myEmote'])
        self.assertEqual(expired['opponentEmote'], 2)
        blocked = at(1007.999, action='emote', emote=3)['battle']
        self.assertIsNone(blocked['myEmote'])
        self.assertEqual(blocked['emoteAvailableAt'], 1008000)
        self.assertTrue(blocked['emoteUsed'])
        repeated = at(1008, action='emote', emote=4)['battle']
        self.assertEqual(repeated['index'], 0)
        self.assertEqual(repeated['myEmote'], 4)
        self.assertEqual(repeated['emoteAvailableAt'], 1013000)
        self.assertEqual(at(1008, friend)['battle']['emoteAvailableAt'], 1009000)
        self.assertEqual(at(1009, friend, action='emote', emote=5)['battle']['myEmote'], 5)

    def test_emote_cooldown_and_bubble_survive_question_transition(self):
        _, _, _, _, at = self.timed_pair()
        at(1000, action='accept')
        at(1003)
        at(1003, action='emote', emote=1)
        at(1003.5, action='answer', index=0, answer='2')
        next_round = at(1006.5)['battle']
        self.assertEqual(next_round['index'], 1)
        self.assertEqual(next_round['myEmote'], 1)
        self.assertEqual(next_round['emoteAvailableAt'], 1008000)
        self.assertTrue(next_round['emoteUsed'])
        blocked = at(1006.5, action='emote', emote=2)['battle']
        self.assertEqual(blocked['myEmote'], 1)
        self.assertEqual(blocked['emoteAvailableAt'], 1008000)
        self.assertIsNone(at(1007)['battle']['myEmote'])
        available = at(1008)['battle']
        self.assertFalse(available['emoteUsed'])
        self.assertEqual(at(1008, action='emote', emote=2)['battle']['myEmote'], 2)

    def test_invalid_or_early_emotes_do_not_start_or_extend_cooldown(self):
        _, owner, _, room, at = self.timed_pair()
        at(1000, action='accept')
        at(1001, action='emote', emote=1)
        player = room['players'][owner['token']]
        self.assertEqual(player['emoteAvailableAt'], 0)
        at(1003)
        for value in (-1, 10, True, False, 1.0, '1', None):
            with self.subTest(value=value):
                invalid = at(1003, action='emote', emote=value)['battle']
                self.assertIsNone(invalid['myEmote'])
                self.assertEqual(invalid['emoteAvailableAt'], 0)
                self.assertFalse(invalid['emoteUsed'])
        at(1004, action='emote', emote=0)
        at(1005, action='emote', emote=10)
        at(1008.999, action='emote', emote=3)
        self.assertEqual(player['emoteAvailableAt'], 1009)
        self.assertEqual(player['emoteUntil'], 1008)
        invalid_after_wait = at(1009, action='emote', emote='2')['battle']
        self.assertEqual(invalid_after_wait['emoteAvailableAt'], 1009000)
        self.assertFalse(invalid_after_wait['emoteUsed'])
        self.assertIsNone(invalid_after_wait['myEmote'])
        accepted = at(1009, action='emote', emote=2)['battle']
        self.assertEqual(accepted['myEmote'], 2)
        self.assertEqual(accepted['emoteAvailableAt'], 1014000)

    def test_random_spell_draws_once_per_hit_and_is_shared_and_retained(self):
        room = self.arena.rooms[self.owner['code']]
        spells = ['rock', 'vine', 'lightning', 'lightning']
        self.assertIsNone(self.call(self.owner)['battle']['lastAttack'])
        attack_ids = set()
        with patch.object(self.arena.random, 'choice', side_effect=spells) as draw:
            for index, spell in enumerate(spells):
                answer = room['questions'][index]['answer']
                hit = self.call(self.owner, 'answer', index=index, answer=answer)['battle']['lastAttack']
                self.assertEqual(set(hit), {'id', 'spell', 'index', 'attacker'})
                self.assertEqual((hit['spell'], hit['index'], hit['attacker']), (spell, index, 'me'))
                self.assertNotIn(hit['id'], attack_ids)
                attack_ids.add(hit['id'])
                opponent = self.call(self.friend)['battle']['lastAttack']
                self.assertEqual(opponent, {**hit, 'attacker':'opponent'})
                self.assertEqual(self.call(self.owner, 'answer', index=index, answer=answer)['battle']['lastAttack'], hit)
                self.call(self.owner, 'emote', emote=1)
                self.assertEqual(self.call(self.friend)['battle']['lastAttack'], opponent)
                self.assertEqual(draw.call_count, index + 1)
                next_round = self.advance()['battle']
                self.assertEqual(next_round['index'], index + 1)
                self.assertEqual(next_round['lastAttack'], hit)
                # A retry for the previous question cannot choose a new spell.
                self.call(self.friend, 'answer', index=index, answer=answer)
                self.assertEqual(draw.call_count, index + 1)
                # Public metadata is copied instead of exposing the internal
                # participant token or allowing the authoritative spell to change.
                hit['spell'] = 'changed-client-copy'
                self.assertEqual(self.call(self.owner)['battle']['lastAttack']['spell'], spell)
            self.assertEqual(draw.call_count, 4)

    def test_wrong_invalid_timeout_and_polling_never_choose_or_clear_a_spell(self):
        room = self.arena.rooms[self.owner['code']]
        with patch.object(self.arena.random, 'choice', return_value='vine') as draw:
            with self.assertRaises(ArenaError):
                self.call(self.owner, 'answer', index=0, answer='not-an-option')
            question = room['questions'][0]
            wrong = next(option for option in question['options'] if option != question['answer'])
            self.call(self.owner, 'answer', index=0, answer=wrong)
            self.call(self.friend, 'answer', index=0, answer=wrong)
            self.call(self.owner, 'emote', emote=1)
            self.assertIsNone(self.call(self.friend)['battle']['lastAttack'])
            self.advance()
            room['deadline'] = time.time() - 0.001
            self.call(self.friend, 'answer', index=1, answer=room['questions'][1]['answer'])
            self.assertIsNone(self.call(self.owner)['battle']['lastAttack'])
            draw.assert_not_called()
            self.advance()
            hit = self.call(self.owner, 'answer', index=2, answer=room['questions'][2]['answer'])['battle']['lastAttack']
            self.advance()
            room['deadline'] = time.time() - 0.001
            self.call(self.owner)
            self.call(self.friend, 'emote', emote=2)
            self.assertEqual(self.call(self.owner)['battle']['lastAttack'], hit)
            self.assertEqual(draw.call_count, 1)

    def test_final_attack_metadata_survives_missed_poll_and_result_retries(self):
        room = self.arena.rooms[self.owner['code']]
        with patch.object(self.arena.random, 'choice', side_effect=['rock','vine','lightning','rock','vine']) as draw:
            for index in range(5):
                self.call(self.friend, 'answer', index=index, answer=room['questions'][index]['answer'])
                if index < 4:
                    self.advance()
            # The other browser misses the final playing response entirely.
            result = self.advance()['result']
            attack = result['lastAttack']
            self.assertEqual((attack['spell'], attack['index'], attack['attacker']), ('vine', 4, 'opponent'))
            self.assertEqual(result['hp'], 0)
            self.assertEqual(result['outcome'], 'lose')
            winner = self.call(self.friend)['result']
            self.assertEqual(winner['lastAttack'], {**attack, 'attacker':'me'})
            self.assertEqual(winner['outcome'], 'win')
            self.assertEqual(self.call(self.owner)['result']['lastAttack'], attack)
            self.call(self.friend, 'answer', index=4, answer=room['questions'][4]['answer'])
            self.assertEqual(draw.call_count, 5)

    def test_first_correct_wins_round_once_and_retries_do_not_skip(self):
        room = self.arena.rooms[self.owner["code"]]
        answer = room["questions"][0]["answer"]
        self.call(self.owner, "answer", index=0, answer=answer)
        self.call(self.owner, "answer", index=0, answer=answer)
        view = self.call(self.friend)["battle"]
        self.assertEqual(view["hp"], 80)
        self.assertTrue(view["resolved"])
        self.assertNotIn("answer", view["questions"][0])
        self.assertEqual(self.call(self.owner,'next',index=0)['battle']['index'],0)
        self.advance()
        self.call(self.owner, "next", index=0)
        self.call(self.friend, "answer", index=0, answer=answer)
        self.assertEqual(room["index"], 1)
        self.assertEqual(self.call(self.friend)["battle"]["hp"], 80)

    def test_win_and_disconnect_results(self):
        room = self.arena.rooms[self.owner["code"]]
        for index in range(5):
            self.call(self.owner, "answer", index=index, answer=room["questions"][index]["answer"])
            if index < 4:
                self.advance()
        self.advance()
        self.assertEqual(self.call(self.owner)["result"]["points"], 2)
        self.assertEqual(self.call(self.friend)["result"]["points"], -1)
        self.assertEqual(self.call(self.owner)["result"]["points"], 2)

    def test_missing_player_interrupts_match_without_points(self):
        room = self.arena.rooms[self.owner["code"]]
        room["players"][self.friend["token"]]["seen"] = time.time() - room['disconnectAfter'] - 1
        result = self.call(self.owner)["result"]
        self.assertEqual(result["points"], 0)
        self.assertEqual(result["outcome"], "left")

    def test_voluntary_forfeit_is_stable_and_never_rewards_the_opponent(self):
        left = self.call(self.owner, 'leave')['result']
        winner = self.call(self.friend)['result']
        self.assertEqual((left['outcome'], left['points']), ('lose', -1))
        self.assertEqual((winner['outcome'], winner['points']), ('win', 0))
        self.assertFalse(left['completed'])
        self.assertEqual(left['reason'], 'forfeit')
        self.assertEqual(self.call(self.friend, 'leave')['result'], winner)
        self.assertEqual(self.call(self.owner, 'leave')['result'], left)

    def test_leave_does_not_reverse_a_decided_final_round_or_lethal_hit(self):
        room = self.arena.rooms[self.owner['code']]
        room.update(resolved=True, nextAt=time.time() + 3)
        room['players'][self.friend['token']]['hp'] = 0
        winner = self.call(self.owner, 'leave')['result']
        self.assertEqual((winner['outcome'], winner['points']), ('win', 2))
        self.assertTrue(winner['completed'])
        self.assertEqual(self.call(self.friend, 'leave')['result']['outcome'], 'lose')

    def test_final_draw_cannot_be_changed_by_leave_or_stale_peer(self):
        room = self.arena.rooms[self.owner['code']]
        room.update(index=19, resolved=True, nextAt=time.time() + 3)
        room['players'][self.friend['token']]['seen'] -= room['disconnectAfter'] + 1
        result = self.call(self.owner, 'leave')['result']
        self.assertEqual((result['outcome'], result['points']), ('draw', 0))
        self.assertTrue(result['completed'])
        self.assertFalse(room['interrupted'])

    def test_cancelling_preparation_is_free_and_never_becomes_forfeit(self):
        room = self.arena.rooms[self.owner['code']]
        room.update(status='preparing', readyAt=time.time() + 3)
        self.assertEqual(self.call(self.owner, 'leave')['status'], 'cancelled')
        self.assertNotIn('abandonedTokens', room)
        self.assertEqual(self.call(self.friend, 'leave')['status'], 'cancelled')

    def test_private_room_and_token_required(self):
        outsider = self.arena.handle({"action": "quick", "name": "Khách", "grade": 5})
        self.assertNotEqual(outsider["code"], self.owner["code"])
        with self.assertRaises(ArenaError):
            self.call({"code": self.owner["code"], "token": "wrong"})
        self.assertEqual(len(self.arena.rooms[self.owner["code"]]["questions"]), 20)
