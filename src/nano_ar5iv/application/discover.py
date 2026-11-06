"""Discovery use case and optional bounded trial observations for ambiguous roots.

Trial success is not a scientific fidelity guarantee and NEVER automatically
promotes an ambiguous root to SELECTED without independent evidence.
"""
from __future__ import annotations
from dataclasses import replace
from nano_ar5iv.domain.source import EntryDecision, SourceBundle
from nano_ar5iv.source.entry_ranker import discover_roots
from nano_ar5iv.ports.engines import ConversionEngine
from nano_ar5iv.infrastructure.repositories import ArtifactStore
from nano_ar5iv.application.convert import convert_source


def discover_entries(bundle: SourceBundle) -> EntryDecision:
    return discover_roots(bundle)


def probe_candidates(bundle: SourceBundle, decision: EntryDecision,
                     engine: ConversionEngine, store: ArtifactStore,
                     top_k: int = 2, timeout_seconds: int = 120) -> EntryDecision:
    if not 1 <= top_k <= 5 or not 1 <= timeout_seconds <= 900:
        raise ValueError("Probe limits: top_k=1..5 and timeout=1..900")
    if decision.status != "AMBIGUOUS":
        return decision
    trials = []
    for candidate in decision.candidates[:top_k]:
        try:
            attempt, manifest_path = convert_source(bundle, candidate.path, engine, store,
                                                     timeout_seconds, selection=decision.to_dict())
            trials.append({"entry": candidate.path, "status": attempt.status,
                           "manifest_path": str(manifest_path)})
        except (OSError, ValueError) as exc:
            trials.append({"entry": candidate.path, "status": "PROBE_ERROR",
                           "error": exc.__class__.__name__})
    return replace(decision, trial_results=tuple(trials),
                   diagnostics=decision.diagnostics +
                   ("Trial results are observations only; ambiguity remains until reviewed",))
