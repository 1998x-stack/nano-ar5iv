"""M05.1 does not silently equate structural content with visual equivalence."""
from __future__ import annotations
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding
from nano_ar5iv.quality.reference import Golden


def evaluate_visual(document: PaperDocument, reference: Golden | None) -> Dimension:
    has_visual = any(a.kind in {"figure", "image", "table"} for a in document.assets)
    if reference is None:
        return Dimension("NOT_RUN", (Finding("VISUAL_NOT_RUN",
                                            "No independent rendered-PDF comparison has run"),))
    if reference.expected["visual"] == "NOT_APPLICABLE":
        if has_visual:
            return Dimension("FAIL", (Finding("VISUAL_EXEMPTION_INCONSISTENT",
                                              "Visual exemption conflicts with present figures/tables"),))
        return Dimension("NOT_APPLICABLE", checked=0)
    return Dimension("NOT_RUN", (Finding("VISUAL_REQUIRED_NOT_RUN",
                                        "Real layout comparison is not implemented in M05.1"),))
