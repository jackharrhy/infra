import pathlib
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
            with sqlite3.connect(source) as db:
                db.execute('CREATE TABLE radio_memberships(project_id,subject,state,grant_id,consented_at)')
                db.executemany('INSERT INTO radio_memberships VALUES(?,?,?,?,?)', [('project',state,state,None,'fixture') for state in ['denied','pending','granted']])
            result = subprocess.run(['python3',str(SCRIPT),'--source',str(source),'--directory',str(root/'backups')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            snapshots = list((root/'backups').glob('*.sqlite'))
            self.assertEqual(len(snapshots),1)
            self.assertEqual(snapshots[0].stat().st_mode & 0o777,0o600)
            self.assertEqual((root/'backups').stat().st_mode & 0o777,0o700)
            with sqlite3.connect(snapshots[0]) as db:
                self.assertEqual(db.execute('SELECT state FROM radio_memberships ORDER BY state').fetchall(), [('denied',),('granted',),('pending',)])

if __name__ == '__main__':
    unittest.main()
