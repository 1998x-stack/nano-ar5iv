"""M03 conservative recovery tests without Docker; assert immutable provenance."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from nano_ar5iv.application.recover import recover_existing_root, recover_fragments
from nano_ar5iv.infrastructure.repositories import SnapshotStore, ArtifactStore
from nano_ar5iv.infrastructure.workspaces import attempt_workspace
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.recovery.classifier import diagnose_attempt
from nano_ar5iv.recovery.patch_policy import RejectedPatch, apply_plan
from nano_ar5iv.recovery.planner import plan_append_end
from nano_ar5iv.recovery.strategies import RecoveryPlan, RecoveryPolicy, PatchOperation
from nano_ar5iv.recovery.wrapper import plan_wrapper


class BoundaryEngine:
    """Fake engine validates control flow, never real TeX semantics."""
    image = "fixture:test"

    def __init__(self):
        self.calls = 0

    def convert(self, workspace, entry, timeout_seconds):
        self.calls += 1
        source = (workspace / entry).read_text(encoding="utf-8")
        passed = r"\begin{document}" in source and r"\end{document}" in source
        (workspace / "html").mkdir()
        (workspace / "engine.stderr.txt").write_text(
            "" if passed else "Error: Incomplete TeX input: missing end document")
        (workspace / "paper.latexml.log").write_text(
            "Warning: layout unverified" if passed else "Error: Missing document end")
        if passed:
            (workspace / "html" / "index.html").write_text("<html>fake content</html>")
        return EngineAttempt("SUCCEEDED" if passed else "FAILED", self.image,
                             "sha256:"+"a"*64, entry, 0 if passed else 1, 0.1,
                             False, ("fake",), 1,
                             "html/index.html" if passed else None)


class MissingPackageEngine(BoundaryEngine):
    def convert(self, workspace, entry, timeout_seconds):
        self.calls += 1
        (workspace / "engine.stderr.txt").write_text("Error: File custom.sty not found")
        return EngineAttempt("FAILED", self.image, "sha256:"+"a"*64, entry,
                             1, 0.1, False, ("fake",), 1, None)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.source = self.tmp / "input"
        self.source.mkdir()
        self.store = ArtifactStore(self.tmp / "output")

    def put(self, name, text):
        file = self.source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def bundle(self):
        return SnapshotStore(self.tmp / "output").capture(self.source)

    def test_append_repair_does_not_modify_source_and_logs_evidence(self):
        original = r"\documentclass{article}" + "\n" + r"\begin{document}" + "\nHello\n"
        self.put("paper.tex", original)
        source_bundle = self.bundle()
        engine = BoundaryEngine()
        result = recover_existing_root(source_bundle, "paper.tex", engine, self.store)
        self.assertEqual(result.status, "RECOVERED_UNVERIFIED")
        self.assertEqual(result.quality_status, "NOT_EVALUATED")
        self.assertEqual(engine.calls, 2)
        self.assertEqual([a["status"] for a in result.attempts], ["FAILED", "SUCCEEDED"])
        self.assertEqual((self.source / "paper.tex").read_text(), original)
        self.assertEqual((source_bundle.source_root / "paper.tex").read_text(), original)
        repaired = Path(result.attempts[1]["manifest_path"])
        saved = json.loads(repaired.read_text())
        self.assertEqual(saved["repair_audit"]["strategy"], "APPEND_END_DOCUMENT")
        self.assertEqual(saved["parent_run"], result.attempts[0]["manifest_path"])
        self.assertIn("repair.diff", [item["path"] for item in saved["artifacts"]])
        self.assertIn("repair-audit.json", [item["path"] for item in saved["artifacts"]])
        self.assertNotEqual(saved["repair_audit"]["before_sha256"],
                            saved["repair_audit"]["after_sha256"])

    def test_complete_baseline_never_repaired(self):
        self.put("paper.tex", r"\documentclass{article}\begin{document}Hello\end{document}")
        engine = BoundaryEngine()
        result = recover_existing_root(self.bundle(), "paper.tex", engine, self.store)
        self.assertEqual(result.status, "BASELINE_SUCCEEDED")
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(engine.calls, 1)
        self.assertIsNone(result.plan)

    def test_missing_custom_package_stops_and_abstains(self):
        self.put("paper.tex", "\\documentclass{article}\n\\begin{document}\nHello\n")
        engine = MissingPackageEngine()
        result = recover_existing_root(self.bundle(), "paper.tex", engine, self.store)
        self.assertEqual(result.status, "REVIEW_REQUIRED")
        self.assertEqual(engine.calls, 1)
        self.assertEqual(result.diagnosis["family"], "MISSING_PACKAGE")
        self.assertIsNone(result.plan)

    def test_policy_can_disable_repair(self):
        self.put("paper.tex", "\\documentclass{article}\n\\begin{document}\nHello\n")
        engine = BoundaryEngine()
        result = recover_existing_root(self.bundle(), "paper.tex", engine, self.store,
                                       policy=RecoveryPolicy(max_repairs=0))
        self.assertEqual(engine.calls, 1)
        self.assertEqual(result.status, "REVIEW_REQUIRED")

    def test_wrapper_order_and_pre_document_macro(self):
        self.put("preamble.tex", "\\newcommand{\\yes}{yes}\n")
        self.put("intro.tex", "\\section{Intro}\nText\n")
        self.put("method.tex", "\\section{Method}\nText\n")
        bundle = self.bundle()
        plan = plan_wrapper(bundle, ("intro.tex", "method.tex"), preamble="preamble.tex")
        self.assertEqual(plan.strategy, "EXPLICIT_FRAGMENT_WRAPPER")
        self.assertLess(plan.operations[0].payload.index(r"\input{intro.tex}"),
                        plan.operations[0].payload.index(r"\input{method.tex}"))
        engine = BoundaryEngine()
        result = recover_fragments(bundle, ("intro.tex", "method.tex"), engine, self.store,
                                   preamble="preamble.tex")
        self.assertEqual(result.status, "RECOVERED_UNVERIFIED")
        manifest = json.loads(Path(result.attempts[0]["manifest_path"]).read_text())
        self.assertEqual(manifest["root_entry"], "__nano_ar5iv_entry.tex")
        self.assertEqual(manifest["entry_selection"]["fragments"], ["intro.tex", "method.tex"])
        self.assertTrue((self.source / "intro.tex").is_file())
        self.assertFalse((self.source / "__nano_ar5iv_entry.tex").exists())
        self.assertFalse((bundle.source_root / "__nano_ar5iv_entry.tex").exists())

    def test_fragments_reject_unsafe_paths_and_duplicates(self):
        self.put("intro.tex", "Intro")
        bundle = self.bundle()
        for paths in (("../outside.tex",), ("intro.tex", "intro.tex"),
                      ("missing.tex",), ("intro.tex", "/tmp/x.tex"), ()):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                plan_wrapper(bundle, tuple(paths))
        with self.assertRaises(ValueError):
            plan_wrapper(bundle, ("intro.tex",), document_class="evil; rm -rf")

    def test_fragments_reject_complete_documents_and_name_collision(self):
        self.put("main.tex", r"\documentclass{article}\begin{document}Hi\end{document}")
        bundle = self.bundle()
        with self.assertRaises(ValueError):
            plan_wrapper(bundle, ("main.tex",))
        self.put("part.tex", "\\section{Part}")
        self.put("__nano_ar5iv_entry.tex", "occupied")
        with self.assertRaises(ValueError):
            plan_wrapper(self.bundle(), ("part.tex",))

    def test_patch_rejects_stale_hash_or_modified_workspace(self):
        source = "\\documentclass{article}\n\\begin{document}Hi\n"
        self.put("main.tex", source)
        bundle = self.bundle()
        attempt = EngineAttempt("FAILED", "test", None, "main.tex", 1, 0., False,
                                (), 1, None)
        diagnosis = diagnose_attempt(attempt, "Error: Missing document end")
        plan = plan_append_end(bundle, "main.tex", attempt, diagnosis)
        self.assertIsNotNone(plan)
        with attempt_workspace(bundle) as workspace:
            (workspace / "main.tex").write_text("tampered")
            with self.assertRaises(RejectedPatch):
                apply_plan(workspace, bundle, plan)

    def test_forged_wrapper_is_rejected_by_allowlist(self):
        self.put("part.tex", "\\section{A}")
        bundle = self.bundle()
        valid = plan_wrapper(bundle, ("part.tex",))
        forged = RecoveryPlan("EXPLICIT_FRAGMENT_WRAPPER", valid.entry,
                              bundle.bundle_id,
                              (PatchOperation("create_wrapper", valid.entry,
                                              "\\documentclass{article}\n\\write18{do_not_run}\n\\end{document}\n"),),
                              ("forged",))
        with attempt_workspace(bundle) as workspace:
            with self.assertRaises(RejectedPatch):
                apply_plan(workspace, bundle, forged)

    def test_repair_preserves_diagnosis_for_failed_second_attempt(self):
        self.put("paper.tex", "\\documentclass{article}\n\\begin{document}\nHello\n")
        class AlwaysFail(BoundaryEngine):
            def convert(self, workspace, entry, timeout_seconds):
                # Files are produced, but never claim successful conversion.
                self.calls += 1
                (workspace / "engine.stderr.txt").write_text("Error: broken document")
                return EngineAttempt("FAILED", self.image, None, entry, 1,
                                     0.1, False, ("fake",), 1, None)
        engine = AlwaysFail()
        result = recover_existing_root(self.bundle(), "paper.tex", engine, self.store)
        self.assertEqual(engine.calls, 2)
        self.assertEqual(result.status, "REVIEW_REQUIRED")
        self.assertEqual(len(result.attempts), 2)
        self.assertIsNotNone(result.plan)


if __name__ == "__main__":
    unittest.main()
