"""M04 preserves unresolved scientific cross-references instead of guessing."""
from __future__ import annotations
from urllib.parse import unquote, urlsplit
from nano_ar5iv.domain.documents import Citation, Relation


def normalized_target(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None
    if value.startswith("#"):
        return unquote(value[1:]) or None
    if "://" in value:
        return None  # external references must never be claimed as local
    if "#" in value:
        # A distinct document's fragment cannot be resolved in this PaperDocument.
        return None
    if value.startswith(("mailto:", "/", ".", "\\")) or ".." in value.split("/"):
        return None
    return value


def build_relations(citations: list[Citation], id_index: dict[str, str]) -> list[Relation]:
    relations: list[Relation] = []
    for citation in citations:
        key = normalized_target(citation.target_ref)
        target = id_index.get(key) if key else None
        relations.append(Relation(
            source_id=citation.id,
            kind="cites" if citation.kind == "citation" else "references",
            requested_target=citation.target_ref,
            target_id=target,
            resolution="RESOLVED" if target else "UNRESOLVED"))
    return relations
