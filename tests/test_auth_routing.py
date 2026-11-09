import re
import unittest
from pathlib import Path

import yaml


class AuthAuthorizationRoutingTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'hosts/mug/traefik/dynamic/routes.yml'
        self.http = yaml.safe_load(path.read_text())['http']

    def test_authorization_aliases_are_guarded_without_capturing_other_protocol_endpoints(self):
        router = self.http['routers']['jack-auth-authorization']
        pattern, = re.findall(r'PathRegexp\(`([^`]+)`\)', router['rule'])
        for path in ['/oauth/v2/authorize', '/oauth/v2/authorize/', '/oauth%2Fv2%2Fauthorize', '/oauth%2fv2%2fauthorize', '/oauth/v2%2Fauthorize', '/oauth//v2//authorize']:
            with self.subTest(path=path):
                self.assertRegex(path, pattern)
        for path in ['/oauth/v2/token', '/oauth/v2/register', '/oidc/v1/userinfo', '/.well-known/openid-configuration', '/login', '/oauth/v2/authorize-other']:
            with self.subTest(path=path):
                self.assertIsNone(re.fullmatch(pattern, path))
        self.assertEqual(router['service'], 'jack-auth-api')
        self.assertEqual(router['tls'], self.http['routers']['jack-auth-api']['tls'])
        self.assertGreater(router['priority'], self.http['routers']['jack-auth-registration']['priority'])

    def test_body_is_bounded_before_private_policy_with_untrusted_forwarded_headers(self):
        router = self.http['routers']['jack-auth-authorization']
        body, policy = [self.http['middlewares'][name] for name in router['middlewares']]
        self.assertEqual(body['buffering']['maxRequestBodyBytes'], 16384)
        self.assertEqual(body['buffering']['memRequestBodyBytes'], 16384)
        auth = policy['forwardAuth']
        self.assertFalse(auth['trustForwardHeader'])
        self.assertTrue(auth['forwardBody'])
        self.assertEqual(auth['authRequestHeaders'], ['Content-Type'])
        self.assertEqual(auth['address'], 'http://newport.hedgehog-python.ts.net:18086/internal/oidc/authorize-policy')
