"""M04 immutable conversion-run -> versioned PaperDocument derivation.

Never edits a prior source snapshot or conversion attempt. Never claims quality
acceptance; M05 must separately validate content fidelity.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from nano_ar5iv.adapters.latexml.output_reader import load_run_artifact
from nano_ar5iv.domain.documents import NORMALIZER_VERSION, PaperDocument, SCHEMA_VERSION
from nano_ar5iv.domain.provenance import sha256_bytes, sha256_file, stable_json
from nano_ar5iv.normalization.html_to_ir import normalize_latexml_html
from nano_ar5iv.normalization.xml_to_ir import normalize_latexml_xml


def normalize_run(run_manifest: Path, output_root: Path,
                  preferred_format: str = "auto") -> tuple[PaperDocument, Path]:
    artifact = load_run_artifact(run_manifest, output_root, preferred_format)
    provenance = {
        "run_id": artifact.run_id, "source_bundle_id": artifact.bundle_id,
        "root_entry": artifact.root_path,
        "source_run_manifest_sha256": artifact.run_manifest_sha256,
        "input_artifact": artifact.artifact_path,
        "input_sha256": artifact.artifact_sha256,
        "source_span_status": "NOT_AVAILABLE",
    }
    parser = normalize_latexml_xml if artifact.input_format == "xml" else normalize_latexml_html
    document = parser(artifact.content, bundle_id=artifact.bundle_id,
                      root_path=artifact.root_path,
                      provenance=provenance, engine=artifact.engine)
    payload = stable_json(document.to_dict())
    derivation_id = sha256_bytes(stable_json({
        "run_id": artifact.run_id, "input_sha256": artifact.artifact_sha256,
        "normalizer_version": NORMALIZER_VERSION,
        "schema_version": SCHEMA_VERSION, "format": artifact.input_format,
    }))
    destination_parent = Path(output_root).resolve() / "normalizations" / artifact.run_id
    destination_parent.mkdir(parents=True, exist_ok=True)
    destination = destination_parent / derivation_id
    report = {
        "schema_version": "1.0", "normalizer_version": NORMALIZER_VERSION,
        "derivation_id": derivation_id, "run_id": artifact.run_id,
        "input_format": artifact.input_format, "input_sha256": artifact.artifact_sha256,
        "paper_document_sha256": sha256_bytes(payload),
        "quality_status": "NOT_EVALUATED",
    }
    if destination.exists():
        docfile = destination / "paper-document.json"
        reportfile = destination / "normalization-manifest.json"
        if (not docfile.is_file() or not reportfile.is_file()
                or sha256_file(docfile) != report["paper_document_sha256"]
                or json.loads(reportfile.read_bytes()) != report):
            raise ValueError("Previously normalized derivation is inconsistent or tampered")
        return document, docfile
    staged = Path(tempfile.mkdtemp(prefix=".normalize-", dir=destination_parent))
    try:
        (staged / "paper-document.json").write_bytes(payload)
        (staged / "normalization-manifest.json").write_bytes(stable_json(report))
        staged.rename(destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return document, destination / "paper-document.json"
