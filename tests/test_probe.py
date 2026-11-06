"""M02 bounded probe checks; fake engine does not prove real TeX conversion."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nano_ar5iv.application.probe import probe_candidates
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.ports.engines import EngineAttempt

ROOT = r"\documentclass{article}\begin{document}Text\end{document}"


class FakeEngine:
    def __init__(self):
        self.calls = []

    def convert(self, workspace, entry, timeout_seconds):
        self.calls.append((entry, timeout_seconds))
        (workspace / "html").mkdir(exist_ok=True)
        (workspace / "html" / "index.html").write_text("<html>fixture</html>")
        return EngineAttempt("SUCCEEDED", "fake:fixed", "sha256:" + "a"*64,
                             entry, 0, .01, False, ("fake",), 0, "html/index.html")


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "paper"
        self.source.mkdir()
        for name in ("a.tex", "b.tex"):
            (self.source / name).write_text(ROOT)
        self.output = self.root / "out"
        self.bundle = SnapshotStore(self.output).capture(self.source)

    def test_multi_root_top_k_without_auto_selection(self):
        engine = FakeEngine()
        report = probe_candidates(self.bundle, engine, ArtifactStore(self.output), top_k=2)
        self.assertEqual(report["discovery_status"], "MULTIPLE_ROOTS")
        self.assertEqual(report["quality_status"], "NOT_EVALUATED")
        self.assertFalse(report["auto_selected"])
        self.assertEqual([a["entry"] for a in report["attempts"]], ["a.tex", "b.tex"])
        for a in report["attempts"]:
            self.assertTrue(Path(a["manifest_path"]).exists())
        self.assertEqual(len(engine.calls), 2)

    def test_top_k_is_bounded(self):
        with self.assertRaises(ValueError):
            probe_candidates(self.bundle, FakeEngine(), ArtifactStore(self.output), top_k=0)
        with self.assertRaises(ValueError):
            probe_candidates(self.bundle, FakeEngine(), ArtifactStore(self.output), top_k=10)

    def test_probe_cli_explicit(self):
        output = io.StringIO()
        engine = FakeEngine()
        with patch("nano_ar5iv.interfaces.cli.Ar5ivistEngine", return_value=engine):
            with contextlib.redirect_stdout(output):
                code = main(["--output", str(self.output), "probe", str(self.source), "--top-k", "1"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["quality_status"], "NOT_EVALUATED")
        self.assertTrue(Path(payload["summary_path"]).exists())


if __name__ == "__main__":
    unittest.main()
