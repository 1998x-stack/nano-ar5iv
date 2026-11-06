"""M02 bounded top-k baseline probes (process evidence only, never scientific acceptance)."""
from __future__ import annotations
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.application.discover import discover_entries
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.infrastructure.repositories import ArtifactStore
from nano_ar5iv.ports.engines import ConversionEngine


def probe_candidates(bundle: SourceBundle, engine: ConversionEngine, store: ArtifactStore,
                     top_k: int = 3, timeout_seconds: int = 90) -> dict:
    if not 1 <= top_k <= 5 or not 1 <= timeout_seconds <= 600:
        raise ValueError("Probe limits: top_k=1..5 and timeout=1..600 seconds")
    discovery = discover_entries(bundle)
    decision = discovery["decision"]
    findings = {"schema_version": "1.0", "source_bundle_id": bundle.bundle_id,
                "discovery_status": decision["status"], "quality_status": "NOT_EVALUATED",
                "auto_selected": False, "attempts": [], "warnings": []}
    if decision["status"] in {"PDF_ONLY", "NO_TEX"}:
        findings["warnings"].append("no_tex_source")
        return findings
    if decision.get("metadata_source") == "invalid" or any(
        str(d).startswith(("missing_metadata_root:", "metadata_root_not_tex:", "metadata_conflict:"))
        for d in decision["diagnostics"]
    ):
        findings["warnings"].append("metadata_invalid_no_probes")
        return findings
    roots = decision["selected_roots"] or [c["path"] for c in decision["candidates"]]
    selected = list(dict.fromkeys(roots))[:top_k]
    for entry in selected:
        attempt, path = convert_source(bundle, entry, engine, store, timeout_seconds)
        findings["attempts"].append({"entry": entry, "status": attempt.status,
                                     "exit_code": attempt.exit_code,
                                     "diagnostic_count": attempt.diagnostic_count,
                                     "manifest_path": str(path)})
    findings["warnings"].append("process_success_does_not_imply_math_or_citation_fidelity")
    return findings
