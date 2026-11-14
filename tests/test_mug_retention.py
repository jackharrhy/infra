import configparser
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class MugRetentionTests(unittest.TestCase):
    def test_existing_producers_keep_seven_latest_verified_names_not_age_prune(self):
        for app in ['andrewsite', 'teacms']:
            script = (ROOT / f'hosts/mug/{app}/backup.sh').read_text()
            marker = '# Keep seven newest producer-verified daily archives'
            self.assertLess(script.index('tar -tzf "$tea_archive"'), script.index(marker))
            self.assertIn('flock -n 9', script)
            self.assertNotIn('-mtime +13', script)
            retention = script[script.index(marker):script.index("printf 'TeaCMS backup verified")]
            with self.subTest(app=app), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                names = [f'tea-202610{i:02}T041701Z.tar.gz' for i in range(1, 13)]
                for name in names:
                    (base / name).write_bytes(b'producer-verified fixture')
                unrelated = base / 'old-image.tar.gz'
                unrelated.write_bytes(b'keep')
                # A symlink with a valid-looking latest name must not displace recovery.
                link = base / 'tea-20261231T041701Z.tar.gz'
                link.symlink_to(unrelated)
                env = {**os.environ, 'tea_backups': temp}
                subprocess.run(['bash', '-euo', 'pipefail', '-c', retention], env=env, check=True)
                self.assertEqual([n for n in names if (base / n).exists()], names[-7:])
                self.assertTrue(unrelated.exists())
                self.assertTrue(link.is_symlink())

    def test_teacms_native_backup_mount_is_isolated_with_bounded_policy(self):
        service = yaml.safe_load((ROOT / 'hosts/mug/compose.yml').read_text())['services']['teacms']
        mounts = [m for m in service['volumes'] if isinstance(m, dict) and m.get('target') == '/app/backups']
        self.assertEqual(mounts, [{'type': 'bind', 'source': './volumes/teacms_backups',
                                  'target': '/app/backups', 'bind': {'create_host_path': False}}])
        self.assertEqual({k: v for k, v in service['environment'].items() if k.startswith('TEA_BACKUP_')}, {
            'TEA_BACKUP_DIR': '/app/backups', 'TEA_BACKUP_INTERVAL_SECONDS': '86400',
            'TEA_BACKUP_KEEP': '7', 'TEA_BACKUP_RESERVE_BYTES': '268435456'})
        self.assertIn('./volumes/teacms:/app/data', service['volumes'])
        self.assertTrue((ROOT / 'hosts/mug/teacms/backup.cron').is_file())

    def test_prospective_journal_bounds_and_future_container_limits(self):
        config = configparser.ConfigParser()
        config.read(ROOT / 'hosts/mug/logging/infra.conf')
        journal = config['Journal']
        self.assertEqual(journal['SystemMaxUse'], '3G')
        self.assertEqual(journal['SystemKeepFree'], '2G')
        self.assertEqual(journal['MaxRetentionSec'], '0')
        self.assertEqual(journal['SystemMaxFileSize'], '64M')
        compose = yaml.safe_load((ROOT / 'hosts/mug/compose.yml').read_text())
        for name in ['radio-celld', 'teacms']:
            self.assertEqual(compose['services'][name]['logging'], {
                'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}})
