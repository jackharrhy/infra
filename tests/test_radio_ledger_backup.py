import pathlib
from contextlib import closing
import sqlite3
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'hosts/newport/jack-auth/backup-radio-ledger.py'

class RadioLedgerBackupTest(unittest.TestCase):
    def test_snapshot_preserves_denials_and_pending_state_privately(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            source = root / 'ledger.sqlite'
            with closing(sqlite3.connect(source)) as db, db:
                db.execute('CREATE TABLE radio_memberships(project_id,subject,state,grant_id,consented_at)')
                db.executemany('INSERT INTO radio_memberships VALUES(?,?,?,?,?)', [('project',state,state,None,'fixture') for state in ['denied','pending','granted']])
            result = subprocess.run(['python3',str(SCRIPT),'--source',str(source),'--directory',str(root/'backups')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            snapshots = list((root/'backups').glob('*.sqlite'))
            self.assertEqual(len(snapshots),1)
            self.assertEqual(snapshots[0].stat().st_mode & 0o777,0o600)
            self.assertEqual((root/'backups').stat().st_mode & 0o777,0o700)
            with closing(sqlite3.connect(snapshots[0])) as db:
                self.assertEqual(db.execute('SELECT state FROM radio_memberships ORDER BY state').fetchall(), [('denied',),('granted',),('pending',)])

    def test_snapshot_includes_existing_access_blocks_without_changing_sources(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            source = root / 'radio-enrollment.sqlite'
            access = root / 'access.sqlite'
            with closing(sqlite3.connect(source)) as db, db:
                db.execute('CREATE TABLE radio_memberships(state)')
                db.execute("INSERT INTO radio_memberships VALUES('denied')")
            with closing(sqlite3.connect(access)) as db, db:
                db.execute('CREATE TABLE blocks(subject, reason)')
                db.execute("INSERT INTO blocks VALUES('fixture-subject', 'explicit denial')")
            identity = [(p.stat().st_ino, hashlib.sha256(p.read_bytes()).hexdigest()) for p in [source, access]]
            result = subprocess.run(['python3', str(SCRIPT), '--source', str(source), '--directory', str(root/'backups')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list((root/'backups').glob('*.sqlite'))), 2)
            receipt = json.loads(result.stdout)
            with closing(sqlite3.connect(receipt['accessSnapshot'])) as db:
                self.assertEqual(db.execute('SELECT * FROM blocks').fetchall(), [('fixture-subject', 'explicit denial')])
            self.assertEqual([(p.stat().st_ino, hashlib.sha256(p.read_bytes()).hexdigest()) for p in [source, access]], identity)
            for p in (root/'backups').iterdir():
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_access_cannot_silently_disappear_after_first_paired_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            source = root / 'radio-enrollment.sqlite'
            access = root / 'access.sqlite'
            with closing(sqlite3.connect(source)) as db, db:
                db.execute('CREATE TABLE radio_memberships(state)')
            with closing(sqlite3.connect(access)) as db, db:
                db.execute('CREATE TABLE blocks(subject)')
            command = ['python3', str(SCRIPT), '--source', str(source), '--directory', str(root/'backups')]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            access.unlink()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('Access database is required', second.stderr)
            self.assertEqual(len(list((root/'backups').glob('*.json'))), 1)

if __name__ == '__main__':
    unittest.main()
