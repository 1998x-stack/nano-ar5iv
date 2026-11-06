"""Real ar5ivist conversion -> M04 IR -> M05 safe abstention, no false acceptance."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.domain.provenance import sha256_file
from nano_ar5iv.interfaces.cli import main


@unittest.skipUnless(os.environ.get("RUN_REAL_LATEXML") == "1", "Docker LaTeXML not configured")
class RealM05Tests(unittest.TestCase):
    def test_real_html_must_not_claim_scientific_fidelity_without_gold(self):
        with tempfile.TemporaryDirectory(prefix="m05-real-") as tmp:
            root = Path(tmp)
            out = root / "store"
            conversion = io.StringIO()
            with contextlib.redirect_stdout(conversion):
                rc = main(["--output", str(out), "convert",
                           "examples/trusted-minimal", "--entry", "manuscript.tex",
                           "--timeout", "200"])
            self.assertEqual(rc, 0, conversion.getvalue())
            first = json.loads(conversion.getvalue())
            self.assertEqual(first["status"], "SUCCEEDED")
            normalized = io.StringIO()
            with contextlib.redirect_stdout(normalized):
                rc = main(["--output", str(out), "normalize", first["manifest_path"]])
            self.assertEqual(rc, 0, normalized.getvalue())
            paper = json.loads(normalized.getvalue())
            evaluated = io.StringIO()
            with contextlib.redirect_stdout(evaluated):
                rc = main(["--output", str(out), "evaluate", paper["document_path"]])
            result = json.loads(evaluated.getvalue())
            self.assertEqual(rc, 3)
            self.assertEqual(result["decision"], "REVIEW_REQUIRED")
            self.assertNotEqual(result["dimensions"]["mathematics"], "PASS")
            self.assertEqual(result["dimensions"]["visual"], "NOT_RUN")
            report_path = Path(result["quality_report_path"])
            manifest = json.loads(report_path.with_name("quality-manifest.json").read_text())
            self.assertEqual(sha256_file(report_path), manifest["quality_report_sha256"])
            original = json.loads(Path(paper["document_path"]).read_text())
            self.assertEqual(original["quality_status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
