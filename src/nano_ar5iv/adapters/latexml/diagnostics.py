"""Baseline LaTeXML warning/error/fatal diagnostic extraction (M01)."""
from __future__ import annotations
import re
from nano_ar5iv.domain.diagnostics import Diagnostic

_PATTERN = re.compile(r"(?:^|\n)\s*(Warning|Error|Fatal):\s*([^\n]{0,800})", re.IGNORECASE)


def parse_diagnostics(log: str, max_events: int = 1000) -> tuple[Diagnostic, ...]:
    return tuple(Diagnostic(match.group(1).upper(), match.group(2).strip())
                 for _, match in zip(range(max_events), _PATTERN.finditer(log)))
