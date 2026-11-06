"""First-cause-oriented classification of LaTeXML diagnostics (M03).

Classifications are hints, not proof that an author submitted malformed TeX.
"""
from __future__ import annotations
import re
from dataclasses import asdict, dataclass
from nano_ar5iv.ports.engines import EngineAttempt


@dataclass(frozen=True, slots=True)
class FailureDiagnosis:
    family: str
    first_evidence: str
    confidence: str = "heuristic"

    def to_dict(self) -> dict:
        return asdict(self)


_RULES: tuple[tuple[str, re.Pattern], ...] = (
    ("MISSING_PACKAGE", re.compile(r"(?i)(?:not found|missing|cannot find|couldn't find).{0,80}\.(?:sty|cls)\b|"
                                   r"(?:\.(?:sty|cls)).{0,80}(?:not found|missing|cannot find)")),
    ("MISSING_INPUT", re.compile(r"(?i)(?:not found|missing|cannot find).{0,80}\.(?:tex|ltx)\b|"
                                 r"(?:\.(?:tex|ltx)).{0,80}(?:not found|missing|cannot find)")),
    ("UNKNOWN_MACRO", re.compile(r"(?i)(undefined control sequence|undefined macro|unknown control sequence)")),
    ("MATH_PARSE", re.compile(r"(?i)(math parsing|math mode|mathml|unexpected math)")),
    ("ASSET_MISSING", re.compile(r"(?i)(graphic|image|figure).{0,80}(?:not found|missing|unknown)")),
    ("BIB_MISSING", re.compile(r"(?i)(bibliograph|bibtex|citation).{0,80}(?:not found|missing|undefined)")),
)


def diagnose_attempt(attempt: EngineAttempt, log_text: str = "") -> FailureDiagnosis:
    if attempt.timed_out or attempt.status == "TIMED_OUT":
        return FailureDiagnosis("TIMEOUT", "Conversion runtime exceeded limit", "confirmed")
    if attempt.status == "ENGINE_UNAVAILABLE":
        return FailureDiagnosis("ENGINE_UNAVAILABLE", attempt.error or "Docker image unavailable", "confirmed")
    if attempt.status == "OUTPUT_MISSING":
        return FailureDiagnosis("OUTPUT_MISSING", "HTML output missing or empty", "confirmed")
    if attempt.status == "SUCCEEDED":
        return FailureDiagnosis("NONE", "Baseline converter returned success", "confirmed")
    # Prefer earliest meaningful diagnostic; subsequent errors may cascade.
    lines = [line.strip() for line in log_text.splitlines()
             if line.strip() and len(line.strip()) < 2000]
    for line in lines[:200]:
        if not (re.search(r"(?i)\b(error|fatal|warning)\b", line) or
                re.search(r"(?i)(not found|missing|undefined)", line)):
            continue
        for family, pattern in _RULES:
            if pattern.search(line):
                return FailureDiagnosis(family, line[:250])
    return FailureDiagnosis("UNCLASSIFIED", (lines[0][:250] if lines else "No useful diagnostics"))
