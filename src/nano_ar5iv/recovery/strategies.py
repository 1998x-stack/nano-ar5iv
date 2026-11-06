"""Allowlisted M03 recovery strategy registry, no autonomous source edits."""
from __future__ import annotations

STRATEGIES = {
    "S0_BASELINE": {"implemented": True, "automatic": False, "note": "M01 explicit-entry baseline"},
    "S2_SYNTHETIC_WRAPPER": {"implemented": True, "automatic": False,
                             "note": "requires explicit document class and ordered fragments"},
    "S1_PATH_REWRITE": {"implemented": False, "automatic": False,
                        "note": "must not guess path case or move author source"},
    "S3_MACRO_BINDINGS": {"implemented": False, "automatic": False,
                          "note": "must not replace unknown math macros with empty commands"},
    "S4_LLM_PATCH": {"implemented": False, "automatic": False,
                     "note": "model-generated source editing remains disabled"},
}
