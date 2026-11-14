import datetime
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid


def main():
    os.umask(0o077)
    config = Path(os.environ.get("CONFIG_DIR", "/config"))
    backups = Path(os.environ.get("BACKUP_DIR", "/backups"))
    backups.mkdir(parents=True, exist_ok=True)
    marker = backups / ".last-success"
    managed = "manual" not in sys.argv[1:]
    helper = os.environ.get("INFRA_BACKUP_HELPER", "/opt/infra-backup-retention.sh")
    def retention(*args):
        return subprocess.check_output(["sh", helper, *map(str, args)], text=True).strip()
    if "daily" in sys.argv[1:] and marker.exists() and time.time() - marker.stat().st_mtime < 86400:
        print("Recent Cleanuparr backup retained")
        return
    databases = sorted(p for p in config.rglob("*.db") if "logs" not in p.relative_to(config).parts)
    if not databases:
        raise RuntimeError("No Cleanuparr databases found")
    name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex
    staging = backups / (".incomplete-" + name)
    staging.mkdir(mode=0o700)
    try:
        for source in databases:
            dest = staging / source.relative_to(config)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)) as current:
                with closing(sqlite3.connect(dest)) as saved:
                    current.backup(saved)
                    saved.execute("PRAGMA journal_mode=DELETE")
                    if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("SQLite backup integrity failure")
            dest.chmod(0o600)
        for source in config.rglob("*"):
            relative = source.relative_to(config)
            if "logs" in relative.parts or not source.is_file() or source.name.endswith((".db", "-wal", "-shm", "-journal")):
                continue
            if source.is_symlink():
                raise RuntimeError("Unexpected configuration symlink")
            dest = staging / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            dest.chmod(0o600)
        if managed:
            digest = retention("hash", staging)
            previous = retention("reuse", backups, digest)
        else:
            previous = ""
        if previous:
            shutil.rmtree(staging)
            name = previous
            print("Fresh Cleanuparr snapshot matches verified previous publication")
        else:
            staging.rename(backups / name)
            if managed:
                retention("complete", backups, name, digest)
        temporary = marker.with_name(".last-success.new")
        temporary.write_text(name + "\n")
        temporary.replace(marker)
        print("Cleanuparr backup complete: " + name)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
