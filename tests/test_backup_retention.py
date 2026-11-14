import datetime as dt
import hashlib
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'hosts/common/backup-retention.sh'
SHA = hashlib.sha256(b'dataset').hexdigest()


class BackupRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.meta = self.root / '.infra-hook-v1'
        self.now = int(dt.datetime.now(dt.timezone.utc).timestamp())

    def call(self, *args, ok=True, env=None):
        result = subprocess.run(['sh', str(SCRIPT), *map(str, args)],
                                capture_output=True, text=True, timeout=20, env=env)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout.strip()

    def artifact(self, name, content=b'backup', directory=False):
        path = self.root / name
        if directory:
            path.mkdir()
            (path / 'payload').write_bytes(content)
        else:
            path.write_bytes(content)
        return path

    def owned(self, name, age=0, dataset=SHA, directory=False):
        path = self.artifact(name, directory=directory)
        digest = self.call('hash', path)
        self.meta.mkdir(exist_ok=True)
        epoch = self.now - age
        day = dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime('%Y-%m-%d')
        (self.meta / name).write_text(
            f'version=1\nbasename={name}\nepoch={epoch}\nday={day}\n'
            f'datasetSHA={dataset}\nartifactSHA={digest}\n')
        return path

    def complete(self, name='current'):
        self.artifact(name)
        self.call('complete', self.root, name, SHA)

    def test_hash_files_directories_paths_empty_dirs_and_mtimes(self):
        path = self.artifact('file', b'hello')
        self.assertEqual(self.call('hash', path), hashlib.sha256(b'hello').hexdigest())
        tree = self.artifact('tree', directory=True)
        (tree / 'empty').mkdir()
        (tree / 'newline\nname').write_bytes(b'edge')
        before = self.call('hash', tree)
        os.utime(tree / 'payload', (1, 1))
        self.assertEqual(self.call('hash', tree), before)
        (tree / 'empty').rmdir()
        self.assertNotEqual(self.call('hash', tree), before)
        (tree / 'empty').mkdir()
        (tree / 'payload').rename(tree / 'renamed')
        self.assertNotEqual(self.call('hash', tree), before)
        (tree / 'renamed').rename(tree / 'payload')
        (tree / 'payload').write_bytes(b'mutated')
        self.assertNotEqual(self.call('hash', tree), before)
        other = self.root / 'other'
        shutil.copytree(tree, other)
        self.assertEqual(self.call('hash', tree), self.call('hash', other))

    def test_hash_rejects_links_special_files_and_missing(self):
        path = self.artifact('file')
        link = self.root / 'link'
        link.symlink_to(path)
        self.call('hash', link, ok=False)
        tree = self.artifact('tree', directory=True)
        (tree / 'link').symlink_to(path)
        self.call('hash', tree, ok=False)
        (tree / 'link').unlink()
        os.mkfifo(tree / 'fifo')
        self.call('hash', tree, ok=False)
        self.call('hash', tree / 'fifo', ok=False)
        self.call('hash', self.root / 'missing', ok=False)

    def test_reuse_requires_exact_fresh_dataset_and_valid_artifact(self):
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        self.owned('older', age=100)
        newer = self.owned('newer', age=10, directory=True)
        self.assertEqual(self.call('reuse', self.root, SHA), 'newer')
        self.owned('different', age=1, dataset='a' * 64)
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        self.assertEqual(self.call('reuse', self.root, 'a' * 64), 'different')
        (self.meta / 'different').unlink()
        (newer / 'payload').write_bytes(b'changed')
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        (self.root / 'older').write_bytes(b'corrupt')
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        for receipt in self.meta.iterdir():
            receipt.unlink()
        self.owned('expired', age=86401)
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        self.assertEqual(self.call('reuse', self.root, 'b' * 64), '')

    def test_union_seven_observed_days_and_three_newest_generations(self):
        expected = {'current', 'g0', 'g0-second', 'g2', 'g5', 'g10', 'g20', 'g40'}
        midnight = self.now - self.now % 86400
        for day in [0, 2, 5, 10, 20, 40, 80, 160]:
            epoch = midnight - day * 86400 - 1
            self.owned(f'g{day}', age=self.now - epoch, directory=day in [2, 160])
        for name, seconds in [('g0-second', 2), ('g0-third', 3)]:
            self.owned(name, age=self.now - midnight + seconds)
        self.complete()
        survivors = {p.name for p in self.root.iterdir() if p.name != '.infra-hook-v1'}
        self.assertEqual(survivors, expected)
        self.assertEqual({p.name for p in self.meta.iterdir()}, expected)

    def test_manual_unknown_changed_and_symlink_artifacts_are_preserved(self):
        for i in range(3):
            self.owned(f'recent{i}', age=10 + i)
        self.owned('old-day-winner', age=9999999)
        manual = self.artifact('manual')
        old = self.owned('changed', age=10000000)
        old.write_bytes(b'changed')
        linked = self.owned('linked', age=10000001)
        linked.unlink()
        linked.symlink_to(manual)
        nested = self.owned('nested', age=10000002, directory=True)
        (nested / 'link').symlink_to(manual)
        self.artifact('unknown')
        (self.meta / 'unknown').write_text('version=99\n')
        (self.meta / 'foreign-link').symlink_to(manual)
        self.artifact('prechange')
        self.artifact('current')
        result = subprocess.run(['sh', str(SCRIPT), 'complete', str(self.root),
                                 'current', SHA], capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stderr.strip())
        for name in ['manual', 'changed', 'linked', 'nested', 'unknown', 'prechange']:
            self.assertTrue((self.root / name).exists())
        self.assertEqual((self.meta / 'unknown').read_text(), 'version=99\n')
        self.assertTrue((self.meta / 'foreign-link').is_symlink())
        self.assertEqual(self.call('reuse', self.root, SHA), 'current')

    def test_failure_never_prunes_and_unknown_receipts_not_overwritten(self):
        for i in range(12):
            self.owned(f'old{i}', age=10000000 + i * 86400)
        before = {p.name for p in self.root.iterdir()}
        for name in ['missing', '../escape', '.hidden', 'bad name']:
            self.call('complete', self.root, name, SHA, ok=False)
        self.artifact('bad-tree', directory=True)
        (self.root / 'bad-tree/link').symlink_to(self.root / 'old0')
        self.call('complete', self.root, 'bad-tree', SHA, ok=False)
        self.assertTrue(before.issubset({p.name for p in self.root.iterdir()}))
        self.artifact('unknown')
        (self.meta / 'unknown').write_text('do not overwrite\n')
        self.call('complete', self.root, 'unknown', SHA, ok=False)
        self.assertEqual((self.meta / 'unknown').read_text(), 'do not overwrite\n')
        self.call('complete', self.root, 'old0', 'not-a-sha', ok=False)
        self.assertEqual(len(list(self.meta.iterdir())), 13)

    def test_strict_receipts_and_metadata_symlink(self):
        self.owned('forged')
        receipt = self.meta / 'forged'
        receipt.write_text(receipt.read_text().replace('basename=forged', 'basename=../forged'))
        self.owned('future', age=-3600)
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        elsewhere = self.root / 'elsewhere'
        self.meta.rename(elsewhere)
        self.meta.symlink_to(elsewhere, target_is_directory=True)
        self.call('reuse', self.root, SHA, ok=False)
        self.artifact('current')
        self.call('complete', self.root, 'current', SHA, ok=False)

    def test_missing_latest_never_falls_back_and_lock_is_fail_closed(self):
        self.owned('older', age=100)
        latest = self.owned('latest', age=1)
        latest.unlink()
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        (self.meta / '.lock').mkdir()
        self.call('reuse', self.root, SHA, ok=False)
        self.artifact('current')
        self.call('complete', self.root, 'current', SHA, ok=False)
        self.assertTrue((self.meta / '.lock').is_dir())
        self.assertFalse((self.meta / 'current').exists())

    def test_failed_receipt_move_cleans_only_own_lock(self):
        self.artifact('current')
        tools = self.root / 'tools'
        tools.mkdir()
        fake = tools / 'mv'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'])
        self.call('complete', self.root, 'current', SHA, ok=False, env=env)
        self.assertFalse((self.meta / '.lock').exists())
        self.assertFalse((self.meta / 'current').exists())
        self.assertTrue((self.root / 'current').exists())


if __name__ == '__main__':
    unittest.main()
