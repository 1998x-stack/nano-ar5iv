import json
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.application.convert import convert_source, validate_entry, InvalidEntry
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.domain.provenance import sha256_file


class FakeSuccessfulEngine:
    def convert(self, workspace, entry, timeout_seconds):
        (workspace / "html").mkdir(exist_ok=True)
        (workspace / "html" / "index.html").write_text("<html><math><mi>x</mi></math></html>")
        (workspace / "manuscript.latexml.log").write_text("Warning: stub fixture")
        return EngineAttempt("SUCCEEDED", "fake:fixed", "sha256:" + "a" * 64,
                             entry, 0, 0.001, False, ("fake",), 1, "html/index.html")


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / "paper"
        self.input.mkdir()
        (self.input / "manuscript.tex").write_text("\\documentclass{article}\\begin{document}hi\\end{document}")
        self.output = self.root / "out"
        self.bundle = SnapshotStore(self.output).capture(self.input)

    def test_explicit_entry_only(self):
        for value in ("", "../paper.tex", "/abs.tex", "manuscript.pdf", "missing.tex", "./manuscript.tex", "x\\manuscript.tex"):
            with self.subTest(value=value):
                with self.assertRaises(InvalidEntry):
                    validate_entry(self.bundle, value)
        self.assertEqual(validate_entry(self.bundle, "manuscript.tex"), "manuscript.tex")

    def test_fake_engine_end_to_end_records_provenance(self):
        attempt, manifest_file = convert_source(self.bundle, "manuscript.tex", FakeSuccessfulEngine(), ArtifactStore(self.output))
        self.assertEqual(attempt.status, "SUCCEEDED")
        manifest = json.loads(manifest_file.read_text())
        self.assertEqual(manifest["source_bundle_id"], self.bundle.bundle_id)
        self.assertEqual(manifest["root_entry"], "manuscript.tex")
        self.assertEqual(manifest["quality_status"], "NOT_EVALUATED")
        files = {a["path"]: a for a in manifest["artifacts"]}
        self.assertIn("html/index.html", files)
        self.assertIn("logs/manuscript.latexml.log", files)
        self.assertEqual(files["html/index.html"]["sha256"], sha256_file(manifest_file.parent / "artifacts" / "html/index.html"))


if __name__ == "__main__":
    unittest.main()
