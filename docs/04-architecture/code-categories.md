# 09｜代码 Category 与实际占位目录（Architecture Scaffold + M01/M02/M03 v0.5）

> **更新于 2026-11-06：本文件中的模块和目录已创建，**M01/M02 的源码快照、Docker 转换、入口发现、依赖图及 M03 的保守修复和 CLI 均已有代码；后续 M04–M07 仍为 docstring/TODO 占位**；M01/M02 已通过真实 ar5ivist 转换，M03 正在验证；科学质量门禁及 API 服务尚未实现。真实模块清单见 [module-catalog](module-catalog.md)，完整流程见 [reproduction-blueprint](reproduction-blueprint.md)。

## 1. 代码分层原则

架构目标是 **Python Modular Monolith + isolated external LaTeXML worker**，未来视实际性能再决定是否引入 Rust 实现扫描/依赖图。领域与存储、调度、引擎和接口必须解耦。

~~~text
interfaces (CLI / HTTP API)  [future]
      |
application (use-case orchestrators)
      |                     \
      +-- domain (data)      +-- ports (contracts)
                                    ^
                                    |
                           adapters + infrastructure
source, recovery, normalization, quality: pure policies/transforms whenever possible
~~~

**依赖倒置的具体解释**：Ports 是 interface abstractions，不是额外的第十个业务 Domain；application 可导入 domain 和 ports，但不应直接使用 GitHub、Docker 或 LaTeXML 实现类型。adapters/infrastructure 只实现外部边界；domain 不依赖任何外部组件。

## 2. 真实目录树（M01 部分实现，其余占位）

~~~text
nano-ar5iv/
├── README.md
├── CONTRIBUTING.md
├── pyproject.toml                    # 仅打包元数据：0.0.0，无 CLI、无运行依赖
├── .gitignore
├── docs/
│   ├── 01-foundations/              # LaTeXML、MathML 与 ar5iv 技术
│   ├── 02-source-recovery/          # root 发现、异常修复
│   ├── 03-research/                 # 论文/博客/issue
│   ├── 04-architecture/             # 架构、代码分类、接口和复现逻辑
│   ├── 05-quality/                  # 测试、质量、安全
│   ├── 06-planning/                 # 分阶段路线
│   └── 07-reproduction/             # 原始上游可重复实验与实施计划
├── src/nano_ar5iv/
│   ├── domain/
│   │   ├── source.py                # bundle / entry / document set
│   │   ├── documents.py             # PaperDocument / scientific IR
│   │   ├── diagnostics.py           # events and error categories
│   │   ├── provenance.py            # source spans and hashes
│   │   └── states.py                # job/quality lifecycle
│   ├── application/
│   │   ├── ingest.py
│   │   ├── discover.py
│   │   ├── convert.py
│   │   ├── recover.py
│   │   ├── evaluate.py
│   │   └── replay.py
│   ├── source/
│   │   ├── archive.py
│   │   ├── inventory.py
│   │   ├── arxiv_manifest.py
│   │   ├── tex_scanner.py
│   │   ├── dependency_graph.py
│   │   └── entry_ranker.py
│   ├── recovery/
│   │   ├── classifier.py
│   │   ├── strategies.py
│   │   ├── wrapper.py
│   │   ├── patch_policy.py
│   │   └── planner.py
│   ├── adapters/
│   │   ├── latexml/{runner,diagnostics,output_reader}.py
│   │   ├── pdf/extraction.py
│   │   └── sources/arxiv.py
│   ├── normalization/
│   │   ├── xml_to_ir.py
│   │   ├── html_to_ir.py
│   │   ├── citation_graph.py
│   │   └── assets.py
│   ├── quality/
│   │   ├── structural.py
│   │   ├── mathematical.py
│   │   ├── bibliography.py
│   │   ├── assets.py
│   │   ├── visual.py
│   │   └── reporting.py
│   ├── infrastructure/
│   │   ├── workspaces.py
│   │   ├── repositories.py
│   │   ├── cache.py
│   │   ├── sandbox.py
│   │   └── jobs.py
│   ├── interfaces/{cli,api,reporting}.py
│   ├── ports/{engines,stores,quality,runtime}.py
│   ├── config.py
│   └── README.md
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   ├── performance/
│   └── fixtures/{entry-discovery,source-recovery,math-fidelity,
│                 bibliography,asset-fidelity,security}/
├── configs/                          # No actual policies yet
├── deployment/                       # No Dockerfiles, no compose
├── examples/                         # No sample papers/fixtures yet
├── benchmarks/                       # No measured data
└── scripts/                          # No executable scripts
~~~

Python package 保留 __init__.py，占位目录由 .gitkeep 保存；**M01 已有少量实际模块与 unittest，目录存在 ≠ 其他阶段已实现**。完整映射见 [M01 baseline](../07-reproduction/m01-baseline.md)。

## 3. 九大业务 Category

| 类目 | 唯一责任 | 输入 → 产物 | 实现阶段 |
|---|---|---|---|
| 01 domain | 来源与文档业务契约 | bytes/metadata → SourceBundle/PaperDocument | M01/M04 |
| 02 application | 有界用例编排 | job request → JobResult / attempt records | M01–M06 |
| 03 source | 发现/依赖/入口选择 | source bundle → EntryDecision/DocumentSet | M02 |
| 04 recovery | 根因归类、策略和副本修复 | diagnostic → RecoveryPlan + immutable patch | M03 |
| 05 adapters | 所有外部解析/转换执行 | workspace → XML/HTML/log/asset | M01/M04 |
| 06 normalization | 中间表示到标准科学文档 | XML/HTML/PDF → PaperDocument | M04 |
| 07 quality | 结构/科学保真/视觉校验 | IR + evidence → QualityReport | M05 |
| 08 infrastructure | 沙箱/缓存/存储/任务安全 | job → isolated attempts/artifacts | M01/M06 |
| 09 interfaces | CLI/API/报告交付 | external request → application use case | M06 |

### Ports 横切层

- engines：§ConversionEngine.convert()§。
- stores：§SourceRepository / ArtifactStore§。
- quality：§QualityGate.assess()§。
- runtime：§Sandbox / JobCheckpoint§。

只有接口语义，除 M01 部分实际代码外没有后续功能。接口应在 M01 按真实样本逐步收紧，而非先制造过宽的通用框架。

## 4. 调用顺序与所有权

~~~text
ingest→source inventory→manifest→dependency graph→root selection
      →engine convert→diagnostics→bounded recovery→normalization
      →quality/acceptance→persist artifacts→user report
~~~

- Source 只负责解释原料，不碰网络、Docker、输出报告。
- Recovery 生成修复计划，但不直接修改作者原件。
- Adapter 必须返回原始日志/exit status，不能静默过滤 error。
- Normalization 对未知节点保留 raw provenance，不丢弃。
- QualityGate 分开 report success 与 scientific fidelity。
- Infrastructure 统一执行资源隔离、对象存储与任务回放。
- Interfaces 不绕过 application 直接执行 shell。

## 5. 反模式

不使用“超级 utils.py”；不将 CSS class 当永久科学数据 schema；不在前端运行 TeX；不盲目合并多个 root；不在未知引用/公式上让 LLM 编造内容；不把 Docker 官方示例当成安全生产沙箱；不把占位模块按运行能力宣告。

## 6. 实现切片和改动纪律

详见 [implementation-slices.md](../07-reproduction/implementation-slices.md)。以 §M01→M02→M03→M04→M05→M06§ 推进，每一阶段需要固定工具版本、授权 fixture、测试和回归报告。M01–M03 已有实际功能和回归测试，M04–M07 未实现。
