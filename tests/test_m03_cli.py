"""M03 CLI smoke and negative tests with a simulated converter."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.ports.engines import EngineAttempt


class FakeEngine:
    def __init__(self, runtime):
        pass

    def convert(self, workspace, entry, timeout_seconds):
        source = (workspace / entry).read_text()
        valid = r"\end{document}" in source
        (workspace / "html").mkdir()
        if valid:
            (workspace / "html" / "index.html").write_text("<html>fake engine</html>")
        else:
            (workspace / "engine.stderr.txt").write_text("Error: Missing end document")
        return EngineAttempt("SUCCEEDED" if valid else "FAILED", "fake:fixed",
                             "sha256:"+"0"*64, entry, 0 if valid else 1,
                             0.01, False, ("fake",), 0,
                             "html/index.html" if valid else None)


class M03CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "src"
        self.source.mkdir()

    def command(self, *args, fake=True):
        capture = io.StringIO()
        cmd = ["--output", str(self.root / "store"), "recover", str(self.source), *args]
        with contextlib.redirect_stdout(capture):
            if fake:
                with patch("nano_ar5iv.interfaces.cli.Ar5ivistEngine", FakeEngine):
                    code = main(cmd)
            else:
                code = main(cmd)
        return code, json.loads(capture.getvalue())

    def test_plan_only_does_not_need_docker(self):
        (self.source / "intro.tex").write_text("\\section{Intro}")
        code, response = self.command("--fragments", "intro.tex", "--plan-only", fake=False)
        self.assertEqual(code, 0)
        self.assertEqual(response["status"], "PLAN_ONLY")
        self.assertEqual(response["plan"]["strategy"], "EXPLICIT_FRAGMENT_WRAPPER")
        self.assertFalse((self.root / "store" / "runs").exists())

    def test_cli_append_and_separate_run_manifests(self):
        content = "\\documentclass{article}\n\\begin{document}\nHello"
        (self.source / "paper.tex").write_text(content)
        code, result = self.command("--entry", "paper.tex")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "RECOVERED_UNVERIFIED")
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual((self.source / "paper.tex").read_text(), content)
        self.assertEqual(result["plan"]["strategy"], "APPEND_END_DOCUMENT")

    def test_cli_explicit_wrapper_outputs_html_but_unverified(self):
        (self.source / "first.tex").write_text("\\section{One}")
        (self.source / "second.tex").write_text("\\section{Two}")
        code, result = self.command("--fragments", "first.tex", "second.tex")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "RECOVERED_UNVERIFIED")
        self.assertEqual(result["quality_status"], "NOT_EVALUATED")
        self.assertEqual(len(result["attempts"]), 1)
        manifest = Path(result["attempts"][0]["manifest_path"])
        self.assertIn("repair.diff", [x["path"] for x in json.loads(manifest.read_text())["artifacts"]])

    def test_plan_only_rejects_entry_mode_without_docker(self):
        (self.source / "a.tex").write_text("\\section{A}")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--output", str(self.root / "store"),
                         "recover", str(self.source), "--entry", "a.tex", "--plan-only"])
        self.assertEqual(code, 2)
        self.assertIn("--plan-only", stderr.getvalue())

    def test_recovery_limit_zero_never_applies_repair(self):
        (self.source / "a.tex").write_text("\\documentclass{article}\n\\begin{document}")
        code, result = self.command("--entry", "a.tex", "--max-repairs", "0")
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(result["attempts"]), 1)


if __name__ == "__main__":
    unittest.main()
