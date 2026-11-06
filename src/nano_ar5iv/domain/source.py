"""Immutable identifiers for content-addressed TeX source bundles (M01)."""
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
