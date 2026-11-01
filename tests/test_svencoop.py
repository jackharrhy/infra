import hashlib
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
import zipfile

SVEN = Path(__file__).resolve().parents[1] / 'hosts/newport/svencoop'
install = runpy.run_path(str(SVEN / 'install-maps.py'))['install']


class SvenCoopTests(unittest.TestCase):
    def test_runtime_config_is_private_and_executes_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['session.cfg', 'jack-admins.txt']:
                (root / name).write_text('old config')
                (root / name).chmod(0o644)
            subprocess.run(['sh', str(SVEN / 'entrypoint.sh'), 'sh', '-c', 'touch executed'],
                           cwd=root, check=True, env={**os.environ,
                           'SVENCOOP_PASSWORD': 'test-only',
                           'SVENCOOP_DOWNLOAD_URL': 'http://192.0.2.1:27015',
                           'SVENCOOP_ADMINS': 'STEAM_0:1:123'})
            self.assertTrue((root / 'executed').exists())
            self.assertIn('sv_password "test-only"', (root / 'session.cfg').read_text())
            self.assertEqual((root / 'jack-admins.txt').read_text(), 'STEAM_0:1:123\n')
            for name in ['session.cfg', 'jack-admins.txt']:
                self.assertEqual((root / name).stat().st_mode & 0o777, 0o600)

    def test_password_cannot_inject_console_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['sh', str(SVEN / 'entrypoint.sh'), 'true'], cwd=tmp,
                                    env={**os.environ, 'SVENCOOP_PASSWORD': 'test\nquit',
                                         'SVENCOOP_DOWNLOAD_URL': 'http://192.0.2.1:27015'},
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(Path(tmp, 'session.cfg').exists())

    def test_archive_validation_precedes_extraction(self):
        for case in ['valid', 'checksum', 'traversal', 'symlink']:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / 'pack.zip'
                with zipfile.ZipFile(archive, 'w') as pack:
                    pack.writestr('bundle/maps/demo.bsp', b'fixture')
                    if case == 'traversal':
                        pack.writestr('bundle/../escape.txt', b'not allowed')
                    if case == 'symlink':
                        link = zipfile.ZipInfo('bundle/models/link')
                        link.create_system = 3
                        link.external_attr = 0o120777 << 16
                        pack.writestr(link, '../escape')
                spec = {'archive': 'pack.zip', 'strip_prefix': 'bundle/',
                        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
                if case == 'checksum':
                    spec['sha256'] = '0' * 64
                if case == 'valid':
                    install('demo', spec, root)
                    self.assertEqual((root / 'custom/maps/demo.bsp').read_bytes(), b'fixture')
                else:
                    with self.assertRaises(ValueError):
                        install('demo', spec, root)
                    self.assertFalse((root / 'custom').exists())
                    self.assertFalse((root / 'escape.txt').exists())
