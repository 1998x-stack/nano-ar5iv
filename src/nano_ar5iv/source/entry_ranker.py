"""Metadata-first root selection; heuristic scores are NOT probabilities."""
from __future__ import annotations
from nano_ar5iv.source.arxiv_manifest import ManifestHints


def rank_entries(scans: dict[str, dict], graph: dict, hints: ManifestHints) -> dict:
    candidates = []
    ignored = set(hints.ignored)
    for name, obs in sorted(scans.items()):
        if name in ignored:
            continue
        incoming = graph["referenced_by"].get(name, [])
        score = (8 * int(obs["has_documentclass"]) + 5 * int(obs["has_begin_document"])
                 + 3 * int(obs["has_end_document"]) + 6 * int(obs["has_plain_tex_bye"])
                 - 9 * int(bool(incoming)))
        candidates.append({"path": name, "score": score,
                           "evidence": [k for k in ("has_documentclass", "has_begin_document",
                                                    "has_end_document", "has_plain_tex_bye") if obs[k]],
                           "referenced_by": incoming,
                           "diagnostics": obs["diagnostics"]})
    candidates.sort(key=lambda x: (-x["score"], x["path"]))
    valid_meta = [r for r in hints.roots if r in scans and r not in ignored]
    issues = list(hints.diagnostics) + graph["diagnostics"]
    issues.extend(d for obs in scans.values() for d in obs["diagnostics"])
    if hints.roots:
        if len(valid_meta) != len(hints.roots) or hints.diagnostics:
            status, selected = "REVIEW_REQUIRED", valid_meta
        else:
            selected = valid_meta
            status = "MULTIPLE_ROOTS" if len(selected) > 1 else "SELECTED"
    else:
        complete = [c["path"] for c in candidates if not c["referenced_by"] and
                    ((scans[c["path"]]["has_documentclass"] and scans[c["path"]]["has_begin_document"])
                     or scans[c["path"]]["has_plain_tex_bye"])]
        if not complete:
            status, selected = "REVIEW_REQUIRED", []
            issues.append("no_complete_root")
        elif len(complete) > 1:
            status, selected = "MULTIPLE_ROOTS", complete
        else:
            status, selected = "SELECTED", complete
    if any(str(d).startswith(("unresolved_dynamic:", "ambiguous_dependency:", "unsafe_dependency:"))
           for d in issues) and status == "SELECTED":
        status = "REVIEW_REQUIRED"
    return {"status": status, "selected_roots": selected, "candidates": candidates,
            "metadata_source": hints.metadata_source, "compiler": hints.compiler,
            "diagnostics": sorted(set(issues)), "algorithm_version": "m02.1"}
