"""M03 immutable explicit-order synthetic wrapper recovery planning."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict

from nano_ar5iv.domain.provenance import sha256_bytes, stable_json
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.recovery.patch_policy import UnsafeRecovery, validate_fragments
from nano_ar5iv.recovery.wrapper import render_wrapper
from nano_ar5iv.source.inventory import read_source_text
from nano_ar5iv.source.tex_scanner import scan_tex

GENERATED_ENTRY = "__nano_ar5iv_wrapper.tex"


@dataclass(frozen=True, slots=True)
class WrapperPlan:
    plan_id: str
    source_bundle_id: str
    fragments: tuple[str, ...]
    documentclass: str
    generated_entry: str
    generated_sha256: str
    review_required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def create_wrapper_plan(bundle: SourceBundle, fragments: tuple[str, ...],
                        documentclass: str) -> WrapperPlan:
    """Return a deterministic proposal; do not execute, patch or guess source order."""
    validate_fragments(bundle, fragments, documentclass)
    for path in fragments:
        observations = scan_tex(read_source_text(bundle, path))
        if (observations["has_documentclass"] or observations["has_begin_document"] or
                observations["has_end_document"] or observations["has_plain_tex_bye"]):
            raise UnsafeRecovery("Fragment already includes a document boundary: " + path)
        if any(issue.startswith("unresolved_dynamic:") for issue in observations["diagnostics"]):
            raise UnsafeRecovery("Dynamic dependency requires manual review: " + path)
    wrapper = render_wrapper(fragments, documentclass)
    generated_sha = hashlib.sha256(wrapper.encode("utf-8")).hexdigest()
    payload = {"algorithm": "m03-wrapper-v1", "source_bundle_id": bundle.bundle_id,
               "fragments": list(fragments), "documentclass": documentclass,
               "generated_entry": GENERATED_ENTRY, "generated_sha256": generated_sha}
    return WrapperPlan(sha256_bytes(stable_json(payload)), bundle.bundle_id, fragments,
                       documentclass, GENERATED_ENTRY, generated_sha)
