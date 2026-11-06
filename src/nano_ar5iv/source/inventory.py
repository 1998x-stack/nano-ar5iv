"""Bounded, hash-checked reads of M01 immutable source snapshots (M02)."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from nano_ar5iv.domain.provenance import sha256_file
from nano_ar5iv.domain.source import SourceBundle


class SourceReadError(ValueError):
    """Snapshot was modified or an input exceeded the M02 read budget."""


def read_source_text(bundle: SourceBundle, relative_path: str, max_bytes: int = 2_000_000) -> str:
    record = next((f for f in bundle.files if f.path == relative_path), None)
    if record is None or record.size_bytes > max_bytes:
        raise SourceReadError("Unlisted or oversized source file: " + relative_path)
    path = bundle.source_root.joinpath(*PurePosixPath(relative_path).parts)
    if path.is_symlink() or not path.is_file():
        raise SourceReadError("Unsafe snapshot file: " + relative_path)
    if path.stat().st_size != record.size_bytes or sha256_file(path) != record.sha256:
        raise SourceReadError("Snapshot hash mismatch: " + relative_path)
    return path.read_bytes().decode("utf-8", errors="replace")


def inventory(bundle: SourceBundle) -> dict:
    paths = [f.path for f in bundle.files]
    tex = [p for p in paths if Path(p).suffix.lower() in {".tex", ".ltx"}]
    pdf = [p for p in paths if Path(p).suffix.lower() == ".pdf"]
    return {"source_kind": "tex" if tex else "pdf_only" if pdf else "no_tex",
            "files": [f.to_dict() for f in bundle.files],
            "tex_files": tex, "pdf_files": pdf}
