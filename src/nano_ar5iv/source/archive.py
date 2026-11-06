"""Extract trusted input archives into an empty staging directory with strict limits.

No symlinks, hard links, special entries, path traversal or recursive extraction.
The M01 SnapshotStore subsequently performs its own bounds/hash verification.
"""
from __future__ import annotations
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from nano_ar5iv.infrastructure.repositories import UnsafeSource


def _name(raw: str) -> str:
    if not raw or "\x00" in raw or "\\" in raw or raw.startswith("/") or ":" in raw:
        raise UnsafeSource("Unsafe archive path")
    # Tar commonly uses a leading "./" without implying traversal.
    while raw.startswith("./"):
        raw = raw[2:]
    if not raw or any(part in {"", ".", ".."} for part in raw.split("/")):
        raise UnsafeSource("Unsafe archive path")
    if any(part in {".git", "__pycache__"} or part.startswith(".env") for part in raw.split("/")):
        raise UnsafeSource("Forbidden private/cache archive entry")
    return str(PurePosixPath(raw))


def extract_archive(archive: Path, destination: Path, max_files: int = 500,
                    max_bytes: int = 150 * 1024 * 1024) -> None:
    source = Path(archive)
    dest = Path(destination)
    if source.is_symlink() or not source.is_file():
        raise UnsafeSource("Archive must be a regular file without symlinks")
    if not dest.is_dir() or any(dest.iterdir()):
        raise UnsafeSource("Archive destination must exist and be empty")
    total = 0
    count = 0
    used: set[str] = set()

    def emit(name: str, size: int, stream) -> None:
        nonlocal count, total
        relative = _name(name)
        if relative in used or count >= max_files or size < 0 or total + size > max_bytes:
            raise UnsafeSource("Archive duplicate or extraction limit exceeded")
        used.add(relative)
        count += 1
        total += size
        target = dest.joinpath(*PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        remaining = size
        with target.open("xb") as output:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise UnsafeSource("Truncated archive entry")
                output.write(chunk)
                remaining -= len(chunk)

    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as zf:
            for item in zf.infolist():
                name = _name(item.filename.rstrip("/") if item.is_dir() else item.filename)
                kind = (item.external_attr >> 16) & 0o170000
                if kind not in (0, stat.S_IFDIR if item.is_dir() else stat.S_IFREG):
                    raise UnsafeSource("Archive contains non-regular entry")
                if item.is_dir():
                    continue
                if item.flag_bits & 0x1 or item.file_size > max(1, item.compress_size) * 1000:
                    raise UnsafeSource("Encrypted or excessive-compression ZIP entry")
                with zf.open(item) as stream:
                    emit(name, item.file_size, stream)
    elif tarfile.is_tarfile(source):
        with tarfile.open(source, mode="r:*") as tf:
            for item in tf:
                if item.isdir():
                    _name(item.name.rstrip("/"))
                    continue
                if not item.isfile():
                    raise UnsafeSource("Archive contains link or special entry")
                stream = tf.extractfile(item)
                if stream is None:
                    raise UnsafeSource("Cannot read TAR member")
                with stream:
                    emit(item.name, item.size, stream)
    else:
        raise UnsafeSource("Unsupported archive type (expected ZIP/TAR)")
    if not count:
        raise UnsafeSource("Archive has no regular files")
