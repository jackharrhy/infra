import datetime as dt
import hashlib
import os
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
        subprocess.run(['cp', '-r', str(tree), str(other)], check=True)
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
        self.owned('expired', age=86401)
        self.assertEqual(self.call('reuse', self.root, SHA), '')
        self.assertEqual(self.call('reuse', self.root, 'b' * 64), '')

    def test_complete_receipt_and_reuse_for_file_and_directory(self):
        for name, directory in [('file', False), ('tree', True)]:
            self.artifact(name, directory=directory)
            self.assertEqual(self.call('complete', self.root, name, SHA), '')
            fields = (self.meta / name).read_text().splitlines()
            self.assertEqual(fields[0:2], ['version=1', f'basename={name}'])
            self.assertEqual(fields[4:], [f'datasetSHA={SHA}',
                                         f'artifactSHA={self.call("hash", self.root / name)}'])
            self.assertTrue(self.call('reuse', self.root, SHA))
        self.assertFalse((self.meta / '.lock').exists())

    def test_union_seven_observed_days_and_three_newest_generations(self):
        # Sparse historical days must count, not just the last seven calendar days.
        names = set()
        expected = {'current'}
        midnight = self.now - self.now % 86400
        for day in [0, 2, 5, 10, 20, 40, 80, 160, 320]:
            for generation in range(4):
                name = f'g{day:03d}-{generation}'
                # Strict chronological order; current publication is newest.
                epoch = midnight - day * 86400 - generation * 60 - 1
                self.owned(name, age=self.now - epoch, directory=(generation == 3))
                names.add(name)
                if day in [0, 2, 5, 10, 20, 40, 80] and generation == 0:
                    expected.add(name)
        # g000-* are actually yesterday. Current day is a separate observed day.
        expected.remove('g080-0')
        expected.add('g000-1')
        self.complete()
        survivors = {p.name for p in self.root.iterdir() if p.name != '.infra-hook-v1'}
        self.assertEqual(survivors, expected)
        self.assertEqual({p.name for p in self.meta.iterdir()}, expected)

    def test_manual_unknown_changed_and_symlink_artifacts_are_preserved(self):
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
        self.assertEqual(result.stderr.strip(),
                         'backup-retention: warning: unverifiable old generations preserved')
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
        for i, mutate in enumerate([
            lambda s: s + 'extra\n',
            lambda s: s.replace('version=1', 'version=2'),
            lambda s: s.replace('basename=r2', 'basename=../r2'),
            lambda s: s.replace('epoch=', 'epoch=0'),
            lambda s: s.replace('day=', 'day=invalid'),
            lambda s: s.replace('datasetSHA=', 'datasetSHA=oops'),
        ]):
            name = f'r{i}'
            self.owned(name, age=10 + i)
            receipt = self.meta / name
            receipt.write_text(mutate(receipt.read_text()))
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

    def test_post_receipt_retention_failure_preserves_publication(self):
        self.owned('old', age=1000000)
        self.artifact('current')
        tools = self.root / 'tools'
        tools.mkdir()
        fake = tools / 'sort'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'])
        result = subprocess.run(['sh', str(SCRIPT), 'complete', str(self.root),
                                 'current', SHA], env=env, capture_output=True,
                                text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('completed artifact and receipt preserved', result.stderr)
        self.assertTrue((self.meta / 'current').is_file())
        self.assertTrue((self.root / 'current').is_file())
        self.assertTrue((self.root / 'old').is_file())

    def test_complete_only_hashes_new_and_prune_candidates(self):
        self.owned('keep1', age=10)
        self.owned('keep2', age=20)
        self.artifact('current')
        tools = self.root / 'tools'
        tools.mkdir()
        fake = tools / 'sha256sum'
        log = self.root / 'hash-calls'
        fake.write_text('#!/bin/sh\n' + f'echo call >> "{log}"\n' +
                        'exec /usr/bin/sha256sum "$@"\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'])
        self.call('complete', self.root, 'current', SHA, env=env)
        self.assertEqual(log.read_text().splitlines(), ['call'])

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

    def test_hash_failure_after_publication_does_not_prune(self):
        self.owned('old', age=1000000)
        self.artifact('current')
        tools = self.root / 'tools'
        tools.mkdir()
        fake = tools / 'sha256sum'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=str(tools) + ':' + os.environ['PATH'])
        self.call('complete', self.root, 'current', SHA, ok=False, env=env)
        self.assertTrue((self.root / 'old').exists())
        self.assertFalse((self.meta / 'current').exists())


if __name__ == '__main__':
    unittest.main()
