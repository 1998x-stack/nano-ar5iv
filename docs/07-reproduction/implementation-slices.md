# 逐文件实施顺序与 PR 切片（M01–M04 分阶段实现，M05+ 仍为计划）

本表保留最初的 M01–M07 计划及切片验收。M01–M03 已实现并合并，**M04.1 已实现 XML/HTML 归一化和 CLI（PR #10）**，但 PDF-only fallback/完整 TeX source spans 尚未交付，M05–M07 仍是规划。证据见 [M01 baseline](m01-baseline.md)、[M02 entry](m02-entry-discovery.md)、[M03 recovery](m03-conservative-recovery.md)、[M04 IR](m04-paper-document.md)。

## Slice M01.1 — 核心契约与可信源快照

- `domain/source.py`、`provenance.py`、`states.py`：SourceBundle/ArtifactHash/JobState 及不变式；
- `ports/stores.py`、`infrastructure/repositories.py`：content addressed manifest 与只读原件契约；
- `application/ingest.py`：source→immutable bundle；
- `tests/unit/`、`tests/contract/`：路径/哈希/状态边界。

**验收**：普通文件样本和危险归档清单；SHA256 可复核；不写原始输入目录；错误均为明确状态。

## Slice M01.2 — 固定 LaTeXML Baseline

- `ports/engines.py`、`adapters/latexml/runner.py`、`diagnostics.py`、`output_reader.py`；
- `infrastructure/sandbox.py`、`application/convert.py`；
- `tests/integration/`：合法最小 TeX → XML/HTML/真实日志。

**验收**：真实 Docker/LaTeXML 版本及 SHA、进程退出码/时间/日志；报告运行配额；不进行自动修复。

## Slice M02.1 — 来源文件盘点与官方元数据

- `source/archive.py`、`inventory.py`、`arxiv_manifest.py`；
- `tests/fixtures/entry-discovery/`：E01–E07；
- **验收**：新旧 `00README` 正确处理 top-level/ignore/include，并拒绝恶意路径。

## Slice M02.2 — 依赖图与候选排序

- `source/tex_scanner.py`、`dependency_graph.py`、`entry_ranker.py`；
- `application/discover.py`、`tests/unit/` / `integration/`：E08–E12；
- **验收**：多 root 保序，动态 input 返回 unknown，不把 comments/verbatim 当依赖。

## Slice M03.1 — 诊断分类

- `domain/diagnostics.py`、`recovery/classifier.py`、`adapters/latexml/diagnostics.py`；
- **验收**：root cause 与 cascade 分层、错误码溯源、缺失宏包/超时覆盖。

## Slice M03.2 — 受限修复与状态机

- `recovery/strategies.py`、`wrapper.py`、`patch_policy.py`、`planner.py`；
- `infrastructure/workspaces.py`、`application/recover.py`；
- **验收**：copy-on-write、修复 diff、有限重试、数学公式不能被静默替换；R01–R10。

## Slice M04 — Canonical IR（M04.1 已有实现；PDF-only fallback 后续）

- `domain/documents.py`、`normalization/xml_to_ir.py`、`html_to_ir.py`、`citation_graph.py`、`assets.py`；
- `adapters/pdf/extraction.py`（PDF fallback **未实现**，必须区别于 XML/HTML 的已实现能力）；
- **验收**：节点 ID 稳定、citation edges 保持、未知节点不会丢弃、版本化 schema。

## Slice M05 — 可信质量门禁

- `ports/quality.py`、`quality/structural.py`、`mathematical.py`、`bibliography.py`、`assets.py`、`visual.py`、`reporting.py`、`application/evaluate.py`；
- **验收**：Q01–Q08 实测、unknown/not-run 不能通过 hard gate、与无质量门禁基线对照。

## Slice M06 — 批量任务/API/运行

- `infrastructure/jobs.py`、`cache.py`、`interfaces/cli.py`、`api.py`、`reporting.py`、`application/replay.py`；
- `deployment/`、`configs/` 与 `tests/performance/`；
- **验收**：任务重放、幂等缓存、限额、权限审查、完整 CLI/API 协议、性能数据。

## Slice M07 — 可选 LLM 与科研生态

LLM 不是默认依赖，必须经 M05 证明科学事实保护有效后才可设计 `adapters/llm` 与 `quality/claim_evidence`。没有对照消融与可审计补丁策略，不启用自动整篇修复。

## 每个 PR 的标准

- 仅改本 slice 相关的实际模块 + fixture + docs；
- PR 附源文件 hash、引擎版本、执行命令、CI/本地日志、样本数、结果与失败；
- 必须区分单测、集成、真实论文复现；未经测试写 `NOT_RUN`；
- 遇到转换正确率下降、无依据修复、许可证或沙箱风险必须停止。

详见 [module catalog](../04-architecture/module-catalog.md) 和 [evaluation matrix](experiment-matrix.md)。
