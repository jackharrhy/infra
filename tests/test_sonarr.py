import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class SonarrConfigTest(unittest.TestCase):
    def test_native_backups_protect_tracking_updates(self):
        service = yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']['sonarr']
        labels=dict(v.split('=',1) for v in service['labels'])
        self.assertEqual(labels['com.centurylinklabs.watchtower.enable'],'true')
        self.assertEqual(labels['com.centurylinklabs.watchtower.lifecycle.pre-update'],'/bin/sh /infra/backup.sh')
