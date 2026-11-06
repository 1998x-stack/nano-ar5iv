"""M02 command-line discovery and fake-engine conversion tests."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.ports.engines import EngineAttempt


def tex(title):
    return "\\documentclass{article}\n\\begin{document}\n\\section{" + title + "}\n\\end{document}\n"


class FakeAr5ivist:
    def __init__(self, runtime):
        pass

    def convert(self, workspace, entry, timeout_seconds):
        output = workspace / "html"
        output.mkdir(parents=True)
        (output / "index.html").write_text("<html>fake smoke: " + entry + "</html>")
        return EngineAttempt("SUCCEEDED", "test:fake", "sha256:" + "a" * 64,
                             entry, 0, 0.001, False, ("fake",), 0, "html/index.html")


class M02CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "paper"
        self.source.mkdir()
        self.out = self.root / "out"

    def run_command(self, *args, fake=True):
        data = io.StringIO()
        cmd = ["--output", str(self.out), *args]
        with contextlib.redirect_stdout(data):
            if fake:
                with patch("nano_ar5iv.interfaces.cli.Ar5ivistEngine", FakeAr5ivist):
                    status = main(cmd)
            else:
                status = main(cmd)
        return status, json.loads(data.getvalue())

    def test_discover_cli_no_docker_required(self):
        (self.source / "draft.tex").write_text(tex("Draft"))
        status, data = self.run_command("discover", str(self.source), fake=False)
        self.assertEqual(status, 0)
        self.assertEqual(data["selected_roots"], ["draft.tex"])
        self.assertEqual(data["status"], "SELECTED")

    def test_auto_convert_records_selection_provenance(self):
        (self.source / "draft.tex").write_text(tex("Draft"))
        status, data = self.run_command("convert", str(self.source))
        self.assertEqual(status, 0)
        self.assertEqual(data["entry"], "draft.tex")
        manifest = json.loads(Path(data["manifest_path"]).read_text())
        self.assertEqual(manifest["entry_selection"]["selected_roots"], ["draft.tex"])
        self.assertEqual(manifest["quality_status"], "NOT_EVALUATED")

    def test_multiple_roots_refuse_implicit_choice(self):
        (self.source / "paper.tex").write_text(tex("Paper"))
        (self.source / "supp.tex").write_text(tex("Supplement"))
        status, data = self.run_command("convert", str(self.source), fake=False)
        self.assertEqual(status, 3)
        self.assertEqual(data["status"], "MULTIPLE_ROOTS")
        self.assertFalse((self.out / "runs").exists())

    def test_multiple_roots_explicitly_convert_all_separate(self):
        (self.source / "paper.tex").write_text(tex("Paper"))
        (self.source / "supp.tex").write_text(tex("Supplement"))
        status, data = self.run_command("convert", str(self.source), "--all-roots")
        self.assertEqual(status, 0)
        self.assertEqual(data["status"], "MULTI_ROOT_ATTEMPTS")
        self.assertEqual(len(data["results"]), 2)
        paths = {Path(row["manifest_path"]) for row in data["results"]}
        self.assertEqual(len(paths), 2)
        self.assertEqual({row["entry"] for row in data["results"]}, {"paper.tex", "supp.tex"})

    def test_ambiguous_probe_never_claims_scientific_selection(self):
        (self.source / "first.tex").write_text("\\section{First}")
        (self.source / "second.tex").write_text("\\section{Second}")
        status, data = self.run_command("discover", str(self.source), "--probe", "--top-k", "2")
        self.assertEqual(status, 3)
        self.assertEqual(data["status"], "AMBIGUOUS")
        self.assertEqual(len(data["trial_results"]), 2)
        self.assertEqual({x["status"] for x in data["trial_results"]}, {"SUCCEEDED"})
        self.assertEqual(data["selected_roots"], [])

    def test_malformed_manifest_abstains(self):
        (self.source / "draft.tex").write_text(tex("Draft"))
        (self.source / "00README.json").write_text('{"sources":')
        status, data = self.run_command("convert", str(self.source), fake=False)
        self.assertEqual(status, 3)
        self.assertEqual(data["status"], "MANIFEST_ERROR")

    def test_explicit_root_still_supported(self):
        (self.source / "paper.tex").write_text(tex("Paper"))
        (self.source / "supp.tex").write_text(tex("Supplement"))
        status, data = self.run_command("convert", str(self.source), "--entry", "supp.tex")
        self.assertEqual(status, 0)
        self.assertEqual(data["entry"], "supp.tex")
        manifest = json.loads(Path(data["manifest_path"]).read_text())
        self.assertEqual(manifest["entry_selection"]["selection"], "explicit")


if __name__ == "__main__":
    unittest.main()
