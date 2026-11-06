"""M01 conversion: explicit entry only, one attempt, immutable provenance."""
from __future__ import annotations
import json
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.infrastructure.repositories import ArtifactStore
from nano_ar5iv.infrastructure.workspaces import attempt_workspace
from nano_ar5iv.ports.engines import ConversionEngine, EngineAttempt
from nano_ar5iv.recovery.strategies import RecoveryPlan, APPEND_END, WRAPPER
from nano_ar5iv.recovery.patch_policy import apply_plan
from nano_ar5iv.domain.provenance import stable_json


class InvalidEntry(ValueError):
    pass


def validate_entry(bundle: SourceBundle, entry: str) -> str:
    if not entry or "\\" in entry or "\x00" in entry:
        raise InvalidEntry("Entry must be a safe forward-slash relative path")
    path = PurePosixPath(entry)
    if path.is_absolute() or any(p in {"..", "."} for p in entry.split("/")) or path.suffix.lower() not in {".tex", ".ltx"}:
        raise InvalidEntry("Explicit .tex/.ltx entry is required for M01")
    if entry not in {f.path for f in bundle.files}:
        raise InvalidEntry("Entry is not present in the immutable snapshot")
    return entry


def convert_source(bundle: SourceBundle, entry: str, engine: ConversionEngine,
                   store: ArtifactStore, timeout_seconds: int = 300,
                   selection: dict | None = None,
                   repair_plan: RecoveryPlan | None = None,
                   parent_run: str | None = None) -> tuple[EngineAttempt, Path]:
    if repair_plan is None or repair_plan.strategy == APPEND_END:
        entry = validate_entry(bundle, entry)
    elif repair_plan.strategy == WRAPPER:
        if entry != repair_plan.entry or entry in {f.path for f in bundle.files}:
            raise InvalidEntry("Synthetic wrapper must have a new reserved entry")
    else:
        raise InvalidEntry("Unknown recovery strategy")
    run_id = uuid.uuid4().hex
    with attempt_workspace(bundle) as workspace:
        patch_evidence = apply_plan(workspace, bundle, repair_plan) if repair_plan else None
        attempt = engine.convert(workspace, entry, timeout_seconds)
        with tempfile.TemporaryDirectory(prefix="nano-ar5iv-artifacts-") as tmp:
            artifact_dir = Path(tmp)
            for src in sorted(workspace.rglob("*.latexml.log")):
                if src.is_symlink():
                    raise ValueError("Symlink output rejected")
                dest = artifact_dir / "logs" / src.relative_to(workspace)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            for name in ("engine.stdout.txt", "engine.stderr.txt"):
                src = workspace / name
                if src.is_file() and not src.is_symlink():
                    (artifact_dir / name).write_bytes(src.read_bytes())
            html = workspace / "html"
            if html.is_dir():
                shutil.copytree(html, artifact_dir / "html", symlinks=True)
            if patch_evidence:
                (artifact_dir / "repair.diff").write_text(patch_evidence.diff, encoding="utf-8")
                (artifact_dir / "repair-audit.json").write_bytes(stable_json({
                    "plan": repair_plan.public_dict(), "evidence": patch_evidence.to_dict(),
                    "parent_run": parent_run}))
            manifest = {"schema_version": "1.0", "run_id": run_id,
                        "source_bundle_id": bundle.bundle_id, "root_entry": entry,
                        "engine_attempt": attempt.to_dict(),
                        "quality_status": "NOT_EVALUATED",
                        "source_manifest": str(bundle.manifest_path),
                        "entry_selection": selection or {"method": "explicit", "entry": entry},
                        "repair_audit": patch_evidence.to_dict() if patch_evidence else None,
                        "parent_run": parent_run}
            return attempt, store.write_run(run_id, manifest, artifact_dir)
