"""M02 self-authored E01-E12 fixtures plus adversarial archive / metadata cases."""
import contextlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from nano_ar5iv.application.discover import discover_entries
from nano_ar5iv.infrastructure.repositories import SnapshotStore, UnsafeSource
from nano_ar5iv.interfaces.cli import main

ROOT = r"\documentclass{article}\begin{document}OK\end{document}"


class EntryDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.paper = self.base / "paper"
        self.paper.mkdir()

    def add(self, name, contents):
        p = self.paper / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contents if isinstance(contents, bytes) else contents.encode())
        return p

    def discover(self):
        bundle = SnapshotStore(self.base / "out").capture(self.paper)
        return discover_entries(bundle)

    def test_e01_main(self):
        self.add("main.tex", ROOT)
        self.assertEqual(self.discover()["decision"]["selected_roots"], ["main.tex"])

    def test_e02_non_main(self):
        self.add("ms.ltx", ROOT)
        self.assertEqual(self.discover()["decision"]["selected_roots"], ["ms.ltx"])

    def test_e03_nested_dependency(self):
        self.add("sub/paper.tex", ROOT + r"\input{sub/chapter}")
        self.add("sub/chapter.tex", "chapter content")
        d = self.discover()
        self.assertEqual(d["decision"]["selected_roots"], ["sub/paper.tex"])
        self.assertEqual(d["graph"]["edges"][0]["target"], "sub/chapter.tex")

    def test_e04_two_roots(self):
        self.add("paper.tex", ROOT)
        self.add("supplement.tex", ROOT)
        d = self.discover()["decision"]
        self.assertEqual(d["status"], "MULTIPLE_ROOTS")
        self.assertEqual(d["selected_roots"], ["paper.tex", "supplement.tex"])

    def test_e05_modern_metadata_precedence(self):
        self.add("alpha.tex", ROOT)
        self.add("beta.tex", ROOT)
        self.add("00README.json", json.dumps({"process": {"compiler": "pdflatex"},
             "sources": [{"filename": "beta.tex", "usage": "toplevel"},
                         {"filename": "alpha.tex", "usage": "ignore"}]}))
        d = self.discover()["decision"]
        self.assertEqual(d["status"], "SELECTED")
        self.assertEqual(d["selected_roots"], ["beta.tex"])
        self.assertEqual(d["metadata_source"], "00README.json")

    def test_e06_legacy_metadata(self):
        self.add("a.tex", ROOT)
        self.add("b.tex", ROOT)
        self.add("00README.XXX", "b.tex toplevelfile\na.tex ignore\n")
        self.assertEqual(self.discover()["decision"]["selected_roots"], ["b.tex"])

    def test_e07_missing_manifest_root(self):
        self.add("a.tex", ROOT)
        self.add("00README.json", '{"sources":[{"filename":"missing.tex","usage":"toplevel"}]}')
        d = self.discover()["decision"]
        self.assertEqual(d["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("missing_metadata_root" in issue for issue in d["diagnostics"]))

    def test_e08_dynamic_input(self):
        self.add("paper.tex", ROOT + r"\input{\jobname}")
        d = self.discover()["decision"]
        self.assertEqual(d["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("unresolved_dynamic" in issue for issue in d["diagnostics"]))

    def test_e09_comment_and_verbatim(self):
        self.add("paper.tex", ROOT + "\n% " + r"\input{fake}" +
                 "\n" + r"\begin{verbatim}\input{alsofake}\end{verbatim}")
        d = self.discover()
        self.assertEqual(d["graph"]["edges"], [])
        self.assertFalse(any("missing_dependency" in issue for issue in d["decision"]["diagnostics"]))

    def test_e10_symlink_rejected(self):
        self.add("main.tex", ROOT)
        (self.paper / "escape.tex").symlink_to(self.paper / "main.tex")
        with self.assertRaises(UnsafeSource):
            self.discover()

    def test_e11_fragment_only(self):
        self.add("part.tex", r"\section{Methods}")
        d = self.discover()["decision"]
        self.assertEqual(d["status"], "REVIEW_REQUIRED")
        self.assertEqual(d["selected_roots"], [])

    def test_e12_pdf_only(self):
        self.add("paper.pdf", b"%PDF-1.4\n")
        self.assertEqual(self.discover()["decision"]["status"], "PDF_ONLY")

    def test_metadata_conflict_requires_review(self):
        self.add("a.tex", ROOT)
        self.add("b.tex", ROOT)
        self.add("00README.json", '{"sources":[{"filename":"a.tex","usage":"toplevel"}]}')
        self.add("00README.XXX", "b.tex toplevelfile\n")
        self.assertEqual(self.discover()["decision"]["status"], "REVIEW_REQUIRED")

    def test_metadata_path_traversal_requires_review(self):
        self.add("a.tex", ROOT)
        self.add("00README.json", '{"sources":[{"filename":"../secret.tex","usage":"toplevel"}]}')
        self.assertEqual(self.discover()["decision"]["status"], "REVIEW_REQUIRED")

    def test_cycle_diagnosed(self):
        self.add("main.tex", ROOT + r"\input{child}")
        self.add("child.tex", r"\input{main}")
        d = self.discover()
        self.assertTrue(any("dependency_cycle" in issue for issue in d["graph"]["diagnostics"]))

    def test_missing_include_diagnosed(self):
        self.add("main.tex", ROOT + r"\input{ghost}")
        self.assertTrue(any("missing_dependency" in issue for issue in self.discover()["graph"]["diagnostics"]))

    def test_discover_cli_persists_auditable_manifest(self):
        self.add("paper.tex", ROOT)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--output", str(self.base / "out"), "discover", str(self.paper)])
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["selected_roots"], ["paper.tex"])
        self.assertEqual(json.loads(Path(result["manifest_path"]).read_text())["decision"]["status"], "SELECTED")

    def test_valid_zip_discovery(self):
        archive = self.base / "input.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("paper.tex", ROOT)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--output", str(self.base / "out"), "discover", str(archive)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["selected_roots"], ["paper.tex"])

    def test_zip_traversal_rejected(self):
        archive = self.base / "bad.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../escape.tex", ROOT)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--output", str(self.base / "out"), "discover", str(archive)]), 2)
        self.assertFalse((self.base / "escape.tex").exists())

    def test_tar_symlink_rejected(self):
        archive = self.base / "bad.tar"
        with tarfile.open(archive, "w") as tf:
            link = tarfile.TarInfo("paper.tex")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tf.addfile(link)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--output", str(self.base / "out"), "discover", str(archive)]), 2)

    def test_ambiguous_auto_convert_stops_before_engine(self):
        self.add("a.tex", ROOT)
        self.add("b.tex", ROOT)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--output", str(self.base / "out"), "convert", str(self.paper)]), 2)


if __name__ == "__main__":
    unittest.main()
