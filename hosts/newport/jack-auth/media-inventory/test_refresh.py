import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('refresh', Path(__file__).with_name('refresh.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RefreshTests(unittest.TestCase):
    def test_exact_projection(self):
        row = m.seerr([dict(id=1, permissions=0, username='fixture', email='discard')])[0]
        self.assertEqual(set(row), {'nativeId', 'name', 'disabled', 'administrator'})
        self.assertTrue(row['administrator'])
        self.assertFalse(row['disabled'])
        self.assertTrue(m.seerr([dict(id=2, permissions=2, username='fixture')])[0]['administrator'])

    def test_invalid_identity(self):
        for uid in (True, -1, 1.5, 9007199254740992):
            with self.assertRaises(ValueError):
                m.seerr([dict(id=uid, permissions=0, username='fixture')])
        with self.assertRaises(ValueError):
            m.seerr([dict(id=2, permissions=0)])

    def test_jellyfin_policy(self):
        row = dict(Id='immutable', Name='fixture', Policy=dict(IsDisabled=True, IsAdministrator=False))
        self.assertTrue(m.jellyfin([row])[0]['disabled'])
        row['Policy']['IsDisabled'] = 0
        with self.assertRaises(ValueError):
            m.jellyfin([row])

    def test_duplicate(self):
        row = m.seerr([dict(id=2, permissions=0, username='fixture')])[0]
        with self.assertRaises(ValueError):
            m.envelope('seerr', [row, row])

    def test_atomic_failure_preserves_old(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'snapshot.json'
            m.atomic(path, {'old': True})
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                m.atomic(path, 'x' * m.LIMIT)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_incomplete_page(self):
        old = m.get
        try:
            m.get = lambda *args: dict(pageInfo=dict(results=2), results=[{}])
            with self.assertRaises(ValueError):
                m.seerr_pages('synthetic')
        finally:
            m.get = old


if __name__ == '__main__':
    unittest.main()
