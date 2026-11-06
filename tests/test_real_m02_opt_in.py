"""One real Docker auto-root conversion. Opt in via RUN_REAL_LATEXML=1."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.interfaces.cli import main


@unittest.skipUnless(os.environ.get("RUN_REAL_LATEXML") == "1", "Real Docker LaTeXML not enabled")
class RealM02Tests(unittest.TestCase):
    def test_auto_main_from_arxiv_metadata_converts_to_html(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source"
            source.mkdir()
            (source / "supplement").mkdir()
            (source / "supplement" / "appendix.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\nSupplement.\n\\end{document}\n")
            (source / "draft.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n"
                "Main paper with $E=mc^2$.\n\\end{document}\n")
            (source / "00README.json").write_text(json.dumps({"sources": [
                {"filename": "draft.tex", "usage": "toplevel"},
                {"filename": "supplement/appendix.tex", "usage": "ignore"}
            ]}))
            response = io.StringIO()
            with contextlib.redirect_stdout(response):
                code = main(["--output", str(root / "out"), "convert", str(source),
                             "--timeout", "300"])
            self.assertEqual(code, 0, response.getvalue())
            data = json.loads(response.getvalue())
            self.assertEqual(data["entry"], "draft.tex")
            self.assertEqual(data["status"], "SUCCEEDED")
            manifest = json.loads(Path(data["manifest_path"]).read_text())
            self.assertEqual(manifest["entry_selection"]["metadata_source"], "00README.json")
            self.assertEqual(manifest["quality_status"], "NOT_EVALUATED")
            output = Path(data["manifest_path"]).parent / "artifacts/html/index.html"
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
