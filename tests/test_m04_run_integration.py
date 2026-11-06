"""M04 checksum-verifying run normalization using fake HTML/XML artifacts."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nano_ar5iv.application.normalize import normalize_run
from nano_ar5iv.adapters.latexml.output_reader import InvalidArtifact
from nano_ar5iv.domain.provenance import sha256_file
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.interfaces.cli import main
from test_m04_normalization import XML, HTML


class FixtureEngine:
    def convert(self, workspace, entry, timeout_seconds):
        (workspace / "html").mkdir()
        (workspace / "html" / "index.html").write_bytes(HTML)
        return EngineAttempt("SUCCEEDED", "fixture:tag", "sha256:"+"a"*64,
                             entry, 0, 0.01, False, ("fake",), 0, "html/index.html")


class RunNormalizationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "output"
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "manuscript.tex").write_text("\\documentclass{article}")
        bundle = SnapshotStore(self.output).capture(self.source)
        _, self.manifest = convert_source(bundle, "manuscript.tex", FixtureEngine(),
                                          ArtifactStore(self.output))

    def test_run_normalize_writes_immutable_versioned_document(self):
        doc, file = normalize_run(self.manifest, self.output)
        self.assertTrue(file.is_file())
        self.assertEqual(doc.source_kind, "latex_html")
        self.assertEqual(doc.provenance["run_id"], self.manifest.parent.name)
        self.assertEqual(doc.provenance["source_span_status"], "NOT_AVAILABLE")
        self.assertTrue(doc.equations)
        self.assertEqual(json.loads(file.read_text())["quality_status"], "NOT_EVALUATED")
        report = json.loads(file.with_name("normalization-manifest.json").read_text())
        self.assertEqual(report["paper_document_sha256"], sha256_file(file))
        self.assertEqual(report["input_sha256"],
                         json.loads(self.manifest.read_text())["artifacts"][0]["sha256"])
        doc_again, second_file = normalize_run(self.manifest, self.output)
        self.assertEqual(doc.to_dict(), doc_again.to_dict())
        self.assertEqual(file, second_file)
        self.assertTrue(self.manifest.is_file())

    def test_run_normalize_fails_on_tampered_artifact(self):
        file = self.manifest.parent / "artifacts/html/index.html"
        file.write_text("tampered")
        with self.assertRaises(InvalidArtifact):
            normalize_run(self.manifest, self.output)

    def test_run_normalize_fails_on_tampered_document_derivation(self):
        _, file = normalize_run(self.manifest, self.output)
        file.write_text("mutated")
        with self.assertRaises(ValueError):
            normalize_run(self.manifest, self.output)

    def test_cli_normalize_smoke(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = main(["--output", str(self.output), "normalize", str(self.manifest)])
        self.assertEqual(result, 0)
        record = json.loads(stdout.getvalue())
        self.assertEqual(record["status"], "NORMALIZED")
        self.assertEqual(record["quality_status"], "NOT_EVALUATED")
        self.assertGreater(record["counts"]["equations"], 0)
        self.assertTrue(Path(record["document_path"]).is_file())

    def test_run_manifest_outside_output_root_rejected(self):
        with self.assertRaises(InvalidArtifact):
            normalize_run(self.manifest, self.root / "wrong-root")

    def test_run_manifest_rejects_unsupported_format(self):
        with self.assertRaises(InvalidArtifact):
            normalize_run(self.manifest, self.output, "xml")

    def test_run_manifest_rejects_malicious_artifact_names(self):
        manifest = json.loads(self.manifest.read_text())
        manifest["artifacts"][0]["path"] = "../escape.html"
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(InvalidArtifact):
            normalize_run(self.manifest, self.output)

    def test_xml_preferred_when_both_formats_recorded(self):
        record = json.loads(self.manifest.read_text())
        source_xml = self.manifest.parent / "artifacts/xml/document.xml"
        source_xml.parent.mkdir(parents=True)
        source_xml.write_bytes(XML)
        from nano_ar5iv.domain.provenance import sha256_file
        record["artifacts"].append({"path": "xml/document.xml",
                                    "sha256": sha256_file(source_xml),
                                    "size_bytes": source_xml.stat().st_size})
        self.manifest.write_text(json.dumps(record))
        document, _ = normalize_run(self.manifest, self.output)
        self.assertEqual(document.source_kind, "latex_xml")
        self.assertEqual(len(document.equations), 2)


if __name__ == "__main__":
    unittest.main()
