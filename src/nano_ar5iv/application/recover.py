"""M03 opt-in recovery: one baseline, at most one copy-only repair attempt.

A successful HTML file is RECOVERED_UNVERIFIED, never scientifically verified.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from nano_ar5iv.application.convert import convert_source, validate_entry
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.infrastructure.repositories import ArtifactStore
from nano_ar5iv.ports.engines import ConversionEngine, EngineAttempt
from nano_ar5iv.recovery.classifier import FailureDiagnosis, diagnose_attempt
from nano_ar5iv.recovery.planner import plan_append_end
from nano_ar5iv.recovery.strategies import RecoveryPlan, RecoveryPolicy
from nano_ar5iv.recovery.wrapper import plan_wrapper


@dataclass(frozen=True)
class RecoveryResult:
    status: str
    attempts: tuple[dict, ...]
    quality_status: str = "NOT_EVALUATED"
    diagnosis: dict | None = None
    plan: dict | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self) | {"attempts": list(self.attempts)}


def _attempt_summary(attempt: EngineAttempt, manifest: Path) -> dict:
    return {"status": attempt.status, "entry": attempt.entry,
            "manifest_path": str(manifest), "image_id": attempt.image_id}


def _saved_log(manifest: Path, limit: int = 1_000_000) -> str:
    root = manifest.parent / "artifacts"
    pieces: list[str] = []
    stderr = root / "engine.stderr.txt"
    if stderr.is_file():
        pieces.append(stderr.read_text(encoding="utf-8", errors="replace")[:limit])
    for p in sorted((root / "logs").rglob("*.latexml.log")) if (root / "logs").exists() else ():
        if p.is_file() and not p.is_symlink():
            pieces.append(p.read_text(encoding="utf-8", errors="replace")[:limit])
            if len(pieces) >= 4:
                break
    return "\n".join(pieces)


def recover_existing_root(bundle: SourceBundle, entry: str,
                          engine: ConversionEngine, store: ArtifactStore,
                          timeout_seconds: int = 300,
                          policy: RecoveryPolicy = RecoveryPolicy()) -> RecoveryResult:
    entry = validate_entry(bundle, entry)
    baseline, baseline_manifest = convert_source(
        bundle, entry, engine, store, timeout_seconds,
        selection={"method": "explicit_m03", "entry": entry})
    steps = [_attempt_summary(baseline, baseline_manifest)]
    if baseline.status == "SUCCEEDED":
        return RecoveryResult("BASELINE_SUCCEEDED", tuple(steps),
                              message="Baseline succeeded; no repair needed (fidelity NOT_EVALUATED)")
    diagnosis = diagnose_attempt(baseline, _saved_log(baseline_manifest))
    if policy.max_repairs == 0:
        return RecoveryResult("REVIEW_REQUIRED", tuple(steps), diagnosis=diagnosis.to_dict(),
                              message="Repair attempts disabled by policy")
    plan = plan_append_end(bundle, entry, baseline, diagnosis, policy)
    if plan is None:
        return RecoveryResult("REVIEW_REQUIRED", tuple(steps), diagnosis=diagnosis.to_dict(),
                              message="No evidence-backed allowlisted repair; original preserved")
    attempt, repaired_manifest = convert_source(
        bundle, entry, engine, store, timeout_seconds,
        selection={"method": "explicit_m03", "entry": entry},
        repair_plan=plan, parent_run=str(baseline_manifest))
    steps.append(_attempt_summary(attempt, repaired_manifest))
    if attempt.status == "SUCCEEDED":
        return RecoveryResult("RECOVERED_UNVERIFIED", tuple(steps),
                              diagnosis=diagnosis.to_dict(), plan=plan.public_dict(),
                              message="HTML produced after bounded patch; scientific fidelity NOT_EVALUATED")
    return RecoveryResult("REVIEW_REQUIRED", tuple(steps),
                          diagnosis=diagnosis.to_dict(), plan=plan.public_dict(),
                          message="Single allowlisted repair did not produce usable HTML")


def recover_fragments(bundle: SourceBundle, fragments: tuple[str, ...],
                      engine: ConversionEngine, store: ArtifactStore,
                      document_class: str = "article", preamble: str | None = None,
                      timeout_seconds: int = 300) -> RecoveryResult:
    plan = plan_wrapper(bundle, fragments, document_class, preamble)
    attempt, manifest = convert_source(
        bundle, plan.entry, engine, store, timeout_seconds,
        selection={"method": "explicit_fragment_order", "fragments": list(fragments),
                   "preamble": preamble, "document_class": document_class},
        repair_plan=plan)
    result = "RECOVERED_UNVERIFIED" if attempt.status == "SUCCEEDED" else "REVIEW_REQUIRED"
    return RecoveryResult(result, (_attempt_summary(attempt, manifest),),
                          diagnosis={"family": "EXPLICIT_FRAGMENTS", "confidence": "user_provided"},
                          plan=plan.public_dict(),
                          message="Synthetic entry created only in private workspace; fidelity NOT_EVALUATED")
