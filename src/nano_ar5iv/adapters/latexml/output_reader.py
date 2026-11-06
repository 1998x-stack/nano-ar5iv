"""M04 immutable, checksum-verified run-artifact selection.

Only read file paths from a recorded M01/M03 manifest; no external fetch or
filesystem traversal. The original run and manifest are not changed.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from nano_ar5iv.domain.provenance import sha256_bytes, sha256_file


class InvalidArtifact(ValueError):
    """Missing, altered, unsafe or unsupported conversion output."""


@dataclass(frozen=True, slots=True)
class NormalizationInput:
    run_id: str
    bundle_id: str
    root_path: str
    input_format: str
    content: bytes
    artifact_path: str
    artifact_sha256: str
    run_manifest_sha256: str
    engine: dict


def load_run_artifact(run_manifest: Path, output_root: Path,
                      format: str = "auto", max_bytes: int = 20 * 1024 * 1024) -> NormalizationInput:
    if format not in {"auto", "xml", "html"}:
        raise InvalidArtifact("format must be auto/xml/html")
    base = Path(output_root).resolve()
    if not base.is_dir():
        raise InvalidArtifact("Configured output root does not exist")
    try:
        path = Path(run_manifest).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InvalidArtifact("Conversion run manifest is unavailable") from exc
    if not path.is_relative_to(base / "runs") or path.name != "manifest.json":
        raise InvalidArtifact("Run manifest must be inside configured output/runs")
    raw = path.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise InvalidArtifact("Run manifest exceeds size limit")
    manifest = json.loads(raw)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or re.fullmatch(r"[0-9a-f]{32}", run_id) is None or path.parent.name != run_id:
        raise InvalidArtifact("Run ID mismatch")
    bundle = manifest.get("source_bundle_id")
    if not isinstance(bundle, str) or not re.fullmatch(r"[0-9a-f]{64}", bundle):
        raise InvalidArtifact("Source bundle ID missing or invalid")
    entry = manifest.get("root_entry")
    if (not isinstance(entry, str) or not entry or entry.startswith("/")
            or "\\" in entry or ".." in entry.split("/")):
        raise InvalidArtifact("Invalid root entry")
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise InvalidArtifact("Invalid artifact records")
    by_name: dict[str, dict] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            raise InvalidArtifact("Invalid artifact item")
        name = item.get("path")
        if (not isinstance(name, str) or not name or name.startswith("/")
                or "\\" in name or any(p in {"", ".", ".."} for p in name.split("/"))):
            raise InvalidArtifact("Unsafe artifact path in manifest")
        if name in by_name:
            raise InvalidArtifact("Duplicate artifact path")
        by_name[name] = item
    xml_names = sorted(p for p in by_name if p.lower().endswith(".xml"))
    html_names = sorted(p for p in by_name if p.lower().endswith((".html", ".htm")))
    if format in {"auto", "xml"} and xml_names:
        chosen, input_format = xml_names[0], "xml"
    elif format in {"auto", "html"} and html_names:
        chosen = "html/index.html" if "html/index.html" in html_names else html_names[0]
        input_format = "html"
    else:
        raise InvalidArtifact("Requested XML/HTML output is not available in the run manifest")
    asset_path = (path.parent / "artifacts" / chosen)
    if asset_path.is_symlink() or not asset_path.resolve(strict=True).is_relative_to(
            (path.parent / "artifacts").resolve(strict=True)):
        raise InvalidArtifact("Artifact outside run directory")
    if not asset_path.is_file() or asset_path.stat().st_size > max_bytes:
        raise InvalidArtifact("Artifact absent or too large")
    item = by_name[chosen]
    if item.get("size_bytes") != asset_path.stat().st_size or item.get("sha256") != sha256_file(asset_path):
        raise InvalidArtifact("Artifact content hash/size mismatch")
    if not isinstance(manifest.get("engine_attempt"), dict):
        raise InvalidArtifact("Missing engine attempt provenance")
    attempt = manifest["engine_attempt"]
    return NormalizationInput(
        run_id, bundle, entry, input_format, asset_path.read_bytes(), chosen,
        item["sha256"], sha256_bytes(raw),
        {"name": "ar5ivist/LaTeXML", "image": attempt.get("image"),
         "image_id": attempt.get("image_id"),
         "status": attempt.get("status"), "exit_code": attempt.get("exit_code")})
