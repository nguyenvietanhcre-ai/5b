import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend.database import initialize
from backend.arena import Arena
from backend.platform_api import seed_catalog, connect, academic
from test_platform_api import Client


class MascotIntegrationTests(unittest.TestCase):
    def test_trusted_challenge_stats_and_rank_up_settlement_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            dbpath=Path(directory)/'integration.sqlite3'
            initialize(dbpath)
            seed_catalog(dbpath)
            server=SimpleNamespace(database_path=dbpath,review_upgrades=False,arena=Arena())
            users=[]
            for i,pet,xp in [(0,'sprout',98),(1,'dolphin',120)]:
                client=Client(server)
                session=client.call('auth/register',{'login':'mascot-integration-'+str(i),'password':'Only-QA-Integration-2026','name':'Mầm thử','birthYear':academic()[0]-10})
                client.call('mascot',{'mascot':pet})
                with connect(dbpath,True) as db:
                    db.execute('UPDATE student_companions SET xp=? WHERE student_id=(SELECT id FROM students WHERE account_id=?)',(xp,session['account']['id']))
                users.append(client)
            first,second=users
            settings={'grade':5,'difficulty':0,'scope':'weekly'}
            room=first.call('arena',{'action':'create',**settings})
            join=second.call('arena',{'action':'join','code':room['code'],**settings,'stats':{'mascot':'dog','xp':999999}})
            challenge=first.call('arena',{'action':'state',**room})
            self.assertEqual(challenge['opponentStats']['mascot'],'dolphin')
            self.assertEqual(challenge['opponentStats']['xp'],120)
            self.assertEqual(challenge['opponentGrade'],5)
            self.assertEqual(set(challenge['opponentStats']),{'mascot','xp','level','wins','losses'})
            first.call('arena',{'action':'accept',**room})
            server.arena.rooms[room['code']]['readyAt']=0
            first.call('arena',{'action':'state',**room})
            for index in range(5):
                answer=server.arena.rooms[room['code']]['questions'][index]['answer']
                first.call('arena',{'action':'answer',**room,'index':index,'answer':answer})
                server.arena.rooms[room['code']]['defenseUntil']=time.time()-1
                first.call('arena',{'action':'state',**room})
                server.arena.rooms[room['code']]['nextAt']=0
                result=first.call('arena',{'action':'state',**room})
            self.assertEqual((result['result']['xpBefore'],result['result']['xpAfter']),(98,100))
            cached=first.call('arena',{'action':'state',**room})
            self.assertEqual((cached['result']['xpBefore'],cached['result']['xpAfter']),(98,100))
            self.assertEqual(first.call('session')['state']['points'],100)
