# Tests — scaffold only

The subdirectories exist as empty placeholders (.gitkeep). There are **zero test implementations, no goldens, and no test results**. The naming follows [Experiment Matrix](../docs/07-reproduction/experiment-matrix.md) and [Test Strategy](../docs/05-quality/test-strategy.md).

- unit: parsing, graph, state, path rules.
- contract: EngineAttempt, SourceBundle, PaperDocument, QualityReport.
- integration: real pinned LaTeXML in isolated runtime.
- e2e: source through quality report.
- security: archives/TeX execution/HTML rendering.
- performance: throughput and resource budget.
- fixtures: entry-discovery, source-recovery, math-fidelity, bibliography, asset-fidelity, security.
