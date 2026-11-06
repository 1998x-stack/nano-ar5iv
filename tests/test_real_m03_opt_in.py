"""M03 real Docker test: only a self-authored fragment and explicit wrapper.

Run only in trusted GitHub-hosted CI with an explicitly pre-pulled ar5ivist image.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.application.recover import recover_fragments
from nano_ar5iv.infrastructure.repositories import SnapshotStore, ArtifactStore
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.infrastructure.sandbox import DockerRuntime


@unittest.skipUnless(os.environ.get("RUN_REAL_LATEXML") == "1", "Real LaTeXML image not enabled")
class RealM03Tests(unittest.TestCase):
    def test_self_authored_fragment_wrapper_converts_without_overwriting_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            original = r"\section{An explicit fragment}" + "\n" + r"Text and $E=mc^2$." + "\n"
            (source / "intro.tex").write_text(original, encoding="utf-8")
            bundle = SnapshotStore(root / "store").capture(source)
            result = recover_fragments(bundle, ("intro.tex",),
                                       Ar5ivistEngine(DockerRuntime()),
                                       ArtifactStore(root / "store"),
                                       timeout_seconds=200)
            self.assertEqual(result.status, "RECOVERED_UNVERIFIED", result.to_dict())
            self.assertEqual(result.quality_status, "NOT_EVALUATED")
            self.assertEqual((source / "intro.tex").read_text(), original)
            self.assertEqual((bundle.source_root / "intro.tex").read_text(), original)
            manifest = Path(result.attempts[0]["manifest_path"])
            recorded = json.loads(manifest.read_text())
            self.assertEqual(recorded["root_entry"], "__nano_ar5iv_entry.tex")
            self.assertEqual(recorded["repair_audit"]["strategy"], "EXPLICIT_FRAGMENT_WRAPPER")
            paths = {item["path"] for item in recorded["artifacts"]}
            self.assertIn("html/index.html", paths)
            self.assertIn("repair.diff", paths)
            self.assertIn("repair-audit.json", paths)
            self.assertGreater((manifest.parent / "artifacts/html/index.html").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
