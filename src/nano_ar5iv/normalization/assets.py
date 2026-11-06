"""M04 local asset reference extraction. No network access or implicit copying."""
from __future__ import annotations
from urllib.parse import urlsplit


def classify_asset_href(href: str | None) -> str:
    if not href:
        return "MISSING_REFERENCE"
    value = href.strip()
    if value.startswith(("data:", "javascript:", "file:")):
        return "UNSAFE_OR_INLINE"
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"}:
        return "EXTERNAL_UNFETCHED"
    if parsed.scheme or parsed.netloc or value.startswith(("/", "\\")):
        return "UNSAFE_PATH"
    if "\\" in value or ".." in parsed.path.split("/") or not parsed.path:
        return "UNSAFE_PATH"
    return "NOT_CHECKED"
