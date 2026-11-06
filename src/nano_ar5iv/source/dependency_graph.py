"""Static, evidence-only TeX include and resource dependency graph (M02).

arXiv compiles from the submission root. Probe root-relative targets first;
a second plausible child-relative match is reported as ambiguity, not guessed.
"""
from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import PurePosixPath
from nano_ar5iv.domain.source import DependencyEdge, SourceBundle
from nano_ar5iv.source.tex_scanner import TeXScan, scan_tex

_INCLUDE = frozenset({"input", "include", "subfile", "import", "subimport",
                      "inputfrom", "includefrom", "subincludefrom"})
_RESOURCES = {"includegraphics": (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"),
              "bibliography": (".bib",), "addbibresource": (".bib",),
              "usepackage": (".sty",), "RequirePackage": (".sty",),
              "documentclass": (".cls",)}


@dataclass(frozen=True)
class GraphResult:
    scans: dict[str, TeXScan]
    edges: tuple[DependencyEdge, ...]
    diagnostics: tuple[str, ...]


def _normalized_path(value: str) -> str | None:
    if not value or "\\" in value or "\x00" in value or value.startswith("/"):
        return None
    candidate = posixpath.normpath(value)
    if candidate in ("", ".", "..") or candidate.startswith("../"):
        return None
    return candidate


def _possible_paths(origin: str, requested: str, suffixes: tuple[str, ...], available: set[str]) -> tuple[str, ...]:
    requested = requested.strip()
    if not requested:
        return ()
    roots = [requested, posixpath.join(posixpath.dirname(origin), requested)]
    found: set[str] = set()
    for raw in roots:
        safe = _normalized_path(raw)
        if safe is None:
            continue
        proposals = [safe] if PurePosixPath(safe).suffix else [safe + ext for ext in suffixes]
        for candidate in proposals:
            if candidate in available:
                found.add(candidate)
    return tuple(sorted(found))


def build_graph(bundle: SourceBundle, ignored: tuple[str, ...] = (),
                max_tex_bytes: int = 8 * 1024 * 1024) -> GraphResult:
    available = {f.path for f in bundle.files}
    tex_paths = sorted(p for p in available if PurePosixPath(p).suffix.lower() in {".tex", ".ltx"})
    scans: dict[str, TeXScan] = {}
    diagnostics: list[str] = []
    edges: list[DependencyEdge] = []
    for path in tex_paths:
        f = next(f for f in bundle.files if f.path == path)
        if f.size_bytes > max_tex_bytes:
            diagnostics.append(f"TeX file exceeds static scan budget: {path}")
            continue
        try:
            content = (bundle.source_root / path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            diagnostics.append(f"Cannot read TeX file {path}: {exc.__class__.__name__}")
            continue
        if "\ufffd" in content:
            diagnostics.append(f"Unrecognized encoding replaced during scan: {path}")
        scan = scan_tex(content)
        scans[path] = scan
        for ref in scan.references:
            if ref.dynamic:
                edges.append(DependencyEdge(path, ref.kind, ref.value, ref.line, "dynamic"))
                diagnostics.append(f"Dynamic TeX reference {path}:{ref.line}: {ref.value}")
                continue
            if ref.kind in _INCLUDE:
                suffixes = (".tex", ".ltx")
            elif ref.kind in _RESOURCES:
                suffixes = _RESOURCES[ref.kind]
            else:
                continue
            options = _possible_paths(path, ref.value, suffixes, available)
            if len(options) == 1:
                resolution, target = "resolved", options[0]
            elif len(options) > 1:
                resolution, target = "ambiguous", None
                diagnostics.append(f"Ambiguous TeX reference {path}:{ref.line}: {ref.value}")
            elif ref.kind in {"usepackage", "RequirePackage", "documentclass"}:
                resolution, target = "external", None  # TeXLive package is not necessarily in source
            else:
                resolution, target = "missing", None
                if ref.kind in _INCLUDE:
                    diagnostics.append(f"Missing TeX include {path}:{ref.line}: {ref.value}")
            edges.append(DependencyEdge(path, ref.kind, ref.value, ref.line,
                                        resolution, target, options if len(options) > 1 else ()))
    return GraphResult(scans, tuple(edges), tuple(diagnostics))
