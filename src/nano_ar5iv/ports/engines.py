"""Executable M01 conversion port and attempt record."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EngineAttempt:
    status: str
    image: str
    image_id: str | None
    entry: str
    exit_code: int | None
    elapsed_seconds: float
    timed_out: bool
    command: tuple[str, ...]
    diagnostic_count: int
    output_html: str | None
    error: str | None = None

    def to_dict(self) -> dict:
        record = asdict(self)
        record["command"] = list(self.command)
        return record


class ConversionEngine(Protocol):
    def convert(self, workspace: Path, entry: str, timeout_seconds: int) -> EngineAttempt:
        """Run one non-repair attempt, preserving logs in the workspace."""
        ...
