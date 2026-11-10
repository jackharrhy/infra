import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class SonarrConfigTest(unittest.TestCase):
    def test_common_import_view_masks_private_media(self):
        service = yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['sonarr']
        media = [v for v in service['volumes'] if isinstance(v,dict) and v['target'].startswith('/data')]
        self.assertEqual({v['source']:v['target'] for v in media}, {'/mnt/stash/media':'/data'})
        self.assertIn('/data/personal:mode=000,size=64k',service['tmpfs'])
        self.assertTrue(all(v['bind']['create_host_path'] is False for v in media))
        self.assertEqual(service['environment']['PGID'],'65536')
        self.assertEqual(service['ports'],['127.0.0.1:8989:8989'])

    def test_native_backups_protect_tracking_updates(self):
        service = yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['sonarr']
        self.assertEqual(service['image'],'lscr.io/linuxserver/sonarr:latest')
        labels=dict(v.split('=',1) for v in service['labels'])
        self.assertEqual(labels['com.centurylinklabs.watchtower.enable'],'true')
        self.assertEqual(labels['com.centurylinklabs.watchtower.lifecycle.pre-update'],'/bin/sh /infra/backup.sh')
        self.assertEqual(labels['traefik.enable'],'true')
