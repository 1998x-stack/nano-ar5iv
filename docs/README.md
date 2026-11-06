# 文档总目录

本目录基于 **2026-11-06** 可查的官方手册、技术文章、论文和 issue 编制。内容分为三类：**事实（有链接）**、**经验判断（有证据链）**、**拟议设计（尚未验证）**。请勿将架构提案表述为已上线功能。

## 阅读路径

- 了解原理：`01-foundations/ar5iv-overview.md` → `latexml-pipeline.md` → `semantic-elements.md`。
- 处理没有 `main.tex` 的论文：`02-source-recovery/entry-discovery.md` → `recovery-playbook.md`。
- 查看外部证据：`03-research/landscape.md` → `issue-analysis.md` → `../REFERENCES.md`。
- 开始软件设计：`04-architecture/system-architecture.md` → `code-categories.md` → `data-contracts.md` → `decisions.md`。
- 开发前必读：`05-quality/evaluation.md`、`security.md`、`test-strategy.md`、`06-planning/roadmap.md`。

## 文档约定

- 使用 `[F]` 表示核实的外部事实、`[O]` 表示外部报告/意见、`[D]` 表示本项目设计决策、`[H]` 表示待验证假设。
- 报告 issue 时记录：日期、原始 URL、状态、作者报告、后续更正、是否独立复现；不把开放 issue 等同已证实的引擎缺陷。
- 文档中出现的代码、伪代码、目录树、JSON 都是**契约草案/示例**，不是运行代码。
