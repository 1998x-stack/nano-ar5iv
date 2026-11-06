# 文档总目录

本目录基于 **2026-11-06** 可查的官方手册、技术文章、论文和 issue 编制。内容分为三类：**事实（有链接）**、**经验判断（有证据链）**、**拟议设计（尚未验证）**。请勿将架构提案表述为已上线功能。

## 阅读路径

- 了解原理：`01-foundations/ar5iv-overview.md` → `latexml-pipeline.md` → `semantic-elements.md`。
- 处理没有 `main.tex` 的论文：`02-source-recovery/entry-discovery.md` → `recovery-playbook.md`。
- 查看外部证据：`03-research/landscape.md` → `issue-analysis.md` → `../REFERENCES.md`。
- 开始软件设计：`04-architecture/system-architecture.md` → `code-categories.md` → `data-contracts.md` → `decisions.md`。
- 开发前必读：`05-quality/evaluation.md`、`security.md`、`test-strategy.md`、`06-planning/roadmap.md`。

## 新增：可复现开发蓝图（M00-B）

- [函数级复现蓝图](04-architecture/reproduction-blueprint.md)：源码入口 → 转换 → 修复 → IR → 质量门禁。
- [模块 Catalog 与真实占位文件](04-architecture/module-catalog.md)：50 个无逻辑 .py 模块与 Ports。
- [上游最小复现实验](07-reproduction/README.md)：手动 ar5ivist/LaTeXML 实验、实验记录。
- [运行时序、API 与状态机](07-reproduction/interface-sequence.md)：未来接口设计，当前不可调用。
- [实验与测试矩阵](07-reproduction/experiment-matrix.md)：入口/恢复/科学保真/安全。
- [故障根因排查](07-reproduction/failure-triage.md)：异常分类、停止条件。
- [M01–M07 逐文件实施步骤](07-reproduction/implementation-slices.md)：模块、阶段、验收。

**状态更新（M01）**：`src/nano_ar5iv/` 的源码快照、显式入口 Docker 转换适配和 CLI 已实现，`tests/` 包含实际单元/模拟用例；其余模块、configs、deployment 和完整科学验证仍是占位设计。真实 LaTeXML 基线与 CLI 在 GitHub Actions 已跑通并校验产物哈希，但科研保真门禁仍未实现。阅读 [M01 baseline](07-reproduction/m01-baseline.md)。

## M02 真实功能

- [M02 Entry Discovery 实现、CLI 与验收](07-reproduction/m02-entry-discovery.md)：arXiv 元数据主入口、静态依赖图、明确歧义状态、optional top-k trial、真实 Docker 测试。
- 旧 M00 的架构设计和 M01 的基线说明依然保留，M03–M07 文档属于规划，不代表已经实现。

## 文档约定

- 使用 `[F]` 表示核实的外部事实、`[O]` 表示外部报告/意见、`[D]` 表示本项目设计决策、`[H]` 表示待验证假设。
- 报告 issue 时记录：日期、原始 URL、状态、作者报告、后续更正、是否独立复现；不把开放 issue 等同已证实的引擎缺陷。
- 文档中出现的代码、伪代码、目录树、JSON 都是**契约草案/示例**，不是运行代码。
