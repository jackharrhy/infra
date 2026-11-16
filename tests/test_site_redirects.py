import re
import unittest
from pathlib import Path

import yaml


class SiteRedirectTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'hosts/mug/traefik/dynamic/routes.yml'
        self.http = yaml.safe_load(path.read_text())['http']

    def test_www_has_its_own_exact_https_router(self):
        router = self.http['routers']['jackharrhy-www']
        self.assertEqual(router['rule'], 'Host(`www.jackharrhy.dev`)')
        self.assertEqual(router['entryPoints'], ['websecure'])
        self.assertEqual(router['service'], 'noop@internal')
        self.assertEqual(router['middlewares'], ['jackharrhy-canonical'])
        self.assertEqual(router['tls'], {'certResolver': 'mugresolver'})

    def test_redirect_fixes_origin_and_preserves_path_and_query(self):
        config = self.http['middlewares']['jackharrhy-canonical']['redirectRegex']
        self.assertTrue(config['permanent'])
        pattern = re.compile(config['regex'])
        for origin in ['https://www.jackharrhy.dev', 'https://www.jackharrhy.dev:443', 'http://www.jackharrhy.dev:80']:
            for suffix in ['/', '/deep/path?q=example&next=https%3A%2F%2Fexample.org', '//example.org/?q=a%2Fb']:
                with self.subTest(origin=origin, suffix=suffix):
                    match = pattern.fullmatch(origin + suffix)
                    self.assertIsNotNone(match)
                    target = config['replacement'].replace('${1}', match.group(1))
                    self.assertEqual(target, 'https://jackharrhy.dev' + suffix)
        for origin in ['https://jackharrhy.dev/', 'https://www.jackharrhy.dev.example.org/', 'https://example.org/']:
            self.assertIsNone(pattern.fullmatch(origin))
