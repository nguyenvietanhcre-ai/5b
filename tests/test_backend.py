import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from backend.content import grade, parse_number
from backend.server import Handler, ThreadingHTTPServer

class GradingTests(unittest.TestCase):
    def test_exam_full_score_fraction(self):
        self.assertEqual(grade("exam", ["<","7/8","36","162","247500"])["score"], 10)
    def test_decimal_comma_and_partial(self):
        self.assertEqual(grade("exam", ["<","0,875","36","","0"])["score"], 4)
    def test_empty_score_zero(self):
        self.assertEqual(grade("exam", [""]*5)["score"], 0)
    def test_interval_boundaries(self):
        for answer, expected in [("2,355",10),("2,35",7.5),("2,36",7.5),("2.359999",10),("2,4",7.5)]:
            with self.subTest(answer=answer):
                self.assertEqual(grade("practice", ["<","=","5,9",answer])["score"], expected)
    def test_invalid_numbers(self):
        for answer in ["","NaN","Infinity","1/0","1/2/3","1e999999999","abc"]:
            with self.subTest(answer=answer):
                self.assertIsNone(parse_number(answer))
    def test_invalid_payloads(self):
        for kind, answers in [("missing",[]),("exam",[]),("exam",[0]*5),("exam",["x"*71]*5),("exam",None)]:
            with self.subTest(kind=kind,answers=answers):
                with self.assertRaises(ValueError):
                    grade(kind, answers)

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1",0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
    def test_health_frontend(self):
        with urlopen(self.base+"/api/health",timeout=5) as response:
            self.assertEqual(json.load(response)["backend"], "python")
        for route, expected in [("/","5BMath"),("/app.js","submitQuiz"),("/styles.css",".hero"),
                                ("/5bmath-logo.svg","5BMath"),("/5bmath-icon.svg","<svg")]:
            with self.subTest(route=route), urlopen(self.base+route,timeout=5) as response:
                if route.endswith(".svg"):
                    self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
                self.assertIn(expected, response.read().decode())
    def test_internal_files_not_served(self):
        for route in ["/README.md","/AGENTS.md","/backend/server.py","/../README.md","/%2e%2e/README.md","/.git/config"]:
            with self.subTest(route=route), self.assertRaises(HTTPError) as error:
                urlopen(self.base+route,timeout=5)
            self.assertEqual(error.exception.code,404)
    def test_grade_api(self):
        payload={"kind":"exam","answers":["<","7/8","36","162","247500"]}
        req=Request(self.base+"/api/grade",json.dumps(payload).encode(),{"Content-Type":"application/json"})
        with urlopen(req,timeout=5) as response:
            result=json.load(response)
        self.assertEqual(result["score"],10)
        self.assertTrue(all(r["correct"] for r in result["results"]))
    def test_bad_payload(self):
        req=Request(self.base+"/api/grade",b"not json",{"Content-Type":"application/json"})
        with self.assertRaises(HTTPError) as error:
            urlopen(req,timeout=5)
        self.assertEqual(error.exception.code,400)

if __name__ == "__main__":
    unittest.main()
