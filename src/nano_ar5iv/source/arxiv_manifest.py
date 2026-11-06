"""Read modern and legacy arXiv 00README without executing metadata."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.source.inventory import read_source_text


class ManifestError(ValueError):
    """Invalid, contradictory, or unsafe metadata."""


@dataclass(frozen=True)
class ManifestHints:
    roots: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    included: tuple[str, ...] = ()
    metadata_source: str | None = None
    compiler: str | dict | None = None
    diagnostics: tuple[str, ...] = ()


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ManifestError("Invalid 00README filename")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ManifestError("00README path traversal")
    return value


def parse_manifest(bundle: SourceBundle) -> ManifestHints:
    names = {f.path for f in bundle.files}
    modern_roots: list[str] = []
    modern_ignore: list[str] = []
    modern_include: list[str] = []
    legacy_roots: list[str] = []
    legacy_ignore: list[str] = []
    legacy_include: list[str] = []
    diagnostics: list[str] = []
    compiler = None
    if "00README.json" in names:
        try:
            obj = json.loads(read_source_text(bundle, "00README.json", 100_000))
            if not isinstance(obj, dict) or not isinstance(obj.get("sources"), list):
                raise ManifestError("00README.json requires a sources array")
            process = obj.get("process", {})
            compiler = process.get("compiler") if isinstance(process, dict) else None
            declarations = obj["sources"]
            for item in declarations:
                if not isinstance(item, dict):
                    raise ManifestError("00README sources entry must be an object")
                filename = safe_path(item.get("filename"))
                usage = item.get("usage", "toplevel" if len(declarations) == 1 else "include")
                if usage not in {"toplevel", "include", "ignore"}:
                    raise ManifestError("Unsupported 00README usage: " + str(usage))
                (modern_roots if usage == "toplevel" else modern_ignore if usage == "ignore"
                 else modern_include).append(filename)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ManifestError("Invalid 00README.json: " + str(exc)) from exc
    if "00README.XXX" in names:
        for raw in read_source_text(bundle, "00README.XXX", 100_000).splitlines():
            stripped = raw.split("#", 1)[0].strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) != 2 or parts[1].lower() not in {"toplevelfile", "ignore", "include"}:
                continue  # Preserve unsupported arXiv switches without interpreting them.
            name = safe_path(parts[0])
            action = parts[1].lower()
            (legacy_roots if action == "toplevelfile" else legacy_ignore if action == "ignore"
             else legacy_include).append(name)
    if modern_roots and legacy_roots and modern_roots != legacy_roots:
        diagnostics.append("metadata_conflict: modern and legacy top-level declarations differ")
    roots = modern_roots if "00README.json" in names else legacy_roots
    ignore = modern_ignore if "00README.json" in names else legacy_ignore
    include = modern_include if "00README.json" in names else legacy_include
    if set(roots) & set(ignore):
        raise ManifestError("A top-level file is also ignored")
    for value in roots:
        if value not in names:
            diagnostics.append("missing_metadata_root: " + value)
        elif PurePosixPath(value).suffix.lower() not in {".tex", ".ltx"}:
            diagnostics.append("metadata_root_not_tex: " + value)
    return ManifestHints(tuple(dict.fromkeys(roots)), tuple(dict.fromkeys(ignore)),
                         tuple(dict.fromkeys(include)),
                         "00README.json" if "00README.json" in names else
                         "00README.XXX" if "00README.XXX" in names else None,
                         compiler, tuple(diagnostics))
