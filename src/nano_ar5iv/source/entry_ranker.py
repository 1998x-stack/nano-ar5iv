"""Metadata-first deterministic root resolution with explicit abstention (M02)."""
from __future__ import annotations

from pathlib import PurePosixPath
from nano_ar5iv.domain.source import EntryCandidate, EntryDecision, SourceBundle
from nano_ar5iv.source.arxiv_manifest import read_manifest
from nano_ar5iv.source.dependency_graph import build_graph

_INCLUDE = frozenset({"input", "include", "subfile", "import", "subimport",
                      "inputfrom", "includefrom", "subincludefrom"})


def discover_roots(bundle: SourceBundle) -> EntryDecision:
    metadata = read_manifest(bundle)
    available_tex = tuple(sorted(f.path for f in bundle.files
                                 if PurePosixPath(f.path).suffix.lower() in (".tex", ".ltx")))
    if metadata.errors:
        return EntryDecision("MANIFEST_ERROR", (), diagnostics=metadata.errors,
                             metadata_source=metadata.source, compiler=metadata.compiler,
                             ignored=metadata.ignored)
    if not available_tex:
        return EntryDecision("NO_TEX", (), diagnostics=("No .tex/.ltx source files",),
                             metadata_source=metadata.source, ignored=metadata.ignored)

    graph = build_graph(bundle, metadata.ignored)
    incoming: dict[str, set[str]] = {p: set() for p in available_tex}
    for edge in graph.edges:
        if edge.kind in _INCLUDE and edge.resolution == "resolved" and edge.target in incoming:
            incoming[edge.target].add(edge.source)

    candidates: list[EntryCandidate] = []
    for path in available_tex:
        if path in metadata.ignored:
            continue
        scan = graph.scans.get(path)
        if scan is None:
            continue
        score = 0
        reasons = []
        for value, weight, reason in (
            (scan.has_class, 10, "documentclass"),
            (scan.has_begin, 8, "begin_document"),
            (scan.has_end, 3, "end_document"),
            (scan.has_section, 2, "sections"),
        ):
            if value:
                score += weight
                reasons.append(reason)
        if incoming[path]:
            score -= 15
            reasons.append("included_by_other")
        else:
            reasons.append("not_included")
        candidates.append(EntryCandidate(path, score, tuple(reasons),
                                         tuple(sorted(incoming[path])),
                                         bool(scan.has_class and scan.has_begin)))
    candidates.sort(key=lambda c: (-c.score, c.path))
    diagnostics = list(graph.diagnostics)

    if metadata.roots:
        return EntryDecision(
            "MULTIPLE_ROOTS" if len(metadata.roots) > 1 else "SELECTED",
            metadata.roots, tuple(candidates), graph.edges, tuple(diagnostics),
            metadata.source, metadata.compiler, metadata.ignored
        )

    independent = [c for c in candidates if c.complete_document and not c.referenced_by]
    if len(independent) > 1:
        return EntryDecision("MULTIPLE_ROOTS", tuple(c.path for c in independent),
                             tuple(candidates), graph.edges, tuple(diagnostics),
                             metadata.source, metadata.compiler, metadata.ignored)
    if len(independent) == 1:
        return EntryDecision("SELECTED", (independent[0].path,), tuple(candidates),
                             graph.edges, tuple(diagnostics),
                             metadata.source, metadata.compiler, metadata.ignored)
    diagnostics.append("No unique, complete, independent TeX entrypoint; explicit review required")
    return EntryDecision("AMBIGUOUS", (), tuple(candidates), graph.edges,
                         tuple(diagnostics), metadata.source, metadata.compiler, metadata.ignored)
