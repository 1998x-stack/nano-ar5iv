"""Generate a synthetic top-level TeX file ONLY with explicit ordered fragments."""
from __future__ import annotations
import re
from pathlib import PurePosixPath
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.domain.provenance import sha256_bytes
from nano_ar5iv.source.tex_scanner import scan_tex
from nano_ar5iv.recovery.strategies import PatchOperation, RecoveryPlan, WRAPPER

_GENERATED = "__nano_ar5iv_entry.tex"
_CLASSES = frozenset({"article", "report", "book"})
_SAFE = re.compile(r"[A-Za-z0-9_/-]+[.](?:tex|ltx)\Z")


def _verified_fragment(bundle: SourceBundle, value: str) -> str:
    if not _SAFE.fullmatch(value) or ".." in value.split("/") or value.startswith("/"):
        raise ValueError("Fragment must be a safe ASCII relative .tex/.ltx file")
    files = {f.path for f in bundle.files}
    if value not in files:
        raise ValueError(f"Fragment not included in source snapshot: {value}")
    path = bundle.source_root / value
    content = path.read_text(encoding="utf-8", errors="replace")
    parsed = scan_tex(content)
    if parsed.has_class or parsed.has_begin or parsed.has_end:
        raise ValueError(f"Fragment already has document boundaries: {value}")
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Fragment too large for explicit wrapper")
    return value


def plan_wrapper(bundle: SourceBundle, fragments: tuple[str, ...],
                 document_class: str = "article", preamble: str | None = None) -> RecoveryPlan:
    if document_class not in _CLASSES:
        raise ValueError("Document class must be an explicit supported class")
    if not 1 <= len(fragments) <= 32 or len(set(fragments)) != len(fragments):
        raise ValueError("1..32 unique, explicitly ordered fragments required")
    if _GENERATED in {f.path for f in bundle.files}:
        raise ValueError("Generated wrapper filename already exists in source")
    ordered = tuple(_verified_fragment(bundle, name) for name in fragments)
    if preamble is not None:
        _verified_fragment(bundle, preamble)
        if preamble in ordered:
            raise ValueError("Preamble file cannot also be a body fragment")
    lines = [r"\documentclass{" + document_class + "}"]
    if preamble:
        lines.append(r"\input{" + preamble + "}")
    lines.append(r"\begin{document}")
    lines.extend(r"\input{" + name + "}" for name in ordered)
    lines.extend((r"\end{document}", ""))
    payload = "\n".join(lines)
    return RecoveryPlan(
        strategy=WRAPPER, entry=_GENERATED, source_bundle_id=bundle.bundle_id,
        operations=(PatchOperation("create_wrapper", _GENERATED, payload),),
        evidence=("explicit ordered fragment selection", "explicit document class",
                  "no document boundary in selected fragments"),
        requires_review=True)
