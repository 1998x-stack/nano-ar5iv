"""M03 fail-closed policy for externally specified TeX fragment wrappers.

Never rewrite author source; reject paths that could change TeX syntax or escape
the immutable snapshot. Unsupported class/path patterns must be reviewed.
"""
from __future__ import annotations

import re
from nano_ar5iv.domain.source import SourceBundle

_ALLOWED_CLASSES = frozenset({"article", "report", "book", "amsart"})
_FRAGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:tex|ltx)$")


class UnsafeRecovery(ValueError):
    """Recovery proposal violates evidence or immutable-source rules."""


def validate_fragments(bundle: SourceBundle, fragments: tuple[str, ...], documentclass: str) -> None:
    if documentclass not in _ALLOWED_CLASSES:
        raise UnsafeRecovery("Document class must be explicitly selected from article/report/book/amsart")
    if not 1 <= len(fragments) <= 10 or len(set(fragments)) != len(fragments):
        raise UnsafeRecovery("Specify 1..10 unique fragment paths in explicit order")
    files = {f.path for f in bundle.files}
    for rel in fragments:
        if (not _FRAGMENT.fullmatch(rel) or rel.startswith("/") or
                any(part in {"", ".", ".."} for part in rel.split("/"))):
            raise UnsafeRecovery("Fragment path is unsafe or not supported")
        if rel not in files:
            raise UnsafeRecovery("Fragment is not in immutable snapshot: " + rel)
    if "__nano_ar5iv_wrapper.tex" in files:
        raise UnsafeRecovery("Reserved generated wrapper path already exists")
