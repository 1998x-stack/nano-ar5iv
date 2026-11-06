"""Plan a single conservative, structural repair using source evidence."""
from __future__ import annotations
from nano_ar5iv.application.convert import validate_entry
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.ports.engines import EngineAttempt
from nano_ar5iv.source.tex_scanner import scan_tex
from nano_ar5iv.recovery.classifier import FailureDiagnosis
from nano_ar5iv.recovery.strategies import APPEND_END, PatchOperation, RecoveryPlan, RecoveryPolicy


def plan_append_end(bundle: SourceBundle, entry: str,
                    baseline: EngineAttempt, diagnosis: FailureDiagnosis,
                    policy: RecoveryPolicy = RecoveryPolicy()) -> RecoveryPlan | None:
    if not policy.allow_append_end or policy.max_repairs == 0:
        return None
    if baseline.status in {"SUCCEEDED", "ENGINE_UNAVAILABLE", "TIMED_OUT"}:
        return None
    if diagnosis.family in {"MISSING_PACKAGE", "UNKNOWN_MACRO", "MATH_PARSE", "ASSET_MISSING",
                            "BIB_MISSING", "MISSING_INPUT", "ENGINE_UNAVAILABLE", "TIMEOUT"}:
        return None
    root = validate_entry(bundle, entry)
    file_info = next(f for f in bundle.files if f.path == root)
    if file_info.size_bytes > 8 * 1024 * 1024:
        return None
    source = (bundle.source_root / root).read_text(encoding="utf-8", errors="replace")
    scan = scan_tex(source)
    if not (scan.has_class and scan.has_begin and not scan.has_end):
        return None
    if source.count(r"\end{document}") > 0 and not scan.has_end:
        # It may be commented out or verbatim, but automatic repair remains uncertain.
        return None
    return RecoveryPlan(
        APPEND_END, root, bundle.bundle_id,
        (PatchOperation("append_end", root, "\n" + r"\end{document}" + "\n",
                        expected_sha256=file_info.sha256),),
        ("explicit user opted into conservative recovery",
         "TeX root has documentclass and begin{document} but not end{document}",
         f"baseline converter status: {baseline.status}",
         f"diagnosis: {diagnosis.family}"),
        requires_review=True)
