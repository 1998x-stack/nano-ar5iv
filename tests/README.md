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

## 真实容器验收记录

GitHub Actions 独立真实 Docker job 已通过最小 LaTeXML 转换、完整 CLI、manifest 与 artifact SHA-256 检查：[GitHub Actions M01 real CLI verification](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42189149532)。普通 Python 矩阵中的跳过仍是有意设计，真实集成由独立 job 执行。测试结果不代表任意 LaTeX 宏包都正确或生产沙箱已获安全验收。

### M02 CI 验收
- [GitHub Actions #42198296310](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42198296310)：Python 3.11/3.13 共 38 unittest/每个版本，36 通过、2 按普通矩阵跳过；独立真实 Docker 作业运行原 M01 与新增 M02 自动入口用例，全部通过。
- 验证范围仅为自编最小论文、静态依赖及模拟引擎；不代表真实 arXiv 大型语料的入口定位准确率和科学保真合格。

### M03 tests

- `tests/test_m03_recovery.py` checks source immutability, one retry, first-cause diagnostics, SHA256 validation and forged patch rejection.
- `tests/test_m03_cli.py` checks `recover --entry/--fragments/--plan-only`, status and audit manifests.
- `tests/test_real_m03_opt_in.py` runs a self-authored fragment-wrapper conversion in the pre-pulled ar5ivist Docker image (separate CI real-engine job).
- Results must be tied to the successful PR CI run. A fake engine only validates orchestration; HTML existence is not M05 scientific fidelity evidence.

See [M03 recovery](../docs/07-reproduction/m03-conservative-recovery.md).

### M04 Python tests and real-engine integration

- `test_m04_normalization.py` — XML and HTML semantic extraction, formulas, tables, bibliographic refs, unknown structures, DTD/bounds, invalid/external assets.
- `test_m04_run_integration.py` — source/manifest SHA256, immutable normalization store, idempotence, tamper refusal, CLI and XML preference.
- `test_real_m04_opt_in.py` — **real GitHub-hosted Docker/ar5ivist** minimal self-authored conversion followed by `normalize` and PaperDocument hash/MathML checks.
- Python 3.11/3.13 suites run via the normal matrix; Docker test only runs with `RUN_REAL_LATEXML=1` in the dedicated CI job. Refer to PR #10 for the current acceptance state.
- No scientific claim quality gate, arbitrary PDF conversion or large real arXiv benchmark in this stage.

[M04 guide](../docs/07-reproduction/m04-paper-document.md).

M04 验收：GitHub Actions [#42204716397](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42204716397) 三组 CI success；Python 3.11/3.13 各 76 test（72 pass，4 skipped），独立 Docker M01–M04 转换链路成功。结果仅适用于测试覆盖与自编最小 TeX，**不等于已完成科学内容质量验收**。
