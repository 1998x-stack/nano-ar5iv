"""Read arXiv modern 00README.json and legacy 00README.XXX, without executing TeX.

Declared roots are authoritative only when paths and metadata are valid.
Conflicts and malformed manifests must not silently fall back to a guessed root.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from nano_ar5iv.domain.source import SourceBundle


def safe_relative(value: str) -> bool:
    return (isinstance(value, str) and bool(value) and "\x00" not in value
            and "\\" not in value and not value.startswith("/")
            and all(p not in ("", ".", "..") for p in value.split("/"))
            and PurePosixPath(value).as_posix() == value)


@dataclass(frozen=True)
class ManifestInfo:
    source: str | None = None
    roots: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    compiler: str | None = None
    errors: tuple[str, ...] = ()
    explicit: bool = False


def read_manifest(bundle: SourceBundle) -> ManifestInfo:
    paths = {item.path for item in bundle.files}
    modern = "00README.json" if "00README.json" in paths else None
    legacy = sorted(p for p in paths
                    if p.startswith("00README.") and p != "00README.json")
    if modern and legacy:
        return ManifestInfo(source=modern, errors=("Conflicting modern and legacy README manifests",))
    if len(legacy) > 1:
        return ManifestInfo(source=",".join(legacy), errors=("Multiple legacy README manifests",))
    if not modern and not legacy:
        return ManifestInfo()
    src = modern or legacy[0]
    try:
        text = (bundle.source_root / src).read_text("utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as exc:
        return ManifestInfo(source=src, errors=(f"Unable to read manifest: {exc.__class__.__name__}",))

    roots: list[str] = []
    ignored: list[str] = []
    errors: list[str] = []
    compiler = None
    explicit = False

    if modern:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return ManifestInfo(source=src, errors=("Invalid 00README.json syntax",))
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            return ManifestInfo(source=src, errors=("00README.json must contain a sources array",))
        process = data.get("process", {})
        if isinstance(process, dict) and isinstance(process.get("compiler"), str):
            compiler = process["compiler"]
        sources = data["sources"]
        if not sources:
            return ManifestInfo(source=src, errors=("Empty sources array",))
        entries: list[tuple[str, str | None]] = []
        for i, item in enumerate(sources):
            if not isinstance(item, dict):
                errors.append(f"sources[{i}] is not an object")
                continue
            name, usage = item.get("filename"), item.get("usage")
            if not safe_relative(name):
                errors.append(f"Unsafe filename in sources[{i}]")
                continue
            if usage is not None and usage not in ("toplevel", "include", "ignore"):
                errors.append(f"Unknown usage for {name}")
                continue
            entries.append((name, usage))
        explicit = any(usage == "toplevel" for _, usage in entries)
        # Unmarked source entries are top-level only when no explicit root exists.
        # Ambiguous mixed metadata gets surfaced by discovery, never silently merged.
        for name, usage in entries:
            if usage == "ignore":
                ignored.append(name)
            elif usage == "toplevel" or (not explicit and usage is None):
                roots.append(name)
    else:
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("%"):
                continue
            words = line.split()
            if len(words) < 2:
                continue  # e.g., nohypertex or a legacy directive we do not model
            name, directive = words[:2]
            if directive not in ("toplevelfile", "ignore", "include"):
                continue
            if not safe_relative(name):
                errors.append(f"Unsafe legacy path on line {i}")
                continue
            if directive == "toplevelfile":
                roots.append(name)
                explicit = True
            elif directive == "ignore":
                ignored.append(name)

    if len(set(roots)) != len(roots):
        errors.append("Duplicate top-level entries")
    if set(roots) & set(ignored):
        errors.append("Top-level entry also ignored")
    for name in roots:
        if name not in paths:
            errors.append(f"Declared top-level file is missing: {name}")
        elif PurePosixPath(name).suffix.lower() not in {".tex", ".ltx"}:
            errors.append(f"Unsupported top-level file type: {name}")
    return ManifestInfo(src, tuple(roots), tuple(sorted(set(ignored))),
                        compiler, tuple(errors), explicit)
