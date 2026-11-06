"""Immutable identifiers for source snapshots and M02 entry discovery."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SourceBundle:
    bundle_id: str
    source_root: Path
    manifest_path: Path
    files: tuple[SourceFile, ...]

    def to_dict(self) -> dict:
        return {"schema_version": "1.0", "bundle_id": self.bundle_id,
                "files": [f.to_dict() for f in self.files]}


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    source: str
    kind: str
    requested: str
    line: int
    resolution: str
    target: str | None = None
    alternatives: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EntryCandidate:
    path: str
    score: int
    evidence: tuple[str, ...]
    referenced_by: tuple[str, ...]
    complete_document: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EntryDecision:
    status: str
    selected_roots: tuple[str, ...]
    candidates: tuple[EntryCandidate, ...] = ()
    edges: tuple[DependencyEdge, ...] = ()
    diagnostics: tuple[str, ...] = ()
    metadata_source: str | None = None
    compiler: str | None = None
    ignored: tuple[str, ...] = ()
    trial_results: tuple[dict, ...] = ()
    algorithm_version: str = "m02.1"

    def to_dict(self) -> dict:
        return {"schema_version": "1.0", "algorithm_version": self.algorithm_version,
                "status": self.status, "selected_roots": list(self.selected_roots),
                "candidates": [c.to_dict() for c in self.candidates],
                "edges": [e.to_dict() for e in self.edges],
                "diagnostics": list(self.diagnostics),
                "metadata_source": self.metadata_source,
                "compiler": self.compiler, "ignored": list(self.ignored),
                "trial_results": list(self.trial_results)}
