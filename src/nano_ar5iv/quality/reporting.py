"""M05 policy: explicit evidence semantics; no unknown/not-run is a PASS."""
from __future__ import annotations
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding, QualityReport
from nano_ar5iv.quality.assets import evaluate_assets
from nano_ar5iv.quality.bibliography import evaluate_bibliography
from nano_ar5iv.quality.mathematical import evaluate_mathematics
from nano_ar5iv.quality.reference import Golden
from nano_ar5iv.quality.structural import evaluate_structure
from nano_ar5iv.quality.visual import evaluate_visual


def assess_document(document: PaperDocument, derivation_id: str, document_sha256: str,
                    reference: Golden | None,
                    verified_artifacts: dict[str, str]) -> QualityReport:
    """ACCEPTED means *supplied, source-bound golden assertions* passed, not general truth.

    A native XML document and an applicable visual exemption are necessary;
    HTML fallback and unparsed scientific structures must remain uncertain.
    """
    dimensions = {
        "structure": evaluate_structure(document, reference),
        "mathematics": evaluate_mathematics(document, reference),
        "bibliography": evaluate_bibliography(document, reference),
        "assets": evaluate_assets(document, reference, verified_artifacts),
        "visual": evaluate_visual(document, reference),
    }
    concerns = []
    if document.source_kind != "latex_xml":
        concerns.append(Finding("HTML_OR_UNKNOWN_PROVENANCE",
                                "Lossy HTML reconstruction cannot prove source-level scientific fidelity"))
    if document.unknown_nodes:
        concerns.append(Finding("UNKNOWN_SCIENTIFIC_STRUCTURES",
                                "Some semantic structures were not fully interpreted",
                                observed=str(len(document.unknown_nodes))))
    if any(node.truncated for node in document.unknown_nodes):
        concerns.append(Finding("TRUNCATED_UNKNOWN_MARKUP", "Unknown semantic markup truncated"))
    if document.warnings:
        concerns.append(Finding("NORMALIZER_WARNINGS",
                                "Normalizer emitted warnings requiring review",
                                observed=",".join(document.warnings)[:250]))
    if document.engine.get("status") != "SUCCEEDED" or document.engine.get("exit_code") != 0:
        dimensions["provenance"] = Dimension(
            "FAIL", (Finding("CONVERSION_NOT_SUCCESSFUL",
                             "Source conversion did not record a successful engine attempt"),))
    elif concerns:
        dimensions["provenance"] = Dimension("UNKNOWN", tuple(concerns))
    else:
        dimensions["provenance"] = Dimension("PASS", checked=1)
    if reference is not None and (
            reference.source_bundle_id != document.provenance.get("source_bundle_id")
            or reference.root_path != document.root_path):
        dimensions["provenance"] = Dimension(
            "FAIL", (Finding("GOLDEN_SOURCE_MISMATCH",
                             "Golden source/root is not the immutable document source"),))
    statuses = {name: dimension.status for name, dimension in dimensions.items()}
    if "FAIL" in statuses.values():
        decision = "REJECTED"
    elif reference is not None and all(
        status == "PASS" or (name == "visual" and status == "NOT_APPLICABLE")
        for name, status in statuses.items()
    ):
        decision = "ACCEPTED"
    elif reference is not None and "NOT_RUN" not in statuses.values() and (
        "PASS" in statuses.values()
    ):
        decision = "PARTIAL"
    else:
        decision = "REVIEW_REQUIRED"
    codes = tuple(sorted({finding.code for dimension in dimensions.values()
                          for finding in dimension.findings}))
    provenance = {
        "run_id": document.provenance.get("run_id"),
        "source_bundle_id": document.provenance.get("source_bundle_id"),
        "source_kind": document.source_kind,
        "reference_supplied": reference is not None,
        "reference_reviewer_claim": reference.reviewer if reference else None,
        "reference_evidence_method_claim": reference.evidence_method if reference else None,
        "reference_identity_independently_authenticated": False,
        "scope": "source-bound, explicitly supplied golden assertions; not universal scientific truth",
    }
    return QualityReport(document.document_id, derivation_id, document_sha256,
                         reference.sha256 if reference else None,
                         dimensions, decision, codes, provenance)
