"""M05 bibliography and cross-reference closure, keeping unknowns explicit."""
from __future__ import annotations
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding
from nano_ar5iv.quality.reference import Golden
from nano_ar5iv.normalization.citation_graph import normalized_target


def evaluate_bibliography(document: PaperDocument, reference: Golden | None) -> Dimension:
    findings: list[Finding] = []
    object_ids = {x.id for items in (document.nodes, document.equations, document.assets)
                  for x in items}
    citation_ids = {c.id for c in document.citations}
    relation_sources = {r.source_id for r in document.relations}
    if citation_ids != relation_sources or len(document.relations) != len(document.citations):
        findings.append(Finding("CITATION_EDGE_COUNT_MISMATCH",
                                "Every citation must have exactly one relation"))
    for relation in document.relations:
        if relation.resolution != "RESOLVED" or relation.target_id not in object_ids:
            findings.append(Finding("UNRESOLVED_SCIENTIFIC_REFERENCE",
                                    "Citation/crossref lacks a valid target",
                                    relation.source_id, relation.requested_target))
    if reference is not None:
        expected_refs = sorted((x["kind"], normalized_target(x["target"]) or x["target"])
                               for x in reference.expected["citations"])
        actual_refs = sorted((c.kind, normalized_target(c.target_ref) or c.target_ref)
                             for c in document.citations)
        if actual_refs != expected_refs:
            findings.append(Finding("CITATION_GOLDEN_MISMATCH",
                                    "Observed citation target list differs from golden"))
        expected_bib = sorted((x["source_id"], x["text"])
                              for x in reference.expected["bibliography"])
        actual_bib = sorted((x.source_id, x.text)
                            for x in document.nodes if x.kind == "bibliography_item")
        if actual_bib != expected_bib:
            findings.append(Finding("BIBLIOGRAPHY_GOLDEN_MISMATCH",
                                    "Bibliography ID/text differs from golden"))
    if findings:
        return Dimension("FAIL", tuple(findings), len(document.citations))
    if reference is None:
        return Dimension("UNKNOWN", (Finding("BIB_NO_GOLDEN",
                                            "Reference closure does not prove bibliography completeness"),),
                         len(document.citations))
    return Dimension("PASS", checked=len(document.citations))
