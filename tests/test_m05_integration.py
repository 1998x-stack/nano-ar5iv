"""M05 integration: M01 run -> M04 derivation -> source-bound audit."""
from __future__ import annotations
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.application.normalize import normalize_run
from nano_ar5iv.application.evaluate import InvalidEvidence, evaluate_run
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.domain.provenance import sha256_file
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.quality.reference import InvalidGolden
from test_m05_quality import SOURCE_XML, SOURCE_HTML, golden_data


class M05EngineFixture:
    def convert(self, workspace, entry, timeout_seconds):
        (workspace / "html").mkdir()
        (workspace / "html" / "index.html").write_bytes(SOURCE_HTML)
        return EngineAttempt("SUCCEEDED", "fixture:test", "sha256:"+"f"*64,
                             entry, 0, 0.01, False, ("fake",), 0, "html/index.html")


class M05RunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.src = self.root / "source"
        self.src.mkdir()
        (self.src / "paper.tex").write_text(
            "\\documentclass{article}\\begin{document}Independent test text $a+b$\\end{document}")
        self.out = self.root / "store"
        self.bundle = SnapshotStore(self.out).capture(self.src)
        _, self.run_manifest = convert_source(
            self.bundle, "paper.tex", M05EngineFixture(), ArtifactStore(self.out))
        self.paper, self.paper_path = normalize_run(self.run_manifest, self.out)

    def with_golden(self, *, xml=True, expectations=None):
        if xml:
            self.add_xml_artifact()
            self.paper, self.paper_path = normalize_run(self.run_manifest, self.out, "xml")
        record = golden_data()
        record["source_bundle_id"] = self.bundle.bundle_id
        if expectations is not None:
            record["expected"] = expectations
        path = self.root / "golden.json"
        path.write_text(json.dumps(record, indent=2))
        return path

    def add_xml_artifact(self):
        manifest = json.loads(self.run_manifest.read_text())
        if any(x["path"] == "xml/document.xml" for x in manifest["artifacts"]):
            return
        file = self.run_manifest.parent / "artifacts/xml/document.xml"
        file.parent.mkdir(parents=True)
        file.write_bytes(SOURCE_XML)
        manifest["artifacts"].append({
            "path": "xml/document.xml", "sha256": sha256_file(file),
            "size_bytes": file.stat().st_size})
        self.run_manifest.write_text(json.dumps(manifest))

    def test_without_external_gold_report_is_review_required_and_source_unchanged(self):
        report, file = evaluate_run(self.paper_path, self.out)
        self.assertEqual(report.decision, "REVIEW_REQUIRED")
        self.assertEqual(report.dimensions["visual"].status, "NOT_RUN")
        self.assertEqual(report.dimensions["mathematics"].status, "UNKNOWN")
        self.assertTrue(file.is_file())
        self.assertEqual(json.loads(self.paper_path.read_text())["quality_status"], "NOT_EVALUATED")
        quality_manifest = json.loads(file.with_name("quality-manifest.json").read_text())
        self.assertEqual(quality_manifest["quality_report_sha256"], sha256_file(file))
        self.assertEqual(quality_manifest["decision"], "REVIEW_REQUIRED")
        same, again = evaluate_run(self.paper_path, self.out)
        self.assertEqual(same.to_dict(), report.to_dict())
        self.assertEqual(file, again)

    def test_xml_source_bound_independently_authored_golden_can_accept_fixture_assertions(self):
        golden = self.with_golden()
        report, file = evaluate_run(self.paper_path, self.out, golden)
        self.assertEqual(report.decision, "ACCEPTED")
        self.assertEqual(report.provenance["reference_reviewer_claim"], "test fixture author")
        self.assertFalse(report.provenance["reference_identity_independently_authenticated"])
        self.assertEqual(report.dimensions["mathematics"].status, "PASS")
        self.assertEqual(report.dimensions["visual"].status, "NOT_APPLICABLE")
        self.assertEqual(sha256_file(file), json.loads(
            file.with_name("quality-manifest.json").read_text())["quality_report_sha256"])
        self.assertEqual(json.loads(self.paper_path.read_text())["quality_status"], "NOT_EVALUATED")

    def test_html_with_same_golden_math_tokens_cannot_accept(self):
        expectation = golden_data()["expected"]
        expectation["equations"] = [{"mathml_tokens": ["a", "+", "b"]}]
        golden = self.with_golden(xml=False, expectations=expectation)
        report, _ = evaluate_run(self.paper_path, self.out, golden)
        self.assertIn(report.decision, {"PARTIAL", "REVIEW_REQUIRED"})
        self.assertNotEqual(report.decision, "ACCEPTED")
        self.assertEqual(report.dimensions["provenance"].status, "UNKNOWN")

    def test_cli_no_gold_nonzero_and_json_report(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--output", str(self.out), "evaluate", str(self.paper_path)])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "ASSESSED")
        self.assertEqual(result["decision"], "REVIEW_REQUIRED")
        self.assertTrue(Path(result["quality_report_path"]).is_file())

    def test_cli_gold_accepted_zero(self):
        golden = self.with_golden()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--output", str(self.out), "evaluate", str(self.paper_path),
                         "--golden", str(golden)])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["decision"], "ACCEPTED")

    def test_tampered_normalized_document_rejected(self):
        self.paper_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(InvalidEvidence):
            evaluate_run(self.paper_path, self.out)

    def test_tampered_run_manifest_rejected(self):
        self.run_manifest.write_text("{}")
        with self.assertRaises(InvalidEvidence):
            evaluate_run(self.paper_path, self.out)

    def test_tampered_source_snapshot_rejected(self):
        path = self.bundle.source_root / "paper.tex"
        path.chmod(0o644)
        path.write_text("altered")
        with self.assertRaises(InvalidEvidence):
            evaluate_run(self.paper_path, self.out)

    def test_tampered_engine_html_artifact_rejected(self):
        (self.run_manifest.parent / "artifacts/html/index.html").write_bytes(b"<html>tampered</html>")
        with self.assertRaises(InvalidEvidence):
            evaluate_run(self.paper_path, self.out)

    def test_tampered_existing_quality_report_refused_not_overwritten(self):
        _, file = evaluate_run(self.paper_path, self.out)
        file.write_text("tampered")
        with self.assertRaises(InvalidEvidence):
            evaluate_run(self.paper_path, self.out)

    def test_document_path_must_be_in_its_normalization_store(self):
        with self.assertRaises((InvalidEvidence, OSError)):
            evaluate_run(self.paper_path, self.root / "wrong-output")

    def test_golden_missing_required_fields_is_not_silently_ignored(self):
        golden = self.with_golden(xml=False)
        data = json.loads(golden.read_text())
        del data["expected"]["tables"]
        golden.write_text(json.dumps(data))
        with self.assertRaises(InvalidGolden):
            evaluate_run(self.paper_path, self.out, golden)

    def test_golden_bound_to_different_paper_never_accepted(self):
        golden = self.with_golden()
        record = json.loads(golden.read_text())
        record["root_path"] = "another.tex"
        golden.write_text(json.dumps(record))
        report, _ = evaluate_run(self.paper_path, self.out, golden)
        self.assertEqual(report.decision, "REJECTED")
        self.assertIn("GOLDEN_SOURCE_MISMATCH", report.reason_codes)


if __name__ == "__main__":
    unittest.main()
