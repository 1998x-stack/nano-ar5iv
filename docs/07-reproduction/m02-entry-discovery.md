# M02 — TeX Entrypoint Discovery: implementation and acceptance

Branch: feat/m02-entry-discovery. This stage depends on the M01 content-addressed source snapshot.

## Implemented

- Discover a root from a directory, ZIP or TAR archive; the CLI stores the immutable source bundle and a separate entry-decision.json report.
- Metadata precedence: modern 00README.json sources with toplevel/include/ignore; legacy 00README.XXX with toplevelfile/ignore/include. Modern declaration takes precedence and conflicts trigger REVIEW_REQUIRED.
- Conservative scanning of input/include/subfile/import/subimport, excluding comments and verbatim; static dependency graph with missing, dynamic, ambiguous and cyclic dependency diagnostics.
- Respect independent multi-root manuscripts (MULTIPLE_ROOTS); never concatenate them, and never auto-convert if there is more than one.
- Fragments, metadata errors and dynamic arguments return REVIEW_REQUIRED. A PDF-only directory returns PDF_ONLY but does not extract or convert the PDF.
- Archive extraction is staging-only, with size/file count limits, no directory traversal, no links, no special entries, no duplicate paths and a ZIP compression ratio bound.
- CLI convert may omit --entry only when discovery returns a single SELECTED entry. Explicit --entry remains available.
- An explicit probe subcommand performs bounded, sequential top-k attempts (1–5) using the existing M01 conversion engine. It stores each attempt manifest and a probe-summary.json; process success NEVER overrides REVIEW_REQUIRED or implies scientific fidelity.

## Commands

    PYTHONPATH=src python -m unittest discover -s tests -p test_entry_discovery.py -v
    PYTHONPATH=src python -m unittest discover -s tests -v
    PYTHONPATH=src python -m compileall -q src tests
    PYTHONPATH=src python -m nano_ar5iv --output /tmp/nano-m02 discover examples/trusted-minimal
    PYTHONPATH=src python -m nano_ar5iv --output /tmp/nano-m02 convert examples/trusted-minimal
    PYTHONPATH=src python -m nano_ar5iv --output /tmp/nano-m02 probe examples/trusted-minimal --top-k 2 --timeout 90

The decision JSON is written to output/discoveries/<source_bundle_id>/entry-decision.json and contains the inventory, graph, evidence, selected roots and diagnostics.

Tests: E01–E12 plus modern/legacy conflicts, unsafe metadata, cycles, missing dependencies, CLI persistence, ZIP ingestion, ZIP traversal, TAR symlink and ambiguous conversion. These use self-authored fixtures, not original research papers.

## Open acceptance gates

- M01 Docker/LaTeXML real conversion is NOT_VERIFIED in this environment. Do not equate mock test success with real HTML/MathML conversion.
- M02 top-k candidate trial code exists but has only fake-engine tests so far; no real Docker probe has been verified, and there is no quality-based winner selection. Real arXiv main-file accuracy, latency and precision/recall have NOT_RUN.
- Scanner is conservative and does not fully interpret TeX catcode changes, conditional expansion, complex macros, nested includeonly or every subimport package semantics. Ambiguous cases should be reviewed.
- Source snapshot hashes are verified on reads. Archive bounds are defense-in-depth; this does not make arbitrary TeX safe to execute.
- M03 patch/recovery, M04 canonical PaperDocument, M05 scientific fidelity gate and M06 service remain future phases.

References: [Official arXiv 00README specification](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md), [arXiv TeX source guidance](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/submit_tex.md), [entry-discovery design](../02-source-recovery/entry-discovery.md).
