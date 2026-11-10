"""Pre-update recovery snapshot: config, consistent SQLite, resume metadata and job exports."""
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


def backup():
    if os.geteuid()==0:
        os.setgroups([65536]);os.setgid(65536);os.setuid(1000)
    os.umask(0o077)
    config=Path('/config');deadline=time.monotonic()+120
    auth=json.loads((config/'.infra/auth.json').read_text())
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders=[('Referer','http://127.0.0.1:8087/')]
    def request(path,data=None):
        if time.monotonic()>deadline:raise TimeoutError('Backup deadline reached')
        body=urllib.parse.urlencode(data).encode()if data is not None else None
        with opener.open('http://127.0.0.1:8087/api/v2/'+path,body,timeout=10)as response:return response.read()
    request('auth/login',auth)
    jobs=json.loads(request('torrents/info'))
    preferences=json.loads(request('app/preferences'))
    with tempfile.TemporaryDirectory(prefix='recovery-',dir=config/'.infra')as directory:
        root=Path(directory)
        (root/'jobs.json').write_text(json.dumps(jobs,indent=2));(root/'preferences.json').write_text(json.dumps(preferences,indent=2))
        for source in config.rglob('*'):
            relative=source.relative_to(config)
            if '.infra'in relative.parts or source.is_dir()or source.name.endswith(('-wal','-shm'))or 'lockfile'in source.name:continue
            before=source.lstat()
            if stat.S_ISSOCK(before.st_mode):continue
            if not stat.S_ISREG(before.st_mode):raise ValueError('Unexpected config special file')
            target=root/'config'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb')as stream:header=stream.read(16)
            if header==b'SQLite format 3\x00':
                original=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);destination=sqlite3.connect(target)
                try:original.backup(destination);assert destination.execute('pragma integrity_check').fetchone()[0]=='ok'
                finally:destination.close();original.close()
            else:
                shutil.copy2(source,target);after=source.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('Config changed during snapshot')
        exports=root/'torrents';exports.mkdir()
        for job in jobs:
            if 'meta' in job['state'].lower():continue
            torrent_hash=job['hash']
            if any(c not in '0123456789abcdef'for c in torrent_hash.lower()):raise ValueError('Invalid torrent hash')
            try:payload=request('torrents/export?hash='+torrent_hash)
            except urllib.error.HTTPError as error:
                if error.code==404 and job.get('magnet_uri'):continue
                raise
            (exports/(torrent_hash+'.torrent')).write_bytes(payload)
        after_jobs=json.loads(request('torrents/info'))
        if {j['hash']for j in jobs}!={j['hash']for j in after_jobs}:raise ValueError('Torrent membership changed during backup')
        target=Path('/backups')/('qbittorrent-'+str(time.time_ns())+'.tar.gz')
        with tarfile.open(target,'w:gz')as archive:archive.add(root,arcname='recovery')
        with tarfile.open(target,'r:gz')as archive:assert any(n.endswith('/jobs.json')for n in archive.getnames())
        print('qBittorrent recovery snapshot completed:',len(jobs),'jobs',flush=True)

if __name__=='__main__':
    try:backup()
    except Exception as error:
        print('qBittorrent recovery backup failed; refusing update ('+type(error).__name__+').',flush=True)
        raise SystemExit(75)
