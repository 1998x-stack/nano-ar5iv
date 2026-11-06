# 09｜代码 Category 与建议目录树（仅设计）

> **未创建下列 `src/` 或 `tests/` 目录，所有名称仅代表未来实现责任边界。** 采用 Python 主导编排、外部 LaTeXML 子进程/容器、未来可插拔 Rust 扫描器的渐进路线。

~~~text
nano-ar5iv/
├── README.md
├── docs/                         # 现有：研究、架构、测试、路线图
├── pyproject.toml                 # 未来
├── src/nano_ar5iv/               # 未来
│   ├── domain/                   # Category 1: pure models + invariants
│   │   ├── source.py
│   │   ├── documents.py
│   │   ├── diagnostics.py
│   │   ├── provenance.py
│   │   └── states.py
│   ├── application/              # Category 2: orchestration
│   │   ├── ingest.py
│   │   ├── discover.py
│   │   ├── recover.py
│   │   ├── convert.py
│   │   └── evaluate.py
│   ├── source/                   # Category 3: source discovery
│   │   ├── inventory.py
│   │   ├── arxiv_manifest.py
│   │   ├── tex_scanner.py
│   │   ├── dependency_graph.py
│   │   └── entry_ranker.py
│   ├── recovery/                 # Category 4: policy + patch planning
│   │   ├── classifier.py
│   │   ├── strategies.py
│   │   ├── wrapper.py
│   │   ├── patch_policy.py
│   │   └── planner.py
│   ├── adapters/                 # Category 5: external engines
│   │   ├── latexml/
│   │   │   ├── runner.py
│   │   │   ├── diagnostics.py
│   │   │   └── output_reader.py
│   │   ├── pdf/
│   │   │   └── extraction.py
│   │   └── sources/
│   │       └── arxiv.py
│   ├── normalization/            # Category 6: canonical PaperDocument
│   │   ├── xml_to_ir.py
│   │   ├── html_to_ir.py
│   │   └── citation_graph.py
│   ├── quality/                  # Category 7: validation and evidence
│   │   ├── structural.py
│   │   ├── mathematical.py
│   │   ├── bibliography.py
│   │   ├── visual.py
│   │   └── reporting.py
│   ├── infrastructure/           # Category 8: jobs, storage, sandbox
│   │   ├── workspaces.py
│   │   ├── repositories.py
│   │   ├── cache.py
│   │   └── sandbox.py
│   ├── interfaces/               # Category 9: entrypoints
│   │   ├── cli.py
│   │   └── api.py
│   └── config.py
├── tests/                         # 未来：unit/contract/integration/e2e
│   ├── fixtures/
│   │   ├── valid/
│   │   ├── missing-entry/
│   │   ├── multiple-roots/
│   │   ├── missing-package/
│   │   ├── math-fidelity/
│   │   └── bibliography/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── e2e/
└── tools/                         # 未来：只放可复现的离线辅助脚本
~~~

## 依赖规则

`domain <- application <- interfaces`；`application` 依赖 Adapter Protocol，而非调用 LaTeXML CLI 细节。`source/recovery/quality` 不相互循环依赖；`infrastructure` 负责提供可替换的 Ports 实现。PDF fallback 不修改 TeX 恢复计划，只生成不同 provenance 的标准 IR。

## 类别责任矩阵

| Category | 输入 | 输出 | 首要测试 |
|---|---|---|---|
| 1 domain | 规范化字段 | immutable entities | schema/invariant |
| 2 application | request + ports | attempt lifecycle | state transitions |
| 3 source | archive tree + manifests | entry candidates + dependency graph | ambiguous source fixtures |
| 4 recovery | diagnostics + source spans | immutable repair plan | patch/idempotency |
| 5 adapters | engine invocation | raw XML/HTML/logs | version contract |
| 6 normalization | parsed outputs | PaperDocument | stable IDs/refs |
| 7 quality | IR + source evidence | assessment + gate | goldens/diff |
| 8 infrastructure | job spec | sandbox/artifacts/checkpoints | security/recovery |
| 9 interfaces | CLI/API requests | validated commands | compatibility/error responses |

## 明确不建议的组织方式

- 一上来把每个阶段拆成微服务；
- 将 CLI 运行/日志正则/IR 构造混入一个大文件；
- 用 `utils.py` 堆积无分类的 TeX 规则；
- 让 LLM 成为没有边界的全文件改写器；
- 将生成 HTML 当作可唯一代表论文的事实源。

## 下一步代码顺序（尚未执行）

`domain+contracts → source scanner+manifest → adapter → recovery policy → normalization → quality → batch execution → API/UI`，每一阶段都先添加 fixture 与真实转换证据。
