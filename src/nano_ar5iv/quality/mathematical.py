"""M05 equation retention checks; independent symbols must be supplied by a golden."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from nano_ar5iv.domain.documents import PaperDocument
from nano_ar5iv.ports.quality import Dimension, Finding
from nano_ar5iv.quality.reference import Golden


def mathml_tokens(markup: str) -> tuple[str, ...]:
    if not isinstance(markup, str) or not markup.strip() or len(markup) > 1024 * 1024:
        raise ValueError("MathML absent or too large")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", markup, re.IGNORECASE):
        raise ValueError("DTD/entities not allowed in MathML")
    try:
        root = ET.fromstring(markup)
    except ET.ParseError as exc:
        raise ValueError("Malformed MathML") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "math":
        raise ValueError("Not a MathML math root")
    tokens = []
    count = 0
    for element in root.iter():
        count += 1
        if count > 5000:
            raise ValueError("MathML exceeds element budget")
        if element.tag.rsplit("}", 1)[-1] in {"mi", "mo", "mn", "mtext"}:
            token = " ".join("".join(element.itertext()).split())
            if token:
                tokens.append(token)
    if not tokens:
        raise ValueError("No independently comparable MathML tokens")
    return tuple(tokens)


def evaluate_mathematics(document: PaperDocument, reference: Golden | None) -> Dimension:
    problems: list[Finding] = []
    unknowns: list[Finding] = []
    actual_tokens: list[tuple[str, ...] | None] = []
    for item in document.equations:
        try:
            actual_tokens.append(mathml_tokens(item.presentation_mathml or ""))
        except ValueError as exc:
            actual_tokens.append(None)
            problems.append(Finding("MATHML_UNUSABLE", str(exc), item.id))
    if reference is None:
        if problems:
            return Dimension("FAIL", tuple(problems), len(document.equations))
        return Dimension("UNKNOWN", (Finding("MATH_NO_GOLDEN",
                                            "MathML presence does not establish symbol fidelity"),),
                         len(document.equations))
    expected = reference.expected["equations"]
    if len(expected) != len(document.equations):
        problems.append(Finding("EQUATION_COUNT_MISMATCH",
                                "Equation count differs from independent golden",
                                observed=f"observed={len(document.equations)} expected={len(expected)}"))
    for index, (target, item) in enumerate(zip(expected, document.equations)):
        if "tex" in target:
            if item.source_tex is None:
                unknowns.append(Finding("SOURCE_TEX_UNAVAILABLE",
                                        "Expected TeX is absent from conversion IR", item.id))
            elif item.source_tex.strip() != target["tex"].strip():
                problems.append(Finding("EQUATION_TEX_MISMATCH",
                                        "Formula TeX differs from golden", item.id))
        if "mathml_tokens" in target:
            if actual_tokens[index] is not None and list(actual_tokens[index]) != target["mathml_tokens"]:
                problems.append(Finding("MATH_SYMBOL_MISMATCH",
                                        "MathML token sequence differs from golden", item.id,
                                        observed=repr(actual_tokens[index])[:250]))
        elif actual_tokens[index] is not None:
            unknowns.append(Finding("MATH_SYMBOLS_NOT_ATTESTED",
                                    "Golden does not contain comparable MathML tokens", item.id))
    if problems:
        return Dimension("FAIL", tuple(problems + unknowns), len(document.equations))
    if unknowns:
        return Dimension("UNKNOWN", tuple(unknowns), len(document.equations))
    return Dimension("PASS", checked=len(document.equations))
