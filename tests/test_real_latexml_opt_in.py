"""Real Docker integration is opt-in and requires a pre-pulled image."""
import os
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.infrastructure.sandbox import DockerRuntime


@unittest.skipUnless(os.environ.get("RUN_REAL_LATEXML") == "1", "Docker LaTeXML integration not configured")
class RealLaTeXMLTests(unittest.TestCase):
    def test_valid_self_authored_minimal_tex(self):
        tex = "\\documentclass{article}\\begin{document}Hello $E=mc^2$.\\end{document}"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "paper.tex").write_text(tex)
            result = Ar5ivistEngine(DockerRuntime()).convert(root, "paper.tex", 180)
            self.assertEqual(result.status, "SUCCEEDED")
            self.assertTrue((root / "html" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
