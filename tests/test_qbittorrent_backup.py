import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'hosts/newport/qbittorrent/hooks/backup.py'
spec = importlib.util.spec_from_file_location('qb_backup', SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class QBittorrentBackupTest(unittest.TestCase):
    def setUp(self):
        self.job = {'hash': 'a' * 40, 'magnet_uri': 'magnet:?xt=urn:btih:' + 'a' * 40}

    def test_only_matching_recoverable_magnet_can_replace_missing_metadata(self):
        self.assertTrue(hook.missing_metadata_magnet(self.job, [], {'pieces_num': -1}))
        self.assertFalse(hook.missing_metadata_magnet(self.job, [{'index': 0}], {'pieces_num': -1}))
        self.assertFalse(hook.missing_metadata_magnet(self.job, [], {'pieces_num': 0}))
        self.assertFalse(hook.missing_metadata_magnet(self.job, [], {}))
        for uri in ['', 'https://example.invalid/file', 'magnet:?xt=urn:btih:' + 'b' * 40]:
            self.assertFalse(hook.missing_metadata_magnet(dict(self.job, magnet_uri=uri), [], {'pieces_num': -1}))

    def test_hash_and_uri_are_validated_without_logging_private_content(self):
        self.assertTrue(hook.recoverable_magnet(self.job))
        self.assertTrue(hook.recoverable_magnet(dict(self.job, magnet_uri=self.job['magnet_uri'].upper().replace('MAGNET:', 'magnet:').replace('XT=', 'xt='))))
        self.assertFalse(hook.recoverable_magnet(dict(self.job, hash='../escape')))
        self.assertFalse(hook.recoverable_magnet(dict(self.job, hash='x' * 40)))
