"""CLI smoke tests without Docker/LaTeXML dependencies."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.infrastructure.sandbox import DockerUnavailable


class CliTests(unittest.TestCase):
    def test_inspect_cli_has_real_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paper = root / "paper"
            paper.mkdir()
            (paper / "a.tex").write_text("\\begin{document}hi\\end{document}")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = main(["--output", str(root / "out"), "inspect", str(paper)])
            self.assertEqual(code, 0)
            report = json.loads(captured.getvalue())
            self.assertEqual(len(report["files"]), 1)
            self.assertTrue(Path(report["manifest_path"]).is_file())

    def test_convert_without_docker_records_failed_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paper = root / "paper"
            paper.mkdir()
            (paper / "a.tex").write_text("test")
            captured = io.StringIO()
            with patch("nano_ar5iv.infrastructure.sandbox.DockerRuntime.image_id", side_effect=DockerUnavailable("no Docker")):
                with contextlib.redirect_stdout(captured):
                    code = main(["--output", str(root / "out"), "convert", str(paper), "--entry", "a.tex"])
            self.assertEqual(code, 2)
            report = json.loads(captured.getvalue())
            self.assertEqual(report["status"], "ENGINE_UNAVAILABLE")
            manifest = json.loads(Path(report["manifest_path"]).read_text())
            self.assertEqual(manifest["engine_attempt"]["status"], "ENGINE_UNAVAILABLE")
            self.assertIn("engine.stderr.txt", {f["path"] for f in manifest["artifacts"]})


if __name__ == "__main__":
    unittest.main()
