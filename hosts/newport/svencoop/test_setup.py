import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent


class RuntimeConfigTests(unittest.TestCase):
    def test_private_config_and_command_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, 'SVENCOOP_PASSWORD': 'test-only',
                   'SVENCOOP_DOWNLOAD_URL': 'http://192.0.2.1:27015',
                   'SVENCOOP_ADMINS': 'STEAM_0:1:123'}
            result = subprocess.run(['sh', str(HERE / 'entrypoint.sh'), 'sh', '-c',
                                     'test -s session.cfg && test -s jack-admins.txt'],
                                    cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            cfg = Path(tmp, 'session.cfg')
            self.assertIn('sv_password "test-only"', cfg.read_text())
            self.assertEqual(cfg.stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(tmp, 'jack-admins.txt').read_text(), 'STEAM_0:1:123\n')

    def test_existing_config_becomes_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp, 'session.cfg')
            cfg.write_text('old configuration')
            cfg.chmod(0o644)
            result = subprocess.run(['sh', str(HERE / 'entrypoint.sh'), 'true'], cwd=tmp,
                                    env={**os.environ, 'SVENCOOP_PASSWORD': 'test-only',
                                         'SVENCOOP_DOWNLOAD_URL': 'http://192.0.2.1:27015'},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(cfg.stat().st_mode & 0o777, 0o600)


    def test_rejects_console_command_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['sh', str(HERE / 'entrypoint.sh'), 'true'], cwd=tmp,
                                    env={**os.environ, 'SVENCOOP_PASSWORD': 'test\nquit',
                                         'SVENCOOP_DOWNLOAD_URL': 'http://192.0.2.1:27015'},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(Path(tmp, 'session.cfg').exists())


class MapInstallTests(unittest.TestCase):
    def test_verified_archive_strips_packaging_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'fixture.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('bundle/maps/demo.bsp', b'test fixture, not a real game map')
            manifest = root / 'maps.json'
            manifest.write_text(json.dumps({'maps': {'demo': {
                'url': archive.as_uri(), 'archive': 'fixture.zip',
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'strip_prefix': 'bundle/'}}}))
            result = subprocess.run(['python3', str(HERE / 'install-maps.py'), 'demo',
                                     '--manifest', str(manifest), '--data-dir', str(root / 'data')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'data/custom/maps/demo.bsp').read_bytes(),
                             b'test fixture, not a real game map')


    def test_rejects_invalid_archives_before_installing(self):
        for invalid in ['checksum', 'traversal', 'symlink']:
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / 'fixture.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr('bundle/maps/demo.bsp', b'fixture')
                    if invalid == 'traversal':
                        z.writestr('bundle/../escape.txt', b'not allowed')
                    if invalid == 'symlink':
                        link = zipfile.ZipInfo('bundle/models/link')
                        link.create_system = 3
                        link.external_attr = 0o120777 << 16
                        z.writestr(link, '../escape')
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                manifest = root / 'maps.json'
                manifest.write_text(json.dumps({'maps': {'demo': {
                    'url': archive.as_uri(), 'archive': 'fixture.zip',
                    'sha256': '0' * 64 if invalid == 'checksum' else digest,
                    'strip_prefix': 'bundle/'}}}))
                result = subprocess.run(['python3', str(HERE / 'install-maps.py'), 'demo',
                                         '--manifest', str(manifest), '--data-dir', str(root / 'data')],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / 'data/custom/maps/demo.bsp').exists())
                self.assertFalse((root / 'data/escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
