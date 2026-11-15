"""Public discovery filters current participants, without changing quick admission."""
import secrets,unittest
import test_local_test_games as native
from backend import platform_api as api
class PublicRoomMembershipTests(unittest.TestCase):
    setUp=native.NativeLocalTestGamesTests.setUp
    tearDown=native.NativeLocalTestGamesTests.tearDown
    actor=native.NativeLocalTestGamesTests.actor
    def duel_list(self,c):return {r['code'] for r in c.call('arena',{'action':'list'})['rooms']}
    def test_duel_host_other_left(self):
        a,b=self.actor(),self.actor();x=a.call('arena',{'action':'quick','scope':'all','requestKey':'list-quick-replay'})
        self.assertNotIn(x['code'],self.duel_list(a));self.assertIn(x['code'],self.duel_list(b))
        y=a.call('arena',{'action':'quick','scope':'all','requestKey':'list-quick-replay'});self.assertEqual(x['code'],y['code'])
        a.call('game-claim',{'action':'leave','claimId':x['gameClaim']['claimId']});self.assertNotIn(x['code'],self.duel_list(b))
    def test_duel_all_seats(self):
        a,b,c=self.actor(),self.actor(),self.actor();x=a.call('arena',{'action':'quick','scope':'all','requestKey':'all-seats-quick'})
        b.call('arena',{'action':'join','code':x['code']});raw=self.server.arena.rooms[x['code']]
        # Defensive waiting snapshot checks joined participant, not only first seat.
        raw['status']='waiting'
        self.assertNotIn(x['code'],self.duel_list(b));self.assertIn(x['code'],self.duel_list(c));self.assertEqual(len(raw['players']),2)
    def group_case(self,mode):
        a,b,c=self.actor(),self.actor(),self.actor()
        def listed(u):return {r['id'] for r in u.call('group-games/rooms?mode='+mode)['rooms']}
        x=a.call('group-games/rooms',{'mode':mode,'requestKey':secrets.token_hex(12)})['room']
        self.assertNotIn(x['id'],listed(a));self.assertIn(x['id'],listed(c))
        b.call('group-games/join',{'code':x['code'],'requestKey':secrets.token_hex(12)})
        self.assertNotIn(x['id'],listed(b));self.assertIn(x['id'],listed(c))
        claim=b.call('game-claim')['claim'];b.call('game-claim',{'action':'leave','claimId':claim['claimId']})
        self.assertIn(x['id'],listed(b));self.assertNotIn(x['id'],listed(a))
        y=b.call('group-games/quick',{'mode':mode,'requestKey':'after-leave-'+mode});self.assertEqual(y['room']['id'],x['id']);self.assertNotIn(x['id'],listed(b))
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM game_claims').fetchone()[0],2)
    def test_capture_membership(self):self.group_case('capture_flag')
    def test_race_membership(self):self.group_case('animal_race')
