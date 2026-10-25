import datetime as dt
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).resolve().parents[1] / 'hosts/newport/cheesetown/retain-backups.sh'
NOW = dt.datetime(2026, 11, 30, 12, tzinfo=ZoneInfo('America/St_Johns'))


class BackupRetentionTests(unittest.TestCase):
    def run_hook(self, directory, argument):
        environment = dict(os.environ, DEST_DIR=directory, TZ='America/St_Johns', RETENTION_NOW=str(int(NOW.timestamp())))
        image = os.environ.get('RETENTION_TEST_IMAGE')
        if image:
            command = ['docker', 'run', '--rm', '--network', 'none', '--memory', '64m', '--cpus', '1',
                       '--entrypoint', 'bash', '-v', directory + ':/backups', '-v', str(SCRIPT) + ':/retain-backups.sh:ro',
                       '-e', 'DEST_DIR=/backups', '-e', 'TZ=America/St_Johns',
                       '-e', 'RETENTION_NOW=' + str(int(NOW.timestamp())), image, '/retain-backups.sh', argument]
        else:
            command = ['bash', str(SCRIPT), argument]
        return subprocess.run(command, env=environment, capture_output=True, text=True, timeout=20)

    def test_recent_daily_weekly_and_first_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dates = [
                NOW - dt.timedelta(days=age, hours=hour)
                for age in [1, 8, 15, 35, 36, 100]
                for hour in [0, 1]
            ]
            for date in dates:
                name = date.strftime('cheesetown-%Y%m%d-%H%M%S.tar.gz')
                (root / name).write_bytes(b'fixture')
            expected_dates = [dates[i] for i in [0, 1, 3, 5, 7, 9, 11]]
            expected = {d.strftime('cheesetown-%Y%m%d-%H%M%S.tar.gz') for d in expected_dates}
            result = self.run_hook(directory, '--apply')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in root.iterdir()}, expected)

    def test_dry_run_and_failed_backup_never_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ['cheesetown-20260901-120000.tar.gz', 'cheesetown-20260901-180000.tar.gz']
            for name in names:
                (root / name).write_bytes(b'fixture')
            for argument in ['--dry-run', '2']:
                result = self.run_hook(directory, argument)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual({p.name for p in root.iterdir()}, set(names))

    def test_foreign_files_symlinks_and_nested_archives_are_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'cheesetown-20260901-120000.tar.gz').write_bytes(b'oldest')
            (root / 'cheesetown-20260901-180000.tar.gz').write_bytes(b'redundant')
            (root / 'other-server-20260901-180000.tar.gz').write_bytes(b'foreign')
            (root / 'cheesetown-20260901-190000.tar.gz').symlink_to('other-server-20260901-180000.tar.gz')
            (root / 'milestones').mkdir()
            nested = root / 'milestones/cheesetown-20260901-200000.tar.gz'
            nested.write_bytes(b'milestone')
            result = self.run_hook(directory, '0')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'cheesetown-20260901-180000.tar.gz').exists())
            self.assertEqual(nested.read_bytes(), b'milestone')
            self.assertEqual((root / 'other-server-20260901-180000.tar.gz').read_bytes(), b'foreign')
            self.assertTrue((root / 'cheesetown-20260901-190000.tar.gz').is_symlink())
