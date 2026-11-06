# Python modules: architecture-only placeholders

Every file under this directory is intentionally a **docstring-only placeholder**. No LaTeXML conversion, archive parser, CLI, API, import-time setup, job runner or PDF pipeline is implemented.

Responsibility and IO contracts: [Module Catalog](../../docs/04-architecture/module-catalog.md); [Reproduction Blueprint](../../docs/04-architecture/reproduction-blueprint.md); [Implementation Slices](../../docs/07-reproduction/implementation-slices.md).

Maintain dependency inversion: domain (pure); application (ports); adapters/infrastructure (ports implementations); interfaces (I/O boundary). Do not add runtime behavior until milestone-specific fixtures and isolation checks exist.
