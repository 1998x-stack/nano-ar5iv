"""Defensive directory snapshot and immutable artifact write operations (M01)."""
from __future__ import annotations
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath
from nano_ar5iv.domain.provenance import sha256_bytes, sha256_file, stable_json
from nano_ar5iv.domain.source import SourceBundle, SourceFile


class UnsafeSource(ValueError):
    """Source tree is unsafe or does not meet ingestion bounds."""


class SnapshotStore:
    def __init__(self, root: Path, max_files: int = 500, max_bytes: int = 150 * 1024 * 1024,
                 max_depth: int = 20) -> None:
        self.root = Path(root).resolve()
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.max_depth = max_depth
        if max_files < 1 or max_bytes < 1 or max_depth < 1:
            raise ValueError("Snapshot limits must be positive")

    def _file_inventory(self, source: Path) -> tuple[SourceFile, ...]:
        files: list[SourceFile] = []
        total_bytes = 0

        def walk(directory: Path, prefix: PurePosixPath, depth: int) -> None:
            nonlocal total_bytes
            if depth > self.max_depth:
                raise UnsafeSource("Source directory nesting exceeds limit")
            for entry in sorted(os.scandir(directory), key=lambda e: e.name):
                if entry.name in {".git", "__pycache__"} or entry.name.startswith(".env"):
                    raise UnsafeSource(f"Forbidden private/cache entry: {entry.name}")
                relative = prefix / entry.name
                if entry.is_symlink():
                    raise UnsafeSource(f"Symlink is not allowed: {relative}")
                if entry.is_dir(follow_symlinks=False):
                    walk(Path(entry.path), relative, depth + 1)
                elif entry.is_file(follow_symlinks=False):
                    st = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(st.st_mode):
                        raise UnsafeSource(f"Nonregular file is not allowed: {relative}")
                    if len(files) + 1 > self.max_files or total_bytes + st.st_size > self.max_bytes:
                        raise UnsafeSource("Source size/count limit exceeded")
                    total_bytes += st.st_size
                    files.append(SourceFile(str(relative), "", st.st_size))
                else:
                    raise UnsafeSource(f"Unsupported filesystem entry: {relative}")

        walk(source, PurePosixPath(), 0)
        if not files:
            raise UnsafeSource("Source directory is empty")
        return tuple(files)

    def _copy_verified(self, source_root: Path, rel: str, dst: Path, expected_size: int) -> SourceFile:
        import hashlib
        # Open each component relative to a no-follow fd to resist symlink swapping.
        parts = PurePosixPath(rel).parts
        opened = []
        dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            parent = os.open(source_root, dir_flags)
            opened.append(parent)
            for part in parts[:-1]:
                parent = os.open(part, dir_flags, dir_fd=parent)
                opened.append(parent)
            fd = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
            opened.append(fd)
            st_before = os.fstat(fd)
            if not stat.S_ISREG(st_before.st_mode) or st_before.st_size != expected_size:
                raise UnsafeSource(f"File changed or is unsafe: {rel}")
            digest = hashlib.sha256()
            with os.fdopen(fd, "rb", closefd=False) as stream, dst.open("xb") as output:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    output.write(chunk)
            st_after = os.fstat(fd)
            if (st_before.st_mtime_ns != st_after.st_mtime_ns or
                    st_before.st_size != st_after.st_size or
                    st_before.st_ino != st_after.st_ino):
                raise UnsafeSource(f"Source mutated during snapshot: {rel}")
            os.chmod(dst, 0o444)
            return SourceFile("", digest.hexdigest(), st_after.st_size)
        finally:
            for handle in reversed(opened):
                os.close(handle)

    def capture(self, source_dir: Path) -> SourceBundle:
        source = Path(source_dir)
        if source.is_symlink() or not source.is_dir():
            raise UnsafeSource("Input must be a real directory without symlink")
        source = source.resolve(strict=True)
        if self.root == source or self.root.is_relative_to(source):
            raise UnsafeSource("Store cannot be inside source tree")
        inventory = self._file_inventory(source)
        source_store = self.root / "sources"
        source_store.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=source_store))
        try:
            observed = []
            for f in inventory:
                target = staging / "files" / f.path
                target.parent.mkdir(parents=True, exist_ok=True)
                record = self._copy_verified(source, f.path, target, f.size_bytes)
                observed.append(SourceFile(f.path, record.sha256, record.size_bytes))
            fingerprint = sha256_bytes(stable_json([f.to_dict() for f in observed]))
            final = source_store / fingerprint
            manifest = {"schema_version": "1.0", "bundle_id": fingerprint,
                        "files": [f.to_dict() for f in observed]}
            (staging / "manifest.json").write_bytes(stable_json(manifest))
            # Staging remains writable for cleanup. All copied source files are read-only.
            if final.exists():
                current = json.loads((final / "manifest.json").read_text(encoding="utf-8"))
                if current != manifest:
                    raise UnsafeSource("Existing snapshot manifest collision")
                for record in observed:
                    if sha256_file(final / "files" / record.path) != record.sha256:
                        raise UnsafeSource("Existing snapshot content is corrupted")
            else:
                staging.rename(final)
            return SourceBundle(fingerprint, final / "files", final / "manifest.json", tuple(observed))
        finally:
            if staging.exists():
                shutil.rmtree(staging)


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def write_run(self, run_id: str, manifest: dict, artifacts_dir: Path) -> Path:
        if not run_id or any(ch not in "0123456789abcdef" for ch in run_id):
            raise ValueError("run_id must be a lowercase hexadecimal identifier")
        runs = self.root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        dest = runs / run_id
        temp = Path(tempfile.mkdtemp(prefix=".run-", dir=runs))
        try:
            captured = []
            total_bytes = 0
            if artifacts_dir.is_dir():
                for p in sorted(artifacts_dir.rglob("*")):
                    if p.is_symlink():
                        raise UnsafeSource("Symlink inside engine output")
                    if p.is_file():
                        rel = p.relative_to(artifacts_dir)
                        file_size = p.stat().st_size
                        total_bytes += file_size
                        if len(captured) >= 500 or file_size > 75 * 1024 * 1024 or total_bytes > 150 * 1024 * 1024:
                            raise UnsafeSource("Engine output exceeded artifact limits")
                        target = temp / "artifacts" / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(p, target)
                        captured.append({"path": rel.as_posix(), "sha256": sha256_file(target),
                                         "size_bytes": target.stat().st_size})
            manifest = {**manifest, "artifacts": captured}
            (temp / "manifest.json").write_bytes(stable_json(manifest))
            if dest.exists():
                raise FileExistsError("Run ID already exists")
            temp.rename(dest)
            return dest / "manifest.json"
        finally:
            if temp.exists():
                shutil.rmtree(temp)
