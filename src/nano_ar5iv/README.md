# nano-ar5iv Python source: M01/M02/M03 functional baseline + remaining placeholders

**Implemented in M01**: `domain/{source,provenance,diagnostics,states}.py`, `ports/engines.py`, `application/{ingest,convert}.py`, `infrastructure/{repositories,workspaces,sandbox}.py`, `adapters/latexml/{runner,diagnostics}.py`, `interfaces/cli.py`, and `__main__.py`.

**M02 implemented**: `source/arxiv_manifest.py`, `source/tex_scanner.py`, `source/dependency_graph.py`, `source/entry_ranker.py` and `application/discover.py`. **M03 implemented**: `recovery/classifier.py`, `strategies.py`, `wrapper.py`, `planner.py`, `patch_policy.py`, `application/recover.py` plus repair-aware `application/convert.py` and `interfaces/cli.py`. Remaining M04–M07 modules are still placeholders. At M01 only the following behavior exists: content-addressed source directory snapshot, explicit .tex/.ltx entry, a single local Docker/ar5ivist conversion attempt, runtime stderr/logs/HTML capture, and a provenance manifest.

**Not implemented**: arXiv metadata auto discovery, .tar.gz parsing, multi-root handling, source recovery/LLM, Canonical PaperDocument, scientific fidelity validation, PDF fallback, durable batch jobs or HTTP API.

[Module catalog](../../docs/04-architecture/module-catalog.md) · [M01 evidence](../../docs/07-reproduction/m01-baseline.md) · [M01–M07 slices](../../docs/07-reproduction/implementation-slices.md).

Layer boundaries remain domain → application/ports → adapters/infrastructure; some M01 wiring is intentionally pragmatic and should be reviewed as the system grows. No untrusted public TeX service is approved.

M03 guide: [Conservative Recovery](../../docs/07-reproduction/m03-conservative-recovery.md). Runtime repair requires explicit CLI opt-in and does not certify scientific fidelity.
