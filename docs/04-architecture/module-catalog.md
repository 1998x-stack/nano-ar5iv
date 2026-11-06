# M00-B/M01–M05.1｜模块清单：五阶段核心子集，M05 视觉与 M06–M07 占位

本页保留 M00 模块职责的最初规划，**现在 M01–M05.1 的核心模块已经实现**，具体能力和差异见 [M01 baseline](../07-reproduction/m01-baseline.md)。M03 的 recovery 类目及应用编排已由占位升级为真实保守修复代码，未实现的其他 .py 仍只有 docstring/TODO。详见 [M03](../07-reproduction/m03-conservative-recovery.md)。M04 已有真实 `PaperDocument`、`DocumentNode`、`Equation`、`TableCell`、`Asset`、`Citation`、`Relation` 类型，QualityReport 和六维 QualityGate 在 M05.1 已有真实代码，批量 API、真实 PDF/视觉对照仍是规划。详见 [M04](../07-reproduction/m04-paper-document.md)。

## Category 1：domain（不引用外层）

| File | 未来重要实体 / 函数 | 约束 |
|---|---|---|
| `domain/source.py` | `SourceBundle`、`SourceFile`、`EntryCandidate`、`EntryDecision`、`DocumentSet` | 相对路径、不可变输入、来源哈希 |
| `domain/documents.py` | `PaperDocument`、`DocumentNode`、`Equation`、`Asset`、`TableCell`、`Citation`、`Relation` | 来源明确、ID 稳定 |
| `domain/diagnostics.py` | `DiagnosticEvent`、`Severity`、`FailureFamily` | 可区分 conversion engine/source fault |
| `domain/provenance.py` | `SourceSpan`、`ArtifactDigest`、`RepairDiff` | 来源可追溯 |
| `domain/states.py` | `JobState`、`ConversionStatus`、`QualityDecision` | 显式合法状态跃迁 |

## Category 2：application（用例编排）

| File | 未来应用命令 | 输入 → 输出 |
|---|---|---|
| `application/ingest.py` | `ingest_source` | input→SourceBundle |
| `application/discover.py` | `discover_entrypoints` | bundle→EntryDecision |
| `application/convert.py` | `convert_roots` | EntryDecision→EngineAttempt[] |
| `application/recover.py` | `recover_with_budget` | diagnostics→RecoveryAttempt[] |
| `application/evaluate.py` | `evaluate_run` | 源码/转换/IR/黄金断言→不可变 QualityReport |
| `application/replay.py` | `replay_job` | manifest→repeatable artifacts |

## Category 3：source（静态可观测，不模拟全 TeX）

`source/archive.py`：安全解包的元数据规则（实际文件系统由基础设施执行）；
`source/inventory.py`：排序文件清单；
`source/arxiv_manifest.py`：新旧 `00README`；
`source/tex_scanner.py`：有限 tokenizer/命令识别；
`source/dependency_graph.py`：输入/宏包/图形/引用依赖；
`source/entry_ranker.py`：root 候选及歧义证据。

## Category 4：recovery（不变原文）

`recovery/classifier.py`：错误根因 vs 级联；`recovery/strategies.py`：枚举适用修复；`recovery/wrapper.py`：合成入口/前后缀；`recovery/patch_policy.py`：白名单、哈希与变更限额；`recovery/planner.py`：生成可审计、可回退的 RecoveryPlan。

## Category 5：adapters（所有外部调用都经 ports）

- `adapters/latexml/runner.py`：latexml / ar5ivist 固定版本调用（未来隔离进程）；
- `adapters/latexml/diagnostics.py`：解析 log 的 Error/Fatal/Warning；
- `adapters/latexml/output_reader.py`：读取 XML/HTML/assets；
- `adapters/pdf/extraction.py`：PDF-only fallback，来源单列；
- `adapters/sources/arxiv.py`：获取原始元数据/资料，遵守速率和授权。

## Category 6：normalization

`normalization/xml_to_ir.py`、`html_to_ir.py`、`citation_graph.py`、`assets.py`。在转换器可能失去信息时携带 `unknown_nodes` 与 provenance。

## Category 7：quality

`quality/structural.py`、`mathematical.py`、`bibliography.py`、`assets.py`、`visual.py`、`reporting.py`。质量分析单元按 `PASS/FAIL/UNKNOWN/NOT_RUN` 返回证据；reporting 不可把未知解释成通过。

## Category 8：infrastructure

`infrastructure/workspaces.py`：copy-on-write 修复沙箱；
`repositories.py`：content-addressed artifact store；
`cache.py`：包含 source/config/engine/IR-schema hash 的 key；
`sandbox.py`：进程隔离/禁外联/资源配额；
`jobs.py`：幂等、检查点、取消/超时、重放。

## Category 9：interfaces

`interfaces/cli.py`：设计中的 inspect/discover/convert/evaluate/replay；
`interfaces/api.py`：未来 HTTP/API boundary；未定义实际运行 URL；
`interfaces/reporting.py`：人类可读审计报告的入口。

## Ports（跨边界合约，不是第十个业务类目）

`ports/engines.py` 定义未来 ConversionEngine；`ports/stores.py` 定义 SourceRepository / ArtifactStore；`ports/quality.py` 定义 QualityGate；`ports/runtime.py` 定义 Sandbox / Clock / JobCheckpoint 等协议。Ports 不依赖基础设施。

## 配置与测试占位

- `configs/`：policy/engine/quality 契约占位；无运行配置；
- `deployment/`：Docker/Sandbox/worker 文件占位；无镜像或部署；
- `scripts/`：辅助工具占位；
- `examples/`：授权样本占位；
- `tests/unit`、`contract`、`integration`、`e2e`、`security`、`performance`、`fixtures`：无用例。

## 模块实现的依赖顺序

~~~text
domain → ports → source → adapters/latexml → application baseline
     → recovery → normalization → quality → infrastructure jobs → interfaces
~~~

**注意设计依赖与调用流不同**：源码模块内部应向 `domain/ports` 依赖，`application` 组织流程，`adapters` 负责外部实现。任何跨类目新增工具必须先明确责任边界。

实现计划与预期验收见 [M01–M07 slices](../07-reproduction/implementation-slices.md)；总体蓝图见 [reproduction](reproduction-blueprint.md)。
