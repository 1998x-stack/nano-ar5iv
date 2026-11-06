"""M04 versioned, provenance-aware scientific-paper intermediate representation.

No field here certifies scientific fidelity; every M04 document is NOT_EVALUATED.
M04 never fabricates LaTeX source locations from HTML positions.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"
NORMALIZER_VERSION = "m04.1"


@dataclass(frozen=True, slots=True)
class DocumentNode:
    id: str
    kind: str
    parent_id: str | None = None
    title: str | None = None
    text: str | None = None
    source_id: str | None = None
    source_ref: str | None = None  # Only explicit, verified TeX source mapping
    children: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Equation:
    id: str
    source_tex: str | None = None
    presentation_mathml: str | None = None
    parent_id: str | None = None
    source_id: str | None = None
    source_ref: str | None = None
    verified: bool = False


@dataclass(frozen=True, slots=True)
class Asset:
    id: str
    kind: str
    href: str | None
    caption: str | None = None
    parent_id: str | None = None
    source_id: str | None = None
    availability: str = "NOT_CHECKED"


@dataclass(frozen=True, slots=True)
class Citation:
    id: str
    kind: str  # citation or reference
    target_ref: str | None
    text: str
    parent_id: str | None = None
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class Relation:
    source_id: str
    kind: str  # cites or references
    requested_target: str | None
    target_id: str | None = None
    resolution: str = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class UnknownNode:
    id: str
    tag: str
    source_id: str | None
    raw_markup: str
    truncated: bool = False


@dataclass(slots=True)
class PaperDocument:
    document_id: str
    root_path: str
    source_kind: str
    engine: dict[str, Any]
    provenance: dict[str, Any]
    nodes: list[DocumentNode] = field(default_factory=list)
    equations: list[Equation] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    unknown_nodes: list[UnknownNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_status: str = "NOT_EVALUATED"
    schema_version: str = SCHEMA_VERSION
    normalizer_version: str = NORMALIZER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
