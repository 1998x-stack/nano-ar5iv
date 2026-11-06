"""M03.1 deterministic, evidence-first log triage (heuristic, not proven causality)."""
from __future__ import annotations

import re

from nano_ar5iv.adapters.latexml.diagnostics import parse_diagnostics

_PATTERNS = (
    ("BIB_MISSING", re.compile(r"(\.bib\b|bibliograph|bibtex|biber).*(missing|not found|can't find|cannot find)|(?:missing|not found|can't find|cannot find).*(\.bib\b|bibliograph)", re.I)),
    ("ASSET_MISSING", re.compile(r"(?:image|graphics|figure|\.png\b|\.jpg\b|\.pdf\b|\.eps\b).*(?:not found|missing|cannot find|can't find)|(?:not found|missing|cannot find|can't find).*(?:image|graphics|figure|\.png\b|\.jpg\b|\.pdf\b|\.eps\b)", re.I)),
    ("DEPENDENCY_MISSING", re.compile(r"(?:not found|missing|cannot find|can't find|no file).*(?:\.sty\b|\.cls\b|\.tex\b|\.ltx\b)|(?:\.sty\b|\.cls\b|\.tex\b|\.ltx\b).*(?:not found|missing|cannot find|can't find)", re.I)),
    ("UNKNOWN_MACRO", re.compile(r"undefined control sequence|undefined macro|unknown macro|unrecognized control sequence|unknown control sequence", re.I)),
    ("MATH_PARSE", re.compile(r"math(?:emath|ml)?[ -]?(?:parse|syntax|error)|missing \$ inserted|math mode", re.I)),
)


def classify_failure(log: str, *, status: str = "FAILED", exit_code: int | None = None,
                     timed_out: bool = False, max_log_chars: int = 2_000_000) -> dict:
    """Identify first *observed* error; preserve cascade count without asserting root cause.

    A zero exit status with error-level diagnostics is not accepted as verified.
    """
    if not isinstance(log, str):
        raise TypeError("log must be text")
    if len(log) > max_log_chars or max_log_chars < 1:
        raise ValueError("Log size exceeds classification limit")
    events = parse_diagnostics(log)
    fatal = [event for event in events if event.severity in {"ERROR", "FATAL"}]
    first = fatal[0] if fatal else None
    if timed_out or status == "TIMED_OUT":
        category, evidence = "TIMEOUT", "engine exceeded execution limit"
    elif status == "ENGINE_UNAVAILABLE":
        category, evidence = "ENGINE_UNAVAILABLE", "engine not available locally"
    elif first is not None:
        evidence = first.message[:800]
        category = next((key for key, pattern in _PATTERNS if pattern.search(evidence)), "UNCLASSIFIED")
    elif status == "OUTPUT_MISSING":
        category, evidence = "OUTPUT_MISSING", "expected conversion output is absent"
    elif exit_code is not None and exit_code != 0:
        category, evidence = "PROCESS_FAILED", "nonzero process exit without parsed error"
    elif status == "SUCCEEDED":
        category, evidence = "NO_ERROR_OBSERVED", "no error-level log diagnostic"
    else:
        category, evidence = "UNCLASSIFIED", "insufficient diagnostics"
    return {
        "schema_version": "1.0",
        "category": category,
        "first_observed_error": evidence,
        "error_events": len(fatal),
        "cascade_events_after_first": max(0, len(fatal) - 1),
        "warning_events": sum(event.severity == "WARNING" for event in events),
        "exit_code": exit_code,
        "engine_status": status,
        "confidence": "HEURISTIC" if first is not None else "UNCONFIRMED",
        "root_cause_proven": False,
        "review_required": True  # No log error cannot establish scientific fidelity.,
        "truncated_diagnostics": len(events) == 1000,
    }
