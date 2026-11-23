import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

class RadarrConfigTest(unittest.TestCase):
    def test_movie_watcher_media_masks_and_backup_gate(self):
        services=yaml.safe_load((ROOT/'hosts/newport/compose.yml').read_text())['services']
        app=services['radarr']
        labels=dict(s.split('=',1)for s in app['labels'])
        self.assertEqual(labels['com.centurylinklabs.watchtower.enable'],'true')
        self.assertEqual(labels['com.centurylinklabs.watchtower.lifecycle.pre-update'],'/bin/sh /infra/backup.sh')
        roots=[v for v in app['volumes']if isinstance(v,dict)and v['target']=='/data']
        self.assertEqual([v['source']for v in roots],['/mnt/stash/media'])
        self.assertEqual(app['environment']['PGID'],'65536')
        masks={m.split(':',1)[0]for m in app['tmpfs']}
        self.assertTrue({'/data/personal','/data/.maintenance','/data/library/tv','/data/library/documentaries','/data/library/music'}<=masks)
