import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class BackupTest(unittest.TestCase):
    def test_online_wal_keys_private_modes_and_daily_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, backups = root / "config", root / "backups"
            config.mkdir()
            db = sqlite3.connect(config / "users.db")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA wal_autocheckpoint=0")
            db.execute("CREATE TABLE users(id INTEGER)")
            db.execute("INSERT INTO users VALUES (7)")
            db.commit()
            (config / "jwt-key.bin").write_bytes(b"synthetic-signing-key")
            keys = config / "DataProtection-Keys"
            keys.mkdir()
            (keys / "fixture.xml").write_text("<fixture/>")
            (config / "logs").mkdir()
            (config / "logs/private.txt").write_text("not backup data")
            env = {**os.environ, "CONFIG_DIR": str(config), "BACKUP_DIR": str(backups)}
            script = Path(__file__).with_name("backup.py")
            for _ in range(2):
                subprocess.run([sys.executable, str(script), "daily"], env=env, check=True)
            snapshots = [p for p in backups.iterdir() if p.is_dir()]
            self.assertEqual(len(snapshots), 1)
            saved = snapshots[0]
            with sqlite3.connect(saved / "users.db") as restored:
                self.assertEqual(restored.execute("SELECT id FROM users").fetchall(), [(7,)])
                self.assertEqual(restored.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual((saved / "jwt-key.bin").read_bytes(), b"synthetic-signing-key")
            self.assertTrue((saved / "DataProtection-Keys/fixture.xml").is_file())
            self.assertFalse((saved / "logs").exists())
            self.assertFalse(any(p.name.endswith(("-wal", "-shm")) for p in saved.rglob("*")))
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in saved.rglob("*") if p.is_file()))
            db.close()


if __name__ == "__main__":
    unittest.main()
