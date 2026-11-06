"""M03.2 explicit synthetic wrapper planning, immutable snapshot, audit-only results."""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from nano_ar5iv.application.recover import execute_wrapper, save_plan
from nano_ar5iv.domain.provenance import sha256_file
from nano_ar5iv.infrastructure.repositories import SnapshotStore
from nano_ar5iv.interfaces.cli import main
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.recovery.patch_policy import UnsafeRecovery
from nano_ar5iv.recovery.planner import create_wrapper_plan, GENERATED_ENTRY
from nano_ar5iv.recovery.wrapper import render_wrapper


class FakeSuccessEngine:
    def __init__(self):
        self.calls = []

    def convert(self, workspace, entry, timeout_seconds):
        self.calls.append((entry, timeout_seconds, (workspace / entry).read_text()))
        html = workspace / "html"
        html.mkdir()
        (html / "index.html").write_text("<html><math><mi>x</mi></math></html>")
        return EngineAttempt("SUCCEEDED", "fake:not-real", "sha256:" + "a" * 64,
                             entry, 0, 0.02, False, ("fake",), 0, "html/index.html")


class WrapperRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paper = self.root / "paper"
        self.paper.mkdir()
        self.out = self.root / "artifacts"
        (self.paper / "chapters").mkdir()
        (self.paper / "chapters" / "intro.tex").write_text(r"\section{Intro} Hello $x^2$.", encoding="utf-8")
        (self.paper / "chapters" / "method.tex").write_text(r"\section{Methods} Hello $y$.", encoding="utf-8")
        self.bundle = SnapshotStore(self.out).capture(self.paper)

    def plan(self, fragments=("chapters/intro.tex", "chapters/method.tex"), documentclass="article"):
        return create_wrapper_plan(self.bundle, tuple(fragments), documentclass)

    def test_plan_determinism_and_explicit_order(self):
        first = self.plan()
        self.assertEqual(first, self.plan())
        self.assertNotEqual(first.plan_id, self.plan(fragments=first.fragments[::-1]).plan_id)
        self.assertTrue(first.review_required)
        self.assertEqual(first.generated_entry, GENERATED_ENTRY)
        self.assertIn(r"\input{chapters/intro.tex}", render_wrapper(first.fragments, first.documentclass))

    def test_planning_does_not_mutate_authors(self):
        original = (self.paper / "chapters/intro.tex").read_bytes()
        self.plan()
        self.assertEqual((self.paper / "chapters/intro.tex").read_bytes(), original)
        self.assertFalse((self.paper / GENERATED_ENTRY).exists())

    def test_rejects_unsafe_paths_and_duplicate_order(self):
        for fragments in (("../secret.tex",), ("/etc/passwd.tex",), ("chapters/intro.tex", "chapters/intro.tex"), ("x.tex",),
                          ("chapters/{injected}.tex",), ("chapters/../chapters/intro.tex",), ()):
            with self.subTest(fragments=fragments), self.assertRaises(UnsafeRecovery):
                self.plan(fragments=fragments)

    def test_rejects_implicit_documentclass(self):
        with self.assertRaises(UnsafeRecovery):
            self.plan(documentclass="customclass")
        with self.assertRaises(UnsafeRecovery):
            self.plan(documentclass=r"article\input{evil}")

    def test_rejects_embedded_complete_document(self):
        (self.paper / "full.tex").write_text(r"\documentclass{article}\begin{document}x\end{document}")
        bundle = SnapshotStore(self.out).capture(self.paper)
        with self.assertRaises(UnsafeRecovery):
            create_wrapper_plan(bundle, ("full.tex",), "article")

    def test_rejects_dynamic_inputs(self):
        (self.paper / "chapters/method.tex").write_text(r"\input{\jobname}")
        bundle = SnapshotStore(self.out).capture(self.paper)
        with self.assertRaises(UnsafeRecovery):
            create_wrapper_plan(bundle, ("chapters/method.tex",), "article")

    def test_conflicting_generated_path_disallowed(self):
        (self.paper / GENERATED_ENTRY).write_text("reserved")
        bundle = SnapshotStore(self.out).capture(self.paper)
        with self.assertRaises(UnsafeRecovery):
            create_wrapper_plan(bundle, ("chapters/intro.tex",), "article")

    def test_plan_save_and_tamper_detection(self):
        plan = self.plan()
        target = save_plan(plan, self.out)
        self.assertEqual(target, save_plan(plan, self.out))
        target.write_text('{"hijacked":true}')
        with self.assertRaises(UnsafeRecovery):
            save_plan(plan, self.out)

    def test_execute_only_one_attempt_and_preserve_original_hashes(self):
        before = {f.path: f.sha256 for f in self.bundle.files}
        plan = self.plan()
        fake = FakeSuccessEngine()
        report, report_path = execute_wrapper(self.bundle, plan, fake, self.out, timeout_seconds=30)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["quality_status"], "NOT_EVALUATED")
        self.assertEqual(report["attempt_count"], 1)
        self.assertTrue(report["original_files_unchanged"])
        self.assertNotEqual(report["original_bundle_id"], report["derived_bundle_id"])
        self.assertEqual(json.loads(report_path.read_text()), report)
        self.assertFalse((self.paper / GENERATED_ENTRY).exists())
        self.assertEqual(before, {f.path: f.sha256 for f in self.bundle.files})
        self.assertEqual(sha256_file(self.bundle.source_root / "chapters/intro.tex"), before["chapters/intro.tex"])
        self.assertIn(r"\input{chapters/method.tex}", fake.calls[0][2])
        self.assertTrue(Path(report["attempt_manifest_path"]).exists())

    def test_plan_tamper_blocks_execution(self):
        plan = replace(self.plan(), generated_sha256="0" * 64)
        with self.assertRaises(UnsafeRecovery):
            execute_wrapper(self.bundle, plan, FakeSuccessEngine(), self.out)
        self.assertFalse((self.paper / GENERATED_ENTRY).exists())

    def test_timeout_is_bounded(self):
        with self.assertRaises(ValueError):
            execute_wrapper(self.bundle, self.plan(), FakeSuccessEngine(), self.out, timeout_seconds=601)

    def test_cli_preview_is_nonexecuting(self):
        output = StringIO()
        with redirect_stdout(output):
            code = main(["--output", str(self.out), "recover-wrapper", str(self.paper),
                         "--fragment", "chapters/intro.tex", "--documentclass", "article"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "PLANNED_REVIEW_REQUIRED")
        self.assertTrue(Path(payload["plan_path"]).is_file())
        self.assertFalse((self.paper / GENERATED_ENTRY).exists())

    def test_cli_execute_fake_engine_remains_review_required(self):
        fake = FakeSuccessEngine()
        output = StringIO()
        with patch("nano_ar5iv.interfaces.cli.Ar5ivistEngine", return_value=fake):
            with redirect_stdout(output):
                code = main(["--output", str(self.out), "recover-wrapper", str(self.paper),
                             "--fragment", "chapters/intro.tex", "--documentclass", "article", "--execute"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["engine_status"], "SUCCEEDED")
        self.assertEqual(payload["status"], "REVIEW_REQUIRED")
        self.assertEqual(payload["quality_status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
