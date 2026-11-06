"""M04 opt-in REAL conversion + normalized IR via M01 CLI output."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.domain.provenance import sha256_file


@unittest.skipUnless(os.environ.get("RUN_REAL_LATEXML") == "1", "Real Docker image not configured")
class RealM04Tests(unittest.TestCase):
    def test_minimal_real_ar5ivist_conversion_normalizes_with_provenance(self):
        source = Path("examples/trusted-minimal").resolve()
        with tempfile.TemporaryDirectory(prefix="m04-real-") as tmp:
            out = Path(tmp) / "out"
            convert_stdout = io.StringIO()
            with contextlib.redirect_stdout(convert_stdout):
                convert_exit = main(["--output", str(out), "convert", str(source),
                                     "--entry", "manuscript.tex", "--timeout", "250"])
            self.assertEqual(convert_exit, 0, convert_stdout.getvalue())
            converted = json.loads(convert_stdout.getvalue())
            self.assertEqual(converted["status"], "SUCCEEDED")
            manifest = Path(converted["manifest_path"])
            normalize_stdout = io.StringIO()
            with contextlib.redirect_stdout(normalize_stdout):
                normalize_exit = main(["--output", str(out), "normalize", str(manifest)])
            self.assertEqual(normalize_exit, 0, normalize_stdout.getvalue())
            result = json.loads(normalize_stdout.getvalue())
            self.assertEqual(result["status"], "NORMALIZED")
            self.assertEqual(result["source_kind"], "latex_html")
            self.assertEqual(result["quality_status"], "NOT_EVALUATED")
            self.assertGreaterEqual(result["counts"]["nodes"], 1)
            self.assertGreaterEqual(result["counts"]["equations"], 1)
            path = Path(result["document_path"])
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["provenance"]["source_run_manifest_sha256"],
                             sha256_file(manifest))
            self.assertTrue(any(eq["presentation_mathml"] for eq in document["equations"]))
            report = json.loads(path.with_name("normalization-manifest.json").read_text())
            self.assertEqual(report["paper_document_sha256"], sha256_file(path))
            self.assertTrue(manifest.exists())


if __name__ == "__main__":
    unittest.main()
