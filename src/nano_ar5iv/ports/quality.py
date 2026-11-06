"""M05 quality gate output types; PASS is not equivalent to paper-wide truth."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Protocol

QUALITY_SCHEMA = "1.0"
POLICY_VERSION = "m05.1"
STATUSES = frozenset({"PASS", "FAIL", "UNKNOWN", "NOT_RUN", "NOT_APPLICABLE"})
DECISIONS = frozenset({"ACCEPTED", "PARTIAL", "REVIEW_REQUIRED", "REJECTED"})


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    message: str
    object_id: str | None = None
    observed: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Dimension:
    status: str
    findings: tuple[Finding, ...] = ()
    checked: int = 0

    def __post_init__(self) -> None:
        if self.status not in STATUSES or self.checked < 0:
            raise ValueError("Invalid dimension status or count")

    def to_dict(self) -> dict:
        return {"status": self.status, "checked": self.checked,
                "findings": [f.to_dict() for f in self.findings]}


@dataclass(frozen=True, slots=True)
class QualityReport:
    document_id: str
    derivation_id: str
    document_sha256: str
    reference_sha256: str | None
    dimensions: dict[str, Dimension]
    decision: str
    reason_codes: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)
    schema_version: str = QUALITY_SCHEMA
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError("Unrecognized quality decision")

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version, "policy_version": self.policy_version,
                "document_id": self.document_id, "derivation_id": self.derivation_id,
                "document_sha256": self.document_sha256,
                "reference_sha256": self.reference_sha256,
                "dimensions": {k: v.to_dict() for k, v in sorted(self.dimensions.items())},
                "decision": self.decision, "reason_codes": list(self.reason_codes),
                "provenance": self.provenance}


class QualityGate(Protocol):
    def assess(self, document: object, reference: object | None) -> dict[str, Dimension]:
        """Assess scientific evidence without synthesizing a source of truth."""
        ...
