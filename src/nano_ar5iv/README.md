# nano-ar5iv Python source: M01 baseline + future placeholders

**Implemented in M01**: `domain/{source,provenance,diagnostics,states}.py`, `ports/engines.py`, `application/{ingest,convert}.py`, `infrastructure/{repositories,workspaces,sandbox}.py`, `adapters/latexml/{runner,diagnostics}.py`, `interfaces/cli.py`, and `__main__.py`.

The rest of the module layout remains **docstring/TODO-only**. At M01 only the following behavior exists: content-addressed source directory snapshot, explicit .tex/.ltx entry, a single local Docker/ar5ivist conversion attempt, runtime stderr/logs/HTML capture, and a provenance manifest.

**Not implemented**: arXiv metadata auto discovery, .tar.gz parsing, multi-root handling, source recovery/LLM, Canonical PaperDocument, scientific fidelity validation, PDF fallback, durable batch jobs or HTTP API.

[Module catalog](../../docs/04-architecture/module-catalog.md) · [M01 evidence](../../docs/07-reproduction/m01-baseline.md) · [M01–M07 slices](../../docs/07-reproduction/implementation-slices.md).

Layer boundaries remain domain → application/ports → adapters/infrastructure; some M01 wiring is intentionally pragmatic and should be reviewed as the system grows. No untrusted public TeX service is approved.
