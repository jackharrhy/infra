"""Fresh staging, rather than a time-only shortcut, protects pre-update recovery."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'hosts/common/backup-retention.sh'


class HookSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config'
        self.backups = self.root / 'backups'
        self.config.mkdir()
        self.backups.mkdir()
        self.env = dict(os.environ, INFRA_BACKUP_HELPER=str(HELPER))

    def run_hook(self, command, *args, ok=True):
        result = subprocess.run([*command, *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def generations(self):
        return sorted(p for p in self.backups.iterdir() if not p.name.startswith('.'))

    def test_adguard_exact_fresh_copy_reuse_corruption_and_manual(self):
        source = self.config / 'AdGuardHome.yaml'
        source.write_text('dns:\n  port: 53\n')
        self.env.update(CONFIG_FILE=str(source), BACKUP_DIR=str(self.backups))
        command = ['sh', str(ROOT / 'hosts/newport/adguardhome/backup.sh')]
        self.run_hook(command)
        self.run_hook(command)
        self.assertEqual(len(self.generations()), 1)
        source.write_text('dns:\n  port: 5353\n')
        self.run_hook(command)
        self.assertEqual(len(self.generations()), 2)
        # Corrupt every publication: exact current staging must not trust receipt alone.
        for path in self.generations():
            path.write_text('corrupt')
        self.run_hook(command)
        self.assertEqual(len(self.generations()), 3)
        receipts = set((self.backups / '.infra-hook-v1').iterdir())
        self.run_hook(command, 'manual')
        self.assertEqual(len(self.generations()), 4)
        self.assertEqual(set((self.backups / '.infra-hook-v1').iterdir()), receipts)
        marker = (self.backups / '.last-success').read_bytes()
        source.unlink()
        self.run_hook(command, ok=False)
        self.assertEqual((self.backups / '.last-success').read_bytes(), marker)
        self.assertEqual(len(self.generations()), 4)

    def exercise_sqlite(self, kind):
        db_dir = self.config / 'db' if kind == 'seerr' else self.config
        db_dir.mkdir(exist_ok=True)
        db_path = db_dir / 'state.db'
        connection = sqlite3.connect(db_path)
        self.addCleanup(connection.close)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE state (value INTEGER)')
        connection.execute('INSERT INTO state VALUES (1)')
        connection.commit()
        self.assertTrue(Path(str(db_path) + '-wal').exists())
        if kind == 'cleanuparr':
            self.env.update(CONFIG_DIR=str(self.config), BACKUP_DIR=str(self.backups))
            command = [sys.executable, str(ROOT / 'hosts/newport/cleanuparr/backup.py')]
        elif kind == 'seerr':
            (self.config / 'settings.json').write_text(json.dumps({'test': True}))
            self.env.update(SEERR_CONFIG_FOLDER=str(self.config), SEERR_BACKUP_FOLDER=str(self.backups))
            command = ['node', str(ROOT / 'hosts/newport/seerr/backup.mjs')]
        else:
            self.env.update(DB_PATH=str(db_path), LISTS_BACKUP_DIR=str(self.backups))
            command = ['bun', str(ROOT / 'hosts/mug/lists/hooks/backup.mjs')]
        self.run_hook(command)
        self.run_hook(command)
        self.assertEqual(len(self.generations()), 1, 'unchanged fresh capture should reuse publication')
        # A committed WAL-only mutation between pre-check and pre-update must publish.
        connection.execute('UPDATE state SET value=2')
        connection.commit()
        self.run_hook(command)
        self.assertEqual(len(self.generations()), 2)
        values = []
        for generation in self.generations():
            saved = generation / db_path.relative_to(self.config) if generation.is_dir() else generation
            with sqlite3.connect(saved) as snapshot:
                self.assertEqual(snapshot.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                values.append(snapshot.execute('SELECT value FROM state').fetchone()[0])
        self.assertEqual(sorted(values), [1, 2])
        count = len(list((self.backups / '.infra-hook-v1').iterdir()))
        self.run_hook(command, 'manual')
        self.assertEqual(len(self.generations()), 3)
        self.assertEqual(len(list((self.backups / '.infra-hook-v1').iterdir())), count)
        # Missing producer data must fail, never prune or advance the success marker.
        marker = self.backups / '.last-success'
        before = marker.read_bytes() if marker.exists() else None
        connection.close()
        db_path.unlink()
        self.run_hook(command, ok=False)
        self.assertEqual(len(self.generations()), 3)
        self.assertEqual(marker.read_bytes() if marker.exists() else None, before)

    def test_cleanuparr_wal_and_fresh_equivalence(self):
        self.exercise_sqlite('cleanuparr')

    def test_seerr_wal_and_fresh_equivalence(self):
        if not shutil.which('node') or subprocess.run(['node', '-e', "require('node:sqlite')"], capture_output=True).returncode:
            self.skipTest('node:sqlite unavailable')
        self.exercise_sqlite('seerr')

    def test_lists_wal_and_fresh_equivalence(self):
        if not shutil.which('bun'):
            self.skipTest('Bun unavailable')
        self.exercise_sqlite('lists')


if __name__ == '__main__':
    unittest.main()
