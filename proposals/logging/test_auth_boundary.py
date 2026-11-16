"""Synthetic native gateway test. Run only in an isolated loopback sandbox."""
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).parent


class AuthSourceTests(unittest.TestCase):
    def test_no_fallback_or_shared_identity(self):
        config = yaml.safe_load((ROOT / 'vmauth.yaml.example').read_text())
        self.assertEqual(set(config), {'users'})
        self.assertEqual([u['username'] for u in config['users']], ['mug', 'newport', 'query-owner'])
        for user in config['users']:
            self.assertNotIn('default_url', user)
            self.assertNotIn('url_prefix', user)
            for route in user['url_map']:
                self.assertIn('Authorization:', route['headers'])
                self.assertIn('Cookie:', route['headers'])
        central = yaml.safe_load((ROOT / 'central.compose.yaml').read_text())
        self.assertNotIn('ports', central['services']['victorialogs'])
        auth = central['services']['vmauth']
        self.assertIn('-httpInternalListenAddr=127.0.0.1:8426', auth['command'])
        self.assertEqual(auth['ports'], ['127.0.0.1:8427:8427'])


@unittest.skipUnless(os.environ.get('VMAUTH_TEST_BINARY'), 'native vmauth requires isolated sandbox')
class NativeAuthTests(unittest.TestCase):
    def test_writer_query_separation_and_header_removal(self):
        captured = []

        class Backend(BaseHTTPRequestHandler):
            def do_GET(self):
                captured.append((self.path, dict(self.headers)))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'fixture')

            do_POST = do_GET

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Backend)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = yaml.safe_load((ROOT / 'vmauth.yaml.example').read_text())
        for user in config['users']:
            user['password'] = 'synthetic-fixture-only'
            for route in user['url_map']:
                route['url_prefix'] = f'http://127.0.0.1:{server.server_port}/'

        def request(path, user=None, method='GET', password='synthetic-fixture-only'):
            headers = {'Cookie': 'synthetic-cookie', 'AccountID': '99', 'ProjectID': '99'}
            if user:
                value = base64.b64encode(f'{user}:{password}'.encode()).decode()
                headers['Authorization'] = f'Basic {value}'
            req = Request('http://127.0.0.1:18427' + path, headers=headers, method=method)
            try:
                with urlopen(req, timeout=10) as response:
                    return response.status
            except HTTPError as error:
                status = error.code
                error.close()
                return status

        process = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'auth.yaml'
                path.write_text(yaml.safe_dump(config))
                process = subprocess.Popen([
                    os.environ['VMAUTH_TEST_BINARY'], '-auth.config=' + str(path),
                    '-httpListenAddr=127.0.0.1:18427',
                    '-httpInternalListenAddr=127.0.0.1:18426',
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(50):
                    if process.poll() is not None:
                        self.fail('synthetic gateway exited before readiness')
                    try:
                        request('/select/vmui/')
                        break
                    except URLError:
                        time.sleep(0.05)
                else:
                    self.fail('synthetic gateway did not become ready')

                for user in ('mug', 'newport'):
                    self.assertEqual(request('/insert/jsonline?_msg_field=_msg', user, 'POST'), 200)
                    self.assertGreaterEqual(request('/select/vmui/', user), 400)
                self.assertEqual(request('/select/vmui/', 'query-owner'), 200)
                self.assertEqual(request('/select/logsql/query?query=fixture', 'query-owner'), 200)
                self.assertGreaterEqual(request('/insert/jsonline', 'query-owner', 'POST'), 400)
                for user in (None, 'mug', 'query-owner'):
                    for path in ('/metrics', '/flags', '/debug/pprof/', '/-/reload'):
                        with self.subTest(user=user, path=path):
                            self.assertGreaterEqual(request(path, user), 400)
                for path in ('/insert/jsonline/', '/insert/../select/vmui/', '/%73elect/vmui/'):
                    self.assertGreaterEqual(request(path, 'mug'), 400)
                self.assertGreaterEqual(request('/select/vmui/'), 400)
                self.assertGreaterEqual(request('/select/vmui/', 'unknown'), 400)
                self.assertGreaterEqual(request('/select/vmui/', 'query-owner', password='wrong-fixture'), 400)
                self.assertEqual(len(captured), 4)
                self.assertEqual(captured[0][0], '/insert/jsonline?_msg_field=_msg')
                for _, headers in captured:
                    headers = {key.lower(): value for key, value in headers.items()}
                    self.assertNotIn('authorization', headers)
                    self.assertNotIn('cookie', headers)
                    self.assertEqual(headers['accountid'], '0')
                    self.assertEqual(headers['projectid'], '0')
        finally:
            if process:
                process.terminate()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
