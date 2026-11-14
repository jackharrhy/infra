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
        self.assertEqual(router['rule'], 'Host(`pi.jackharrhy.dev`)')
        self.assertEqual(router['tls']['certResolver'], 'newportdns')
        self.assertEqual(router['tls']['domains'], [
            {'main': 'pi.jackharrhy.dev', 'sans': ['*.pi.jackharrhy.dev']}])
        self.assertEqual(http['services']['pi']['loadBalancer'], {
            'passHostHeader': True, 'servers': [{'url': 'http://127.0.0.1:8788'}]})
        self.assertEqual(http['middlewares']['pi-proxy-marker']['headers']['customRequestHeaders'],
                         {'X-P2-Proxy-Secret': '1'})

    def test_named_previews_are_opt_in_private_fixed_upstreams(self):
        http = yaml.safe_load((ROOT / 'hosts/newport/traefik/dynamic/routes.yml').read_text())['http']
        previews = {
            'alderpoint-preview': ('alderpoint', 5173),
            'alderpoint-preview-api': ('alderpoint-api', 54321),
            '4orm-preview': ('4orm', 18954),
            'wonder-site': ('wonder', 18810),
        }
        for name, (host, port) in previews.items():
            with self.subTest(name=name):
                router = http['routers'][name]
                self.assertEqual(router['rule'], f'Host(`{host}.pi.jackharrhy.dev`)')
                self.assertEqual(router['entryPoints'], ['pitailnet'])
                self.assertEqual(router.get('middlewares', []), [])
                self.assertIn('tls', router)
                self.assertEqual(http['services'][router['service']]['loadBalancer'], {
                    'passHostHeader': True, 'servers': [{'url': f'http://127.0.0.1:{port}'}]})
        private_rules = {r['rule'] for r in http['routers'].values()
                         if 'pitailnet' in r.get('entryPoints', [])}
        self.assertEqual(private_rules, {
            'Host(`pi.jackharrhy.dev`)',
            'Host(`alderpoint.pi.jackharrhy.dev`)',
            'Host(`alderpoint-api.pi.jackharrhy.dev`)',
            'Host(`4orm.pi.jackharrhy.dev`)',
            'Host(`wonder.pi.jackharrhy.dev`)',
            'Host(`browse.pi.jackharrhy.dev`) && Path(`/mcp`)',
        })
        for router in http['routers'].values():
            if 'pitailnet' in router.get('entryPoints', []):
                self.assertNotIn('HostRegexp', router['rule'])

    def test_wonder_serves_only_built_static_releases(self):
        compose = yaml.safe_load((ROOT / 'hosts/newport/compose.yml').read_text())
        service = compose['services']['wonder-site']
        self.assertTrue(service['read_only'])
        self.assertEqual(service['user'], '101:101')
        self.assertEqual(service['ports'], ['127.0.0.1:18810:8080'])
        self.assertIn('/mnt/terrabud/websites/pi-wonder:/srv/site:ro', service['volumes'])
        self.assertTrue(all('/repos/' not in v for v in service['volumes']))
        nginx = (ROOT / 'hosts/newport/wonder/nginx.conf').read_text()
        self.assertIn('root /srv/site/current;', nginx)
        self.assertIn('autoindex off;', nginx)
        self.assertIn('try_files $uri $uri/ =404;', nginx)
        self.assertIn('limit_except GET HEAD', nginx)

    def test_browse_adapter_is_authenticated_private_and_not_raw_cdp(self):
        http = yaml.safe_load((ROOT / 'hosts/newport/traefik/dynamic/routes.yml').read_text())['http']
        router = http['routers']['browse-mcp']
        self.assertEqual(router['entryPoints'], ['pitailnet'])
        self.assertEqual(router['rule'], 'Host(`browse.pi.jackharrhy.dev`) && Path(`/mcp`)')
        self.assertNotIn('middlewares', router)
        self.assertEqual(http['services']['browse-mcp']['loadBalancer']['servers'],
                         [{'url': 'http://127.0.0.1:19989'}])
        unit = (ROOT / 'hosts/newport/browse/browse-mcp.service').read_text()
        self.assertIn('--host 127.0.0.1 --port 19989', unit)
        self.assertIn('--apiKeyFile %h/.local/share/browse/mcp-api-key', unit)
        self.assertIn('--stateful', unit)
        self.assertNotIn('--oauth2Bearer', unit)
        self.assertNotIn('--cors', unit)
        self.assertIn('--logLevel none', unit)
        launcher = (ROOT / 'hosts/newport/browse/browse').read_text()
        self.assertIn('OPENCODE_BROWSER_AUTO_UPDATE=off', launcher)
        self.assertIn('browse-runtime-v0.0.16', launcher)
        compose = yaml.safe_load((ROOT / 'hosts/newport/compose.yml').read_text())
        executor = compose['services']['executor']
        self.assertEqual(executor['environment']['EXECUTOR_APPS_ALLOW_PRIVATE_FETCH'], 'true')
        self.assertEqual(executor['environment']['SSO_ONLY'], 'true')
        self.assertEqual(executor['image'], 'local/executor:2.0.0-beta.41-auth-only.1')

    def test_temporary_auth_fixture_is_not_permanent_configuration(self):
        http = yaml.safe_load((ROOT / 'hosts/newport/traefik/dynamic/routes.yml').read_text())['http']
        self.assertNotIn('auth-preview', http['routers'])
        self.assertNotIn('auth-preview', http['services'])

    def test_dns_has_no_public_ipv6_and_preserves_acme_challenge(self):
        zone = yaml.safe_load((ROOT / 'dns/zones/jackharrhy.dev.yaml').read_text())
        for name in ['pi', '*.pi']:
            self.assertEqual(zone[name], {'ttl': 300, 'type': 'A', 'value': '100.123.66.70'})
        dns = yaml.safe_load((ROOT / 'dns/config.yaml').read_text())
        self.assertIn('pi-acme', dns['zones']['jackharrhy.dev.']['processors'])
        self.assertEqual(dns['processors']['pi-acme']['rejectlist'], ['_acme-challenge.pi'])
