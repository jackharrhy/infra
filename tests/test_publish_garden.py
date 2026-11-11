import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("publish_garden", Path(__file__).parents[1] / "scripts/publish-garden.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublishGardenTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.notes = self.root / "notes"
        self.assets = self.root / "assets"
        self.notes.mkdir()
        self.assets.mkdir()

    def snapshot(self, source="---\npublic: true\n---\nFixture page\n"):
        data = source.encode()
        (self.notes / "Home.md").write_bytes(data)
        manifest = {"pages": [{"sourcePath": "Home.md", "hash": hashlib.sha256(data).hexdigest(), "bytes": len(data), "route": "/home"}], "assets": []}
        (self.notes / "deploy-manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_validates_source_hash_and_publication_boundary(self):
        manifest = self.snapshot()
        self.assertEqual(publisher.validate_snapshot(self.notes, self.assets), manifest)
        (self.notes / "Home.md").write_text("Changed after export")
        with self.assertRaisesRegex(ValueError, "Hash/size mismatch"):
            publisher.validate_snapshot(self.notes, self.assets)
        self.snapshot('---\npublic: "true"\n---\nNot published\n')
        with self.assertRaisesRegex(ValueError, "Non-public"):
            publisher.validate_snapshot(self.notes, self.assets)

    def test_rejects_unlisted_notes_and_escaping_media_paths(self):
        self.snapshot()
        (self.notes / "Private.md").write_text("Private fixture")
        with self.assertRaisesRegex(ValueError, "unlisted"):
            publisher.validate_snapshot(self.notes, self.assets)
        with self.assertRaisesRegex(ValueError, "Invalid snapshot path"):
            publisher.checked_file(self.assets, {"sourcePath": "../notes/Private.md"})

    def test_diff_separates_added_changed_and_removed(self):
        before = [{"sourcePath": "one", "hash": "old"}, {"sourcePath": "removed", "hash": "same"}]
        after = [{"sourcePath": "one", "hash": "new"}, {"sourcePath": "added", "hash": "same"}]
        self.assertEqual(publisher.changes(before, after, "sourcePath"), {"added": ["added"], "changed": ["one"], "removed": ["removed"]})


if __name__ == "__main__":
    unittest.main()
