import http.client
import json
import tempfile
import threading
import unittest
from webapp.runtime import LocalServer,Store,integer

class Stub:
    def state(self):return {'local':True}
    def action(self,body):return {'echo':body.get('value')}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.server=LocalServer(('127.0.0.1',0),Stub())
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,path='/',method='GET',body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        h={'Host':f'127.0.0.1:{self.server.server_port}',**(headers or {})}
        con.request(method,path,body,h);response=con.getresponse();raw=response.read();result=(response.status,dict(response.getheaders()),raw);con.close();return result
    def test_root_and_static_headers(self):
        status,headers,raw=self.request();self.assertEqual(status,200);self.assertIn(self.server.token.encode(),raw)
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff');self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
    def test_requires_token_and_rejects_rebinding(self):
        self.assertEqual(self.request('/api/state')[0],403)
        self.assertEqual(self.request('/',headers={'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request('/api/state',headers={'X-Workspace-Token':self.server.token})[0],200)
    def test_cross_origin_write_rejected_even_with_token(self):
        h={'Content-Type':'application/json','X-Workspace-Token':self.server.token,'Origin':'https://other.example'}
        self.assertEqual(self.request('/api/action','POST','{}',h)[0],403)
    def test_valid_write_and_body_limit(self):
        h={'Content-Type':'application/json','X-Workspace-Token':self.server.token}
        status,_,raw=self.request('/api/action','POST',json.dumps({'value':'<script>'}),h)
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['echo'],'<script>')
        self.assertEqual(self.request('/api/action','POST','{}',{**h,'Content-Length':'5000000'})[0],413)
    def test_path_traversal_is_not_served(self):self.assertEqual(self.request('/../app.py')[0],404)
    def test_integer_rejects_bool_and_fraction(self):
        for value in [True,'1.5',1.5]:
            with self.assertRaises(ValueError):integer(value,'Count')
        self.assertEqual(integer('12','Count'),12)

class StoreTests(unittest.TestCase):
    def test_persistence_and_parameterized_identifier(self):
        with tempfile.TemporaryDirectory() as d:
            one=Store(d);one.save('finding',{'id':'abc','title':'test'})
            two=Store(d);self.assertEqual(two.get('finding','abc')['title'],'test')
            with self.assertRaises(ValueError):two.get('finding',"' OR 1=1 --")
            two.delete('finding','abc');self.assertEqual(one.all('finding'),[])
