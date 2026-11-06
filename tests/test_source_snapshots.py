import json
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.infrastructure.repositories import SnapshotStore, UnsafeSource


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        (self.source / "nested").mkdir()
        (self.source / "nested" / "section.tex").write_text("x", encoding="utf-8")
        (self.source / "paper.tex").write_text("\\input{nested/section}", encoding="utf-8")
        self.store = SnapshotStore(self.root / "store")

    def test_capture_is_content_addressed_and_repeatable(self):
        first = self.store.capture(self.source)
        second = self.store.capture(self.source)
        self.assertEqual(first.bundle_id, second.bundle_id)
        self.assertTrue((first.source_root / "paper.tex").is_file())
        manifest = json.loads(first.manifest_path.read_text())
        self.assertEqual([f["path"] for f in manifest["files"]], ["nested/section.tex", "paper.tex"])
        (self.source / "paper.tex").write_text("different", encoding="utf-8")
        third = self.store.capture(self.source)
        self.assertNotEqual(third.bundle_id, first.bundle_id)
        self.assertEqual((first.source_root / "paper.tex").read_text(), "\\input{nested/section}")

    def test_rejects_symlink_and_output_nested_in_source(self):
        (self.source / "bad.tex").symlink_to(self.source / "paper.tex")
        with self.assertRaises(UnsafeSource):
            self.store.capture(self.source)
        (self.source / "bad.tex").unlink()
        with self.assertRaises(UnsafeSource):
            SnapshotStore(self.source / "generated").capture(self.source)

    def test_rejects_private_dot_env_and_count_limits(self):
        (self.source / ".env").write_text("SECRET=1")
        with self.assertRaises(UnsafeSource):
            self.store.capture(self.source)
        (self.source / ".env").unlink()
        with self.assertRaises(UnsafeSource):
            SnapshotStore(self.root / "store", max_files=1).capture(self.source)

    def test_rejects_tampered_snapshot_on_second_capture(self):
        first = self.store.capture(self.source)
        saved = first.source_root / "paper.tex"
        saved.chmod(0o644)
        saved.write_text("corruption")
        with self.assertRaises(UnsafeSource):
            self.store.capture(self.source)


if __name__ == "__main__":
    unittest.main()
