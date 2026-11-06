"""Small, versioned conversion diagnostics model (M01 baseline)."""
from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: str
    message: str
    source: str = "latexml"

    def to_dict(self) -> dict:
        return asdict(self)
