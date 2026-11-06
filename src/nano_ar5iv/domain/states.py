"""M01 operation status; richer job state machine is scheduled for M06."""
from enum import StrEnum


class AttemptStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    ENGINE_UNAVAILABLE = "ENGINE_UNAVAILABLE"
    OUTPUT_MISSING = "OUTPUT_MISSING"
