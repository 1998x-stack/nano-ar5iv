"""M05 verified PaperDocument + optional golden -> immutable quality report.

Never mutates source snapshots, conversion runs or canonical PaperDocuments.
A QualityReport does not automatically modify PaperDocument.quality_status.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from nano_ar5iv.domain.documents import (
    Asset, Citation, DocumentNode, Equation, PaperDocument, Relation,
    TableCell, UnknownNode,
)
from nano_ar5iv.domain.provenance import sha256_bytes, sha256_file, stable_json
from nano_ar5iv.ports.quality import POLICY_VERSION, QualityReport
from nano_ar5iv.quality.reference import Golden, load_golden
from nano_ar5iv.quality.reporting import assess_document


class InvalidEvidence(ValueError):
    pass


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RUN = re.compile(r"[0-9a-f]{32}\Z")


def _safe_json(path: Path, limit: int = 20 * 1024 * 1024) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise InvalidEvidence("Evidence file missing, symlinked or too large")
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidEvidence("Malformed evidence JSON") from exc
    if not isinstance(data, dict):
        raise InvalidEvidence("Evidence JSON must be an object")
    return data, raw


def _document(data: dict) -> PaperDocument:
    if data.get("schema_version") != "1.0" or data.get("quality_status") != "NOT_EVALUATED":
        raise InvalidEvidence("Only unevaluated M04 PaperDocument schema 1.0 is supported")
    try:
        nodes = [DocumentNode(**{**row, "children": tuple(row.get("children", []))})
                 for row in data["nodes"]]
        equations = [Equation(**row) for row in data["equations"]]
        assets = [Asset(**{**row, "table_rows": tuple(
            tuple(TableCell(**cell) for cell in line)
            for line in row.get("table_rows", []))}) for row in data["assets"]]
        citations = [Citation(**row) for row in data["citations"]]
        relations = [Relation(**row) for row in data["relations"]]
        unknowns = [UnknownNode(**row) for row in data["unknown_nodes"]]
        doc = PaperDocument(
            document_id=data["document_id"], root_path=data["root_path"],
            source_kind=data["source_kind"], engine=data["engine"],
            provenance=data["provenance"], nodes=nodes, equations=equations,
            assets=assets, citations=citations, relations=relations,
            unknown_nodes=unknowns, warnings=data["warnings"],
            quality_status=data["quality_status"], schema_version=data["schema_version"],
            normalizer_version=data["normalizer_version"])
        if stable_json(doc.to_dict()) != stable_json(data):
            raise InvalidEvidence("Unexpected/unsupported IR fields")
        if (not isinstance(doc.document_id, str) or
                not isinstance(doc.provenance, dict) or not isinstance(doc.engine, dict)):
            raise InvalidEvidence("Incorrect IR types")
        return doc
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise InvalidEvidence("Invalid PaperDocument structure") from exc


def _safe_relpath(value: str) -> bool:
    return (isinstance(value, str) and bool(value) and "\\" not in value and
            not value.startswith("/") and all(p not in {"", ".", ".."} for p in value.split("/")))


def _load_evidence(document_path: Path, output_root: Path) -> tuple[
    PaperDocument, str, str, dict[str, str]
]:
    output = Path(output_root).resolve(strict=True)
    root = output / "normalizations"
    path = Path(document_path)
    if path.is_symlink():
        raise InvalidEvidence("Symlink document path")
    try:
        path = path.resolve(strict=True)
    except OSError as exc:
        raise InvalidEvidence("Missing normalized document") from exc
    if not path.is_relative_to(root) or path.name != "paper-document.json":
        raise InvalidEvidence("Document outside normalization store")
    run_id = path.parent.parent.name
    derivation_id = path.parent.name
    if not _RUN.fullmatch(run_id) or not _SHA.fullmatch(derivation_id):
        raise InvalidEvidence("Malformed normalization derivation path")
    manifest, _ = _safe_json(path.parent / "normalization-manifest.json", 1024 * 1024)
    if (manifest.get("run_id") != run_id or
            manifest.get("derivation_id") != derivation_id or
            manifest.get("normalizer_version") != "m04.1"):
        raise InvalidEvidence("Normalization manifest is inconsistent")
    encoded, raw = _safe_json(path)
    digest = sha256_bytes(raw)
    if manifest.get("paper_document_sha256") != digest:
        raise InvalidEvidence("PaperDocument content hash mismatch")
    document = _document(encoded)
    if document.provenance.get("run_id") != run_id:
        raise InvalidEvidence("PaperDocument run ID does not match derivation")
    run_path = output / "runs" / run_id / "manifest.json"
    run, run_raw = _safe_json(run_path, 2 * 1024 * 1024)
    if sha256_bytes(run_raw) != document.provenance.get("source_run_manifest_sha256"):
        raise InvalidEvidence("Original conversion manifest has changed")
    if (run.get("root_entry") != document.root_path or
            run.get("source_bundle_id") != document.provenance.get("source_bundle_id") or
            run.get("run_id") != run_id):
        raise InvalidEvidence("Conversion run source provenance mismatch")
    if not _SHA.fullmatch(str(document.provenance.get("source_bundle_id", ""))):
        raise InvalidEvidence("Missing valid source bundle ID")
    if document.engine.get("status") != run.get("engine_attempt", {}).get("status"):
        raise InvalidEvidence("Engine status differs from original conversion")
    # Revalidate the M01 immutable source snapshot, not just its metadata reference.
    bundle_id = document.provenance["source_bundle_id"]
    snapshot_root = output / "sources" / bundle_id
    snapshot, _ = _safe_json(snapshot_root / "manifest.json", 2 * 1024 * 1024)
    if snapshot.get("bundle_id") != bundle_id:
        raise InvalidEvidence("Source snapshot bundle identity mismatch")
    file_records = snapshot.get("files", [])
    if not isinstance(file_records, list) or len(file_records) > 500:
        raise InvalidEvidence("Invalid source inventory")
    for record in file_records:
        if not isinstance(record, dict):
            raise InvalidEvidence("Invalid source inventory item")
        filename = record.get("path")
        digest = record.get("sha256")
        if not _safe_relpath(filename) or not _SHA.fullmatch(str(digest or "")):
            raise InvalidEvidence("Unsafe source inventory path")
        source_file = snapshot_root / "files" / filename
        if (source_file.is_symlink() or
                not source_file.resolve(strict=False).is_relative_to((snapshot_root / "files").resolve()) or
                not source_file.is_file() or source_file.stat().st_size != record.get("size_bytes") or
                sha256_file(source_file) != digest):
            raise InvalidEvidence("Immutable source snapshot has changed")

    recorded = {x.get("path"): x for x in run.get("artifacts", []) if isinstance(x, dict)}
    input_ref = document.provenance.get("input_artifact")
    if not _safe_relpath(input_ref) or input_ref not in recorded:
        raise InvalidEvidence("Missing normalization input artifact in original run")
    if (recorded[input_ref].get("sha256") != document.provenance.get("input_sha256")
            or recorded[input_ref].get("sha256") != manifest.get("input_sha256")):
        raise InvalidEvidence("Original conversion input hash differs from derivation")
    verified: dict[str, str] = {}
    artifact_root = run_path.parent / "artifacts"
    if len(recorded) > 500:
        raise InvalidEvidence("Too many recorded artifacts")
    for name, item in recorded.items():
        if not _safe_relpath(name) or not _SHA.fullmatch(str(item.get("sha256", ""))):
            raise InvalidEvidence("Unsafe artifact record")
        asset = artifact_root / name
        if asset.is_symlink() or not asset.resolve(strict=False).is_relative_to(artifact_root.resolve()):
            raise InvalidEvidence("Artifact path traversal/symlink")
        if not asset.is_file() or item.get("size_bytes") != asset.stat().st_size:
            raise InvalidEvidence("Missing or changed artifact file")
        if sha256_file(asset) != item["sha256"]:
            raise InvalidEvidence("Artifact checksum mismatch")
        verified[name] = item["sha256"]
    return document, derivation_id, digest, verified


def evaluate_run(document_path: Path, output_root: Path,
                 golden_path: Path | None = None) -> tuple[QualityReport, Path]:
    document, derivation, document_sha, verified = _load_evidence(document_path, output_root)
    golden = load_golden(golden_path) if golden_path is not None else None
    report = assess_document(document, derivation, document_sha, golden, verified)
    run_id = document.provenance["run_id"]
    evidence_key = sha256_bytes(stable_json({
        "derivation": derivation, "document_sha256": document_sha,
        "reference_sha256": golden.sha256 if golden else None,
        "policy_version": POLICY_VERSION,
    }))
    output = Path(output_root).resolve()
    parent = output / "quality-reports" / run_id / derivation
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / evidence_key
    report_raw = stable_json(report.to_dict())
    report_manifest = {
        "schema_version": "1.0", "policy_version": POLICY_VERSION,
        "report_id": evidence_key, "decision": report.decision,
        "document_sha256": document_sha,
        "reference_sha256": golden.sha256 if golden else None,
        "quality_report_sha256": sha256_bytes(report_raw),
    }
    if destination.exists():
        file = destination / "quality-report.json"
        manifest_path = destination / "quality-manifest.json"
        saved, raw = _safe_json(file)
        saved_manifest, _ = _safe_json(manifest_path, 1024 * 1024)
        if raw != report_raw or saved_manifest != report_manifest:
            raise InvalidEvidence("Existing quality report has changed or is inconsistent")
        return report, file
    staged = Path(tempfile.mkdtemp(prefix=".quality-", dir=parent))
    try:
        (staged / "quality-report.json").write_bytes(report_raw)
        (staged / "quality-manifest.json").write_bytes(stable_json(report_manifest))
        staged.rename(destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return report, destination / "quality-report.json"
