"""Strict, user-supplied, source-bound golden assertions for M05.

This module cannot authenticate a claimed reviewer. Reports identify the
reference as a supplied claim, NEVER as independently verified by the tool.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from nano_ar5iv.domain.provenance import sha256_bytes


class InvalidGolden(ValueError):
    pass


_REQUIRED = {"sections", "paragraphs_contain", "equations", "citations",
             "bibliography", "figures", "tables", "visual"}
_EXPECT_KEYS = _REQUIRED
_TOKEN = re.compile(r"^[0-9a-f]{64}$")
_LIMIT = 1024 * 1024


@dataclass(frozen=True, slots=True)
class Golden:
    source_bundle_id: str
    root_path: str
    reviewer: str
    evidence_method: str
    expected: dict
    sha256: str


def _array_strings(value: object, field: str) -> None:
    if not isinstance(value, list) or len(value) > 1000 or any(
        not isinstance(s, str) or not s.strip() or len(s) > 4096 for s in value
    ):
        raise InvalidGolden(f"{field} must be a bounded list of nonempty strings")


def _object_list(value: object, key: str, keys: set[str], mandatory: set[str]) -> None:
    if not isinstance(value, list) or len(value) > 1000:
        raise InvalidGolden(f"{key} must be a bounded list")
    for i, obj in enumerate(value):
        if not isinstance(obj, dict) or set(obj) - keys or not mandatory <= set(obj):
            raise InvalidGolden(f"{key}[{i}] has invalid keys")
        for k, v in obj.items():
            if k == "mathml_tokens":
                _array_strings(v, f"{key}[{i}].mathml_tokens")
            elif k == "rows":
                if not isinstance(v, list) or len(v) > 1000:
                    raise InvalidGolden("Table rows must be bounded lists")
                for row in v:
                    if not isinstance(row, list) or len(row) > 200:
                        raise InvalidGolden("Table row is not a bounded list")
                    for cell in row:
                        if not isinstance(cell, dict) or set(cell) != {"text", "rowspan", "colspan"}:
                            raise InvalidGolden("Expected table cells must have text,rowspan,colspan")
                        if not isinstance(cell["text"], str) or len(cell["text"]) > 8192:
                            raise InvalidGolden("Invalid table cell text")
                        for span in ("rowspan", "colspan"):
                            if type(cell[span]) is not int or not 1 <= cell[span] <= 1000:
                                raise InvalidGolden("Invalid table cell span")
            elif not isinstance(v, str) or not v.strip() or len(v) > 8192:
                raise InvalidGolden(f"{key}[{i}].{k} must be a bounded string")
        if key == "equations" and not ("tex" in obj or "mathml_tokens" in obj):
            raise InvalidGolden("Every equation assertion needs tex and/or MathML tokens")
        if key == "figures" and not _TOKEN.fullmatch(obj["sha256"]):
            raise InvalidGolden("Expected figure needs a SHA256")


def parse_golden(raw: bytes) -> Golden:
    if not raw or len(raw) > _LIMIT:
        raise InvalidGolden("Golden file absent or larger than 1 MiB")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise InvalidGolden("Invalid golden JSON") from exc
    if not isinstance(data, dict) or set(data) != {
        "schema_version", "source_bundle_id", "root_path", "review", "expected"
    } or data["schema_version"] != "1.0":
        raise InvalidGolden("Unsupported or incomplete golden schema")
    bundle = data["source_bundle_id"]
    root = data["root_path"]
    review = data["review"]
    if not isinstance(bundle, str) or not _TOKEN.fullmatch(bundle):
        raise InvalidGolden("Golden is not bound to a SHA256 source bundle")
    if not isinstance(root, str) or not root or "\\" in root or "\x00" in root or root.startswith("/") or any(
        p in {"", ".", ".."} for p in root.split("/")
    ):
        raise InvalidGolden("Unsafe root name")
    if not isinstance(review, dict) or set(review) != {"reviewer", "evidence_method"}:
        raise InvalidGolden("Review provenance is required")
    for k in ("reviewer", "evidence_method"):
        if not isinstance(review[k], str) or not review[k].strip() or len(review[k]) > 300:
            raise InvalidGolden("Invalid review provenance field")
    expected = data["expected"]
    if not isinstance(expected, dict) or set(expected) != _EXPECT_KEYS:
        raise InvalidGolden("Each quality dimension must be explicit (including empty arrays)")
    for key in ("sections", "paragraphs_contain"):
        _array_strings(expected[key], key)
    _object_list(expected["equations"], "equations", {"tex", "mathml_tokens"}, set())
    _object_list(expected["citations"], "citations", {"kind", "target"}, {"kind", "target"})
    _object_list(expected["bibliography"], "bibliography", {"source_id", "text"}, {"source_id", "text"})
    _object_list(expected["figures"], "figures", {"href", "sha256"}, {"href", "sha256"})
    _object_list(expected["tables"], "tables", {"rows"}, {"rows"})
    if expected["visual"] not in {"REQUIRED", "NOT_APPLICABLE"}:
        raise InvalidGolden("Visual review must be REQUIRED or NOT_APPLICABLE")
    if any(x["kind"] not in {"citation", "reference"} for x in expected["citations"]):
        raise InvalidGolden("Unknown citation kind")
    # The digest is the exact user-provided file bytes for auditability.
    return Golden(bundle, root, review["reviewer"], review["evidence_method"],
                  expected, sha256_bytes(raw))


def load_golden(path: Path) -> Golden:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise InvalidGolden("Golden must be a local regular file, not a symlink")
    if target.stat().st_size > _LIMIT:
        raise InvalidGolden("Golden file exceeds 1 MiB")
    return parse_golden(target.read_bytes())
