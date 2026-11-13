import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PiRoutingTests(unittest.TestCase):
    def test_private_listener_and_auth_proxy_contract(self):
        compose = yaml.safe_load((ROOT / 'hosts/newport/compose.yml').read_text())
        args = compose['services']['traefik']['command']
        self.assertIn('--entrypoints.pitailnet.address=100.123.66.70:443', args)
        self.assertIn('--entrypoints.websecure.address=192.168.2.30:443', args)
        self.assertNotIn('--entrypoints.websecure.address=:443', args)
        self.assertIn('--entrypoints.web.asdefault=true', args)
        self.assertIn('--entrypoints.websecure.asdefault=true', args)
        self.assertFalse(any('pitailnet.forwardedheaders' in a for a in args))
        http = yaml.safe_load((ROOT / 'hosts/newport/traefik/dynamic/routes.yml').read_text())['http']
        router = http['routers']['pi']
        self.assertEqual(router['entryPoints'], ['pitailnet'])
        self.assertEqual(router['tls']['certResolver'], 'newportdns')
        self.assertEqual(http['services']['pi']['loadBalancer'], {
            'passHostHeader': True, 'servers': [{'url': 'http://127.0.0.1:8788'}]})
        self.assertEqual(http['middlewares']['pi-proxy-marker']['headers']['customRequestHeaders'],
                         {'X-P2-Proxy-Secret': '1'})

    def test_dns_has_no_public_ipv6_and_preserves_acme_challenge(self):
        zone = yaml.safe_load((ROOT / 'dns/zones/jackharrhy.dev.yaml').read_text())
        self.assertEqual(zone['pi'], {'ttl': 300, 'type': 'A', 'value': '100.123.66.70'})
        dns = yaml.safe_load((ROOT / 'dns/config.yaml').read_text())
        self.assertIn('pi-acme', dns['zones']['jackharrhy.dev.']['processors'])
        self.assertEqual(dns['processors']['pi-acme']['rejectlist'], ['_acme-challenge.pi'])
