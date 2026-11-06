import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nano_ar5iv.infrastructure.sandbox import DockerRuntime, DockerUnavailable
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.adapters.latexml.diagnostics import parse_diagnostics


class FakeRuntime:
    image = "latexml/ar5ivist:2512.17"
    def execute(self, workspace, entry, timeout_seconds):
        from nano_ar5iv.infrastructure.sandbox import RuntimeResult
        (workspace / "html").mkdir(exist_ok=True)
        (workspace / "html" / "index.html").write_text("<html>test</html>")
        (workspace / "paper.latexml.log").write_text("Warning: simulated warning\nWarning: second simulated warning")
        return RuntimeResult("sha256:"+"0"*64, 0, 0.5, False, "ok", "", ("docker", "run"))


class DockerRuntimeTests(unittest.TestCase):
    def test_docker_is_networkless_nonroot_and_bounded(self):
        runtime = DockerRuntime(image="latexml/ar5ivist:2512.17")
        with tempfile.TemporaryDirectory() as d:
            args = runtime.build_command(Path(d).resolve(), "paper.tex", "nano-ar5iv-"+"a"*32)
        self.assertIn("--network=none", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--read-only", args)
        self.assertIn("--pull=never", args)
        self.assertIn("--pids-limit", args)
        self.assertIn("--memory", args)
        self.assertIn("--source=paper.tex", args)
        self.assertIn("--destination=html/index.html", args)
        self.assertEqual(args[args.index("--mount") + 1].split(",")[-1], "dst=/docdir")

    def test_rejects_latest_image(self):
        for image in ("latexml/ar5ivist:latest", "bad image", ""):
            with self.subTest(image=image), self.assertRaises(ValueError):
                DockerRuntime(image=image)

    def test_engine_success_only_if_output_present(self):
        with tempfile.TemporaryDirectory() as d:
            result = Ar5ivistEngine(FakeRuntime()).convert(Path(d), "paper.tex")
            self.assertEqual(result.status, "SUCCEEDED")
            self.assertEqual(result.diagnostic_count, 2)
            self.assertEqual(result.image_id, "sha256:" + "0" * 64)

    def test_fatal_diagnostic_overrides_zero_exit(self):
        class MisleadingRuntime(FakeRuntime):
            def execute(self, workspace, entry, timeout_seconds):
                value = super().execute(workspace, entry, timeout_seconds)
                (workspace / "paper.latexml.log").write_text("Fatal: missing math binding")
                return value
        with tempfile.TemporaryDirectory() as d:
            result = Ar5ivistEngine(MisleadingRuntime()).convert(Path(d), "paper.tex")
            self.assertEqual(result.status, "FAILED")

    def test_preexisting_html_does_not_count_as_success(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "html").mkdir()
            (Path(d) / "html/index.html").write_text("fake output")
            with self.assertRaisesRegex(ValueError, "Reserved"):
                Ar5ivistEngine(FakeRuntime()).convert(Path(d), "paper.tex")

    def test_diagnostic_parser(self):
        events = parse_diagnostics("Info: ignore\nWarning: foo\nError: bar\nFatal: bad")
        self.assertEqual([e.severity for e in events], ["WARNING", "ERROR", "FATAL"])

    def test_unavailable_image_returns_actionable_status(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = DockerRuntime()
            with patch.object(runtime, "execute", side_effect=DockerUnavailable("no image")):
                result = Ar5ivistEngine(runtime).convert(Path(d), "paper.tex")
            self.assertEqual(result.status, "ENGINE_UNAVAILABLE")
            self.assertIn("no image", (Path(d) / "engine.stderr.txt").read_text())


if __name__ == "__main__":
    unittest.main()
