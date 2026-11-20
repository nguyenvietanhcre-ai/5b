"""Production HTTP adapter with fresh fixture DB; never uses port8765/live data."""
import http.client
import json
import threading
import unittest
from backend.server import ThreadingHTTPServer,Handler
from backend.local_test_games import NativeLocalTestGames
from test_local_test_games import NativeLocalTestGamesTests

class QuietHandler(Handler):
    def log_message(self,*args):pass

class GroupRoomHTTPTests(unittest.TestCase):
    setUp=NativeLocalTestGamesTests.setUp
    tearDown=NativeLocalTestGamesTests.tearDown
    actor=NativeLocalTestGamesTests.actor

    def test_private_public_owned_claim_and_csrf_over_http(self):
        clients=[self.actor() for _ in range(3)]
        server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        port=server.server_address[1]
        server.database_path=self.path;server.arena=self.server.arena
        server.native_python_backend=True;server.real_accounts=True;server.review_upgrades=False
        server.local_test_games=NativeLocalTestGames({port})
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def call(client,path,body=None,bad_csrf=False):
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            headers={'Host':f'127.0.0.1:{port}','Origin':f'http://127.0.0.1:{port}',
                     'Cookie':client.headers['Cookie'],'X-CSRF-Token':'bad' if bad_csrf else client.csrf}
            if body is not None:headers['Content-Type']='application/json'
            try:
                connection.request('GET' if body is None else 'POST','/api/v1/'+path,
                                   None if body is None else json.dumps(body),headers)
                response=connection.getresponse();return response.status,json.loads(response.read())
            finally:connection.close()
        try:
            code,private=call(clients[0],'group-games/rooms',{'mode':'capture_flag','public':False,'requestKey':'http-private-001'})
            self.assertEqual(code,200);self.assertIs(private['room']['public'],False)
            code,public=call(clients[1],'group-games/rooms',{'mode':'capture_flag','public':True,'requestKey':'http-public-001'})
            self.assertEqual(code,200);self.assertIs(public['room']['public'],True)
            code,listed=call(clients[2],'group-games/rooms?mode=capture_flag')
            self.assertEqual(code,200);self.assertEqual({r['id'] for r in listed['rooms']},{public['room']['id']})
            self.assertEqual(call(clients[2],'group-games/rooms/'+private['room']['id'])[0],403)
            code,owned=call(clients[0],'game-claim');self.assertEqual(code,200)
            self.assertEqual(owned['claim']['roomId'],private['room']['id'])
            self.assertEqual(call(clients[2],'game-claim')[1]['claim'],None)
            self.assertEqual(call(clients[2],'group-games/join',{'code':private['room']['code'],'requestKey':'http-bad-csrf-001'},True)[0],403)
        finally:server.shutdown();server.server_close();worker.join(5)
