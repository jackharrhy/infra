import unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

class AcquisitionConfigTest(unittest.TestCase):
    def test_qbittorrent_only_sees_torrent_payloads_and_private_state(self):
        s=yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['qbittorrent']
        media=[v for v in s['volumes']if isinstance(v,dict)and v['target'].startswith('/data')]
        self.assertEqual([(v['source'],v['target'])for v in media],[('/mnt/stash/media/downloads/torrents','/data/downloads/torrents')])
        self.assertEqual(s['environment']['PGID'],'65536')

    def test_prowlarr_needs_no_library_mount(self):
        s=yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['prowlarr']
        self.assertFalse(any(isinstance(v,dict)and v['target'].startswith('/data')for v in s['volumes']))

    def test_sonarr_common_view_masks_private_and_unrelated_paths(self):
        s=yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['sonarr']
        media=[v for v in s['volumes']if isinstance(v,dict)and v['target'].startswith('/data')]
        self.assertEqual([(v['source'],v['target'])for v in media],[('/mnt/stash/media','/data')])
        self.assertTrue(all(not v['bind']['create_host_path'] for v in media))
        self.assertEqual(s['environment']['PGID'], '65536')
        masks={v.split(':',1)[0]for v in s['tmpfs']}
        self.assertTrue({'/data/personal','/data/.maintenance','/data/library/movies','/data/library/music'}<=masks)
