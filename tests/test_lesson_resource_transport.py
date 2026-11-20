"""Bounded transport and download headers for authored lesson documents."""
import io
import json
import unittest
from email.message import Message
from unittest.mock import patch
from backend.server import Handler


class LessonResourceTransportTests(unittest.TestCase):
    def handler(self, endpoint, raw=b'{}', extra=()):
        h=Handler.__new__(Handler)
        h.path=endpoint
        h.headers=Message()
        h.headers['Content-Type']='application/json'
        h.headers['Content-Length']=str(len(raw))
        for key,value in extra:h.headers[key]=value
        h.rfile=io.BytesIO(raw)
        h.server=object()
        h.json_response=lambda status,payload:setattr(h,'result',(status,payload))
        h.respond=lambda status,body,mime,**kwargs:setattr(h,'binary_result',(status,body,mime,kwargs,dict(h.api_headers)))
        return h

    def test_larger_upload_body_is_scoped_to_two_lesson_edit_routes(self):
        raw=json.dumps({'padding':'a'*300000}).encode()
        for route in ('/api/staff/lessons','/api/staff/native-lessons'):
            h=self.handler(route,raw)
            with patch('backend.server.staff_dispatch',return_value=({'saved':True},200)) as dispatch:
                h.platform_request('POST',route)
            self.assertEqual(h.result,(200,{'saved':True}))
            self.assertEqual(len(dispatch.call_args.args[3]['padding']),300000)
        for route in ('/api/staff/users','/api/website/admin/settings'):
            h=self.handler(route,raw)
            h.platform_request('POST',route)
            self.assertEqual(h.result[0],413)

    def test_upload_limit_and_ambiguous_length_rejected_before_read(self):
        for extra in ((('Transfer-Encoding','chunked'),),(('Content-Length','2'),)):
            h=self.handler('/api/staff/lessons',extra=extra)
            h.platform_request('POST','/api/staff/lessons')
            self.assertEqual(h.result[0],400)
            self.assertEqual(h.rfile.tell(),0)
        h=self.handler('/api/staff/lessons')
        h.headers.replace_header('Content-Length',str(8*1024*1024+1))
        h.platform_request('POST','/api/staff/lessons')
        self.assertEqual(h.result[0],413)
        self.assertEqual(h.rfile.tell(),0)

    def test_document_attachment_is_private_and_filename_is_encoded(self):
        h=self.handler('/api/v1/lesson-materials/main/abc/1/'+'a'*32)
        raw=b'%PDF-1.4\nprivate-test\n%%EOF'
        with patch('backend.server.dispatch',return_value=({'_lesson_binary':raw,'mime':'application/pdf','filename':'Tai lieu bé.pdf'},200)):
            h.platform_request('GET',h.path)
        status,body,mime,options,headers=h.binary_result
        self.assertEqual((status,body,mime),(200,raw,'application/pdf'))
        self.assertEqual(options['cache_control'],'private, no-store')
        self.assertIn('attachment;',headers['Content-Disposition'])
        self.assertIn("filename*=UTF-8''Tai%20lieu%20b%C3%A9.pdf",headers['Content-Disposition'])
        self.assertEqual(headers['Content-Security-Policy'],"sandbox; default-src 'none'")

if __name__=='__main__':unittest.main()
