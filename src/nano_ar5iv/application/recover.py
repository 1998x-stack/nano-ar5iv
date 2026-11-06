"""M03 recovery orchestration: explicit, one-shot synthetic wrapper only.

Plans are audit-only unless an explicit caller supplies an engine and executes.
No author input file is rewritten and no conversion is called VERIFIED.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.domain.provenance import sha256_file, stable_json
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore
from nano_ar5iv.infrastructure.workspaces import attempt_workspace
from nano_ar5iv.ports.engines import ConversionEngine
from nano_ar5iv.recovery.patch_policy import UnsafeRecovery
from nano_ar5iv.recovery.planner import WrapperPlan, create_wrapper_plan
from nano_ar5iv.recovery.wrapper import render_wrapper


def save_plan(plan: WrapperPlan, output_root: Path) -> Path:
    location = Path(output_root).resolve() / "recoveries" / plan.plan_id
    location.mkdir(parents=True, exist_ok=True)
    target = location / "plan.json"
    content = stable_json(plan.to_dict())
    if target.exists():
        if target.read_bytes() != content:
            raise UnsafeRecovery("Existing recovery plan differs for same plan ID")
    else:
        with target.open("xb") as stream:
            stream.write(content)
    return target


def execute_wrapper(bundle: SourceBundle, plan: WrapperPlan, engine: ConversionEngine,
                    output_root: Path, timeout_seconds: int = 180) -> tuple[dict, Path]:
    """Apply a reviewed explicit plan to a fresh copy; run at most one conversion."""
    if not 1 <= timeout_seconds <= 600:
        raise ValueError("Recovery timeout must be 1..600 seconds")
    expected = create_wrapper_plan(bundle, plan.fragments, plan.documentclass)
    if expected != plan or plan.source_bundle_id != bundle.bundle_id:
        raise UnsafeRecovery("Plan does not match source snapshot or deterministic policy")
    output = Path(output_root).resolve()
    save_plan(plan, output)
    with attempt_workspace(bundle) as workdir:
        generated = workdir / plan.generated_entry
        with generated.open("x", encoding="utf-8") as f:
            f.write(render_wrapper(plan.fragments, plan.documentclass))
        if sha256_file(generated) != plan.generated_sha256:
            raise UnsafeRecovery("Generated patch hash mismatch")
        patched = SnapshotStore(output).capture(workdir)
    source_hashes = {f.path: f.sha256 for f in bundle.files}
    new_hashes = {f.path: f.sha256 for f in patched.files}
    if any(new_hashes.get(k) != v for k, v in source_hashes.items()):
        raise UnsafeRecovery("Original file changed in derived snapshot")
    if set(new_hashes) != set(source_hashes) | {plan.generated_entry}:
        raise UnsafeRecovery("Derived snapshot must add exactly one generated file")
    attempt, manifest_file = convert_source(patched, plan.generated_entry, engine,
                                            ArtifactStore(output), timeout_seconds)
    report = {
        "schema_version": "1.0", "plan_id": plan.plan_id,
        "original_bundle_id": bundle.bundle_id, "derived_bundle_id": patched.bundle_id,
        "generated_entry": plan.generated_entry, "generated_sha256": plan.generated_sha256,
        "original_files_unchanged": True,
        "attempt_manifest_path": str(manifest_file),
        "engine_status": attempt.status, "engine_exit_code": attempt.exit_code,
        "status": "REVIEW_REQUIRED", "quality_status": "NOT_EVALUATED",
        "attempt_count": 1, "synthetic_root": True,
        "warning": "Engine success does not verify math, citations or scientific fidelity",
    }
    location = output / "recoveries" / plan.plan_id
    unique = location / ("attempt-" + uuid.uuid4().hex + ".json")
    with unique.open("xb") as stream:
        stream.write(stable_json(report))
    return report, unique
