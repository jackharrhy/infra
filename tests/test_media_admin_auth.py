import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class MediaAdminAuthTest(unittest.TestCase):
    def test_every_media_app_requires_central_auth_including_api_paths(self):
        config = yaml.safe_load((ROOT / 'hosts/newport/compose.yml').read_text())
        for name, port in [('sonarr',8989),('prowlarr',9696),('qbittorrent',8087)]:
            with self.subTest(app=name):
                service = config['services'][name]
                labels = dict(label.split('=',1) for label in service['labels'])
                router = 'traefik.http.routers.' + name
                self.assertEqual(labels.get(router+'.middlewares'), name+'-auth@docker')
                self.assertEqual(labels.get(router+'.rule'), 'Host(`'+name+'.rotund.org`)')
                self.assertEqual(service['ports'][0], f'127.0.0.1:{port}:{port}')
                self.assertFalse(any(p.startswith('100.') for p in service['ports']))
                proxy = config['services'][name+'-auth']
                env = proxy['environment']
                self.assertEqual(env['OAUTH2_PROXY_REDIRECT_URL'], f'https://{name}.rotund.org/oauth2/callback')
                self.assertEqual(env['OAUTH2_PROXY_COOKIE_NAME'], '__Host-media_admin')
                self.assertEqual(env['OAUTH2_PROXY_OIDC_GROUPS_CLAIM'], 'sub')
                self.assertNotIn('OAUTH2_PROXY_COOKIE_DOMAINS', env)
                auth_port = {'sonarr':14181,'prowlarr':14182,'qbittorrent':14183}[name]
                self.assertEqual(proxy['ports'],[f'127.0.0.1:{auth_port}:4180'])
                plabels = dict(label.split('=',1) for label in proxy['labels'])
                address = plabels['traefik.http.middlewares.'+name+'-auth.forwardauth.address']
                self.assertEqual(address, f'http://127.0.0.1:{auth_port}/')
                self.assertEqual(env['OAUTH2_PROXY_UPSTREAMS'], 'static://202')
                self.assertEqual(env['OAUTH2_PROXY_CODE_CHALLENGE_METHOD'], 'S256')
                self.assertEqual(env['OAUTH2_PROXY_INSECURE_OIDC_SKIP_NONCE'], 'false')

    def test_public_edge_relays_only_the_named_apps(self):
        routers = yaml.safe_load((ROOT/'hosts/mug/traefik/dynamic/routes.yml').read_text())['http']['routers']
        for name in ['sonarr','prowlarr','qbittorrent']:
            self.assertEqual(routers.get(name,{}).get('rule'), f'Host(`{name}.rotund.org`)')
            self.assertEqual(routers[name]['service'], 'newport-origin')
            self.assertEqual(routers[name]['entryPoints'], ['websecure'])
