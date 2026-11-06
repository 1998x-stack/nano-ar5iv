# Tests: M01 active, future suites placeholders

M01 implemented Python `unittest` suites in the top-level `tests/test_*.py` files:
- `test_source_snapshots.py`: deterministic SHA256 inventory, repeatability, symlink and path limits, tampering.
- `test_conversion.py`: explicit-root validation, simulated engine output and artifact manifest.
- `test_docker_runtime.py`: docker command restrictions, warnings/errors, unavailable engine and output collision.
- `test_cli.py`: real `inspect` smoke test and absent-Docker failure manifest.
- `test_real_latexml_opt_in.py`: **skipped unless** `RUN_REAL_LATEXML=1` and pre-pulled Docker image is available.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

Local result on 2026-11-06: **16 test cases, 15 pass, 1 skip**. Only tests against simulated engines (or real no-Docker failure) were run. The M01 LaTeXML Docker integration, scientific quality, performance, and sandbox penetration tests remain `NOT_RUN`.

The existing `tests/unit`, `contract`, `integration`, `e2e`, `fixtures`, `security` and `performance` directories still contain only `.gitkeep` placeholders for M02–M07.

[Experiment matrix](../docs/07-reproduction/experiment-matrix.md) · [M01 implementation record](../docs/07-reproduction/m01-baseline.md).
