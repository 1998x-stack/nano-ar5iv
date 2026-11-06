"""Conservative allowlist of M03 recovery operations.

No package synthesis, mass regex rewriting, or unconstrained LLM patches.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

APPEND_END = "APPEND_END_DOCUMENT"
WRAPPER = "EXPLICIT_FRAGMENT_WRAPPER"
ALLOWED_STRATEGIES = frozenset({APPEND_END, WRAPPER})


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    max_repairs: int = 1
    allow_append_end: bool = True
    allow_wrapper: bool = True

    def __post_init__(self) -> None:
        if self.max_repairs not in (0, 1):
            raise ValueError("M03 supports 0 or 1 repair attempt; no unbounded retries")


@dataclass(frozen=True, slots=True)
class PatchOperation:
    action: str
    path: str
    payload: str
    expected_sha256: str | None = None

    def public_dict(self) -> dict:
        from nano_ar5iv.domain.provenance import sha256_bytes
        return {"action": self.action, "path": self.path,
                "expected_sha256": self.expected_sha256,
                "payload_sha256": sha256_bytes(self.payload.encode("utf-8"))}


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    strategy: str
    entry: str
    source_bundle_id: str
    operations: tuple[PatchOperation, ...]
    evidence: tuple[str, ...]
    requires_review: bool = True
    version: str = "m03.1"

    def public_dict(self) -> dict:
        return {"version": self.version, "strategy": self.strategy,
                "entry": self.entry, "source_bundle_id": self.source_bundle_id,
                "operations": [op.public_dict() for op in self.operations],
                "evidence": list(self.evidence),
                "requires_review": self.requires_review}
