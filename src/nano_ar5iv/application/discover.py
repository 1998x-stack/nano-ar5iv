"""M02: discover probable TeX entrypoints from one verified immutable bundle."""
from __future__ import annotations
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.source.arxiv_manifest import ManifestError, parse_manifest
from nano_ar5iv.source.dependency_graph import dependency_graph
from nano_ar5iv.source.entry_ranker import rank_entries
from nano_ar5iv.source.inventory import inventory, read_source_text
from nano_ar5iv.source.tex_scanner import scan_tex


def discover_entries(bundle: SourceBundle) -> dict:
    listing = inventory(bundle)
    result = {"schema_version": "1.0", "source_bundle_id": bundle.bundle_id,
              "inventory": listing, "graph": {"edges": [], "referenced_by": {}, "diagnostics": []}}
    if not listing["tex_files"]:
        result["decision"] = {"status": "PDF_ONLY" if listing["pdf_files"] else "NO_TEX",
                              "selected_roots": [], "candidates": [],
                              "metadata_source": None, "diagnostics": [],
                              "algorithm_version": "m02.1"}
        return result
    scans = {p: scan_tex(read_source_text(bundle, p)) for p in listing["tex_files"]}
    graph = dependency_graph(scans, set(listing["tex_files"]))
    result["graph"] = graph
    try:
        hints = parse_manifest(bundle)
    except ManifestError as exc:
        result["decision"] = {"status": "REVIEW_REQUIRED", "selected_roots": [],
                              "candidates": [], "metadata_source": "invalid",
                              "diagnostics": [str(exc)], "algorithm_version": "m02.1"}
        return result
    result["decision"] = rank_entries(scans, graph, hints)
    return result
