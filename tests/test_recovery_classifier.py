"""M03.1 diagnostic evidence and false-root-cause safeguards."""
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

from nano_ar5iv.recovery.classifier import classify_failure
from nano_ar5iv.interfaces.cli import main


class FailureTriageTests(unittest.TestCase):
    def test_missing_class_is_first_observed_cause(self):
        report = classify_failure("Warning: hint\nError: Cannot find foo.cls\nError: invalid math\nFatal: cascade", exit_code=1)
        self.assertEqual(report["category"], "DEPENDENCY_MISSING")
        self.assertEqual(report["cascade_events_after_first"], 2)
        self.assertEqual(report["warning_events"], 1)
        self.assertFalse(report["root_cause_proven"])

    def test_unknown_macro(self):
        self.assertEqual(classify_failure("Error: Undefined control sequence \\foo")["category"], "UNKNOWN_MACRO")

    def test_bib_and_asset(self):
        self.assertEqual(classify_failure("Error: Missing references.bib")["category"], "BIB_MISSING")
        self.assertEqual(classify_failure("Error: image plot.png not found")["category"], "ASSET_MISSING")

    def test_math_parse(self):
        self.assertEqual(classify_failure("Error: Math parse error")["category"], "MATH_PARSE")

    def test_timeout_precedence(self):
        value = classify_failure("Error: Undefined control sequence", timed_out=True)
        self.assertEqual(value["category"], "TIMEOUT")
        self.assertFalse(value["root_cause_proven"])

    def test_engine_unavailable_and_output_missing(self):
        self.assertEqual(classify_failure("", status="ENGINE_UNAVAILABLE")["category"], "ENGINE_UNAVAILABLE")
        self.assertEqual(classify_failure("", status="OUTPUT_MISSING")["category"], "OUTPUT_MISSING")

    def test_no_diagnostic_does_not_prove_fidelity(self):
        result = classify_failure("", status="SUCCEEDED", exit_code=0)
        self.assertEqual(result["category"], "NO_ERROR_OBSERVED")
        self.assertFalse(result["root_cause_proven"])
        self.assertFalse(result["review_required"])

    def test_nonzero_exit_without_log(self):
        self.assertEqual(classify_failure("", status="FAILED", exit_code=125)["category"], "PROCESS_FAILED")

    def test_classifier_rejects_excess_log(self):
        with self.assertRaises(ValueError):
            classify_failure("a" * 21, max_log_chars=20)

    def test_diagnose_cli_without_source_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "attempt.latexml.log"
            file.write_text("Error: Undefined control sequence")
            output = StringIO()
            with redirect_stdout(output):
                code = main(["--output", str(Path(tmp) / "reports"), "diagnose", str(file), "--exit-code", "1"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["category"], "UNKNOWN_MACRO")


if __name__ == "__main__":
    unittest.main()
