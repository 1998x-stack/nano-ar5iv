"""M05 image/figure presence and table-content evidence, no asset downloading."""
from __future__ import annotations
from pathlib import PurePosixPath
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding
from nano_ar5iv.quality.reference import Golden


def _rows(asset: object) -> list[list[dict]]:
    return [[{"text": c.text, "rowspan": c.rowspan, "colspan": c.colspan} for c in row]
            for row in asset.table_rows]


def evaluate_assets(document: PaperDocument, reference: Golden | None,
                    verified_artifacts: dict[str, str]) -> Dimension:
    errors: list[Finding] = []
    uncertain: list[Finding] = []
    figures = [a for a in document.assets if a.kind in {"figure", "image"}]
    tables = [a for a in document.assets if a.kind == "table"]
    for item in figures:
        if item.availability == "UNSAFE_PATH" or (
                item.availability == "UNSAFE_OR_INLINE"
                and not (item.href or "").startswith("data:")):
            errors.append(Finding("UNSAFE_ASSET_URI",
                                  "Figure has an unsafe local/active resource URI",
                                  item.id, item.href))
        elif item.availability == "MISSING_REFERENCE" or (
                item.availability == "UNSAFE_OR_INLINE"
                and (item.href or "").startswith("data:")):
            uncertain.append(Finding("INLINE_OR_UNMAPPED_FIGURE",
                                     "Inline SVG/data image or missing URI cannot be hash-verified",
                                     item.id, item.href))
        elif item.availability == "EXTERNAL_UNFETCHED":
            uncertain.append(Finding("EXTERNAL_FIGURE_UNCHECKED",
                                     "Remote figure not downloaded or compared", item.id))
        elif item.href:
            path = item.href.lstrip("./")
            # Figure URI must be an exact safe relative path to an artifact in the run.
            if (not path or "\\" in path or ".." in path.split("/") or
                    PurePosixPath(path).is_absolute() or "?" in path or "#" in path):
                errors.append(Finding("UNSAFE_FIGURE_REF", "Figure URI is unsafe", item.id))
            elif path not in verified_artifacts and "html/" + path not in verified_artifacts:
                uncertain.append(Finding("FIGURE_CONTENT_UNAVAILABLE",
                                         "No SHA256-verified referenced image in this run", item.id, path))
    for table in tables:
        if not table.table_rows or any(not row for row in table.table_rows):
            errors.append(Finding("TABLE_EMPTY", "Recognized table contains no cells", table.id))
        elif any(c.rowspan < 1 or c.colspan < 1 for row in table.table_rows for c in row):
            errors.append(Finding("TABLE_INVALID_SPAN", "Invalid table cell spans", table.id))
    if reference is not None:
        expected_figs = reference.expected["figures"]
        if len(figures) != len(expected_figs):
            errors.append(Finding("FIGURE_COUNT_MISMATCH",
                                  "Figure count differs from golden",
                                  observed=f"{len(figures)} != {len(expected_figs)}"))
        for observed, golden in zip(figures, expected_figs):
            if observed.href != golden["href"]:
                errors.append(Finding("FIGURE_HREF_MISMATCH",
                                      "Figure resource URI differs from golden", observed.id))
            path = observed.href or ""
            actual_hash = verified_artifacts.get(path) or verified_artifacts.get("html/" + path)
            if actual_hash is None:
                uncertain.append(Finding("FIGURE_HASH_NOT_VERIFIED",
                                         "Referenced file lacks a verified local artifact", observed.id))
            elif actual_hash != golden["sha256"]:
                errors.append(Finding("FIGURE_HASH_MISMATCH",
                                      "Figure file differs from golden SHA256", observed.id))
        expected_tables = reference.expected["tables"]
        if len(tables) != len(expected_tables):
            errors.append(Finding("TABLE_COUNT_MISMATCH", "Table count differs from golden"))
        for observed, target in zip(tables, expected_tables):
            if _rows(observed) != target["rows"]:
                errors.append(Finding("TABLE_CELL_MISMATCH",
                                      "Cell text/spans differ from golden", observed.id))
    if errors:
        return Dimension("FAIL", tuple(errors + uncertain), len(document.assets))
    if reference is None:
        return Dimension("UNKNOWN", tuple(uncertain) + (
            Finding("ASSETS_NO_GOLDEN", "Asset set has no source-bound independent reference"),),
                         len(document.assets))
    if uncertain:
        return Dimension("UNKNOWN", tuple(uncertain), len(document.assets))
    return Dimension("PASS", checked=len(document.assets))
