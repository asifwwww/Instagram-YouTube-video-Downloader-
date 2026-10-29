"""Mocked API tests; real provider availability is NOT tested."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
HAS_API = all(importlib.util.find_spec(n) for n in ('fastapi', 'httpx'))

@unittest.skipUnless(HAS_API, 'Install requirements-dev.txt to run API tests')
class APITests(unittest.TestCase):
    def setUp(self):
        import app
        from fastapi.testclient import TestClient
        self.app = app
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(app, 'ROOT', Path(self.temp.name)), patch.object(app, 'TOKEN', 'test-secret'), patch.object(app, 'PUBLIC', False), patch.dict(os.environ, {'OPENAI_API_KEY': ''})]
        for p in self.patches: p.start()
        self.client = TestClient(app.app)
        self.client.__enter__()
        self.auth = {'Authorization': 'Bearer test-secret'}
        self.body = {'url': 'https://youtu.be/abcdefghijk', 'action': 'metadata', 'rights_confirmed': True}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_health_and_security_headers(self):
        r = self.client.get('/healthz')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')
        self.assertEqual(r.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("default-src 'self'", r.headers['Content-Security-Policy'])

    def test_static_site(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)

    def test_auth_required(self):
        self.assertEqual(self.client.post('/api/jobs', json=self.body).status_code, 401)
        self.assertEqual(self.client.get('/api/jobs/not-real').status_code, 401)

    def test_permission_and_url_validation(self):
        body = {**self.body, 'rights_confirmed': False}
        self.assertEqual(self.client.post('/api/jobs', json=body, headers=self.auth).status_code, 400)
        body = {**self.body, 'url': 'https://localhost/admin'}
        self.assertEqual(self.client.post('/api/jobs', json=body, headers=self.auth).status_code, 400)

    def test_ai_requires_key(self):
        r = self.client.post('/api/jobs', json={**self.body, 'action': 'seo'}, headers=self.auth)
        self.assertEqual(r.status_code, 400)

    def test_mocked_job_download_and_missing_file(self):
        def fake(jid, payload):
            folder = self.app.ROOT / jid
            folder.mkdir()
            (folder / 'metadata.json').write_text('{"title":"fixture"}')
            with self.app.lock:
                self.app.jobs[jid].update(status='done', finished=time.time(), result={'metadata': {'title': 'fixture'}, 'files': [{'name': 'metadata.json', 'bytes': 19}]})
        with patch.object(self.app, 'process_job', side_effect=fake):
            r = self.client.post('/api/jobs', json=self.body, headers=self.auth)
            self.assertEqual(r.status_code, 202)
            jid = r.json()['id']
            for _ in range(100):
                job = self.client.get('/api/jobs/' + jid, headers=self.auth).json()
                if job['status'] == 'done': break
                time.sleep(0.01)
            self.assertEqual(job['status'], 'done')
            self.assertEqual(self.client.get('/api/files/' + jid + '/metadata.json', headers=self.auth).status_code, 200)
            self.assertEqual(self.client.get('/api/files/' + jid + '/result.json', headers=self.auth).status_code, 404)

    def test_expiry(self):
        jid = 'a' * 32
        self.app.jobs[jid] = {'status': 'error', 'finished': time.time() - self.app.TTL - 5, 'error': 'fixture'}
        self.assertEqual(self.client.get('/api/jobs/' + jid, headers=self.auth).status_code, 404)

    def test_single_job_admission(self):
        self.app.jobs['a'*32] = {'status': 'running'}
        r = self.client.post('/api/jobs', json=self.body, headers=self.auth)
        self.assertEqual(r.status_code, 429)

if __name__ == '__main__': unittest.main()
