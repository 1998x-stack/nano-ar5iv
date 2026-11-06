# nano-ar5iv

> **Status: Documentation / Architecture v0.1 — no application code implemented.**  
> 更新时间：2026-11-06

**nano-ar5iv** 是面向科研论文的「可恢复、可验证、可追溯」LaTeX 源码转换系统设计。目标是把不规则论文源码包转换为结构化论文（PaperDocument）及 HTML5/MathML，并明确记录任何缺失、修复及质量风险。

## 为什么做

ar5iv 的成功基础是 **LaTeXML 对 TeX 宏、文档结构和数学表达式的解析能力**，再配合参考文献/交叉引用/图片的后处理、批量转换及网页服务。但真实论文不总是拥有 `main.tex`：可能有多个入口、缺失宏包、动态引用、损坏档案或只有 PDF。真正需要补足的是**源码恢复和结果质量**，而非再发明一个 TeX 引擎。

## 文档导览

| 系列 | 内容 |
|---|---|
| [研究与技术原理](docs/01-foundations/ar5iv-overview.md) | ar5iv 系统边界与端到端架构 |
| [LaTeXML 内核](docs/01-foundations/latexml-pipeline.md) | Mouth / Gullet / Stomach → XML → latexmlpost |
| [数学、图表与引用](docs/01-foundations/semantic-elements.md) | MathML、公式语义、交叉引用、图表 |
| [源码入口发现](docs/02-source-recovery/entry-discovery.md) | `00README`、多入口、依赖图、评分 |
| [损坏源码恢复](docs/02-source-recovery/recovery-playbook.md) | 包装入口、缺宏包、日志反馈、PDF 兜底 |
| [资料与评论研究](docs/03-research/landscape.md) | 论文、文章、框架对比 |
| [真实问题与用户反馈](docs/03-research/issue-analysis.md) | 可追溯的 GitHub issue 样本及研究结论 |
| [总体架构](docs/04-architecture/system-architecture.md) | 领域边界、调度、数据流 |
| [代码类别与目录](docs/04-architecture/code-categories.md) | 未来代码组织方案（仅设计） |
| [数据契约](docs/04-architecture/data-contracts.md) | SourceBundle、RecoveryPlan、PaperDocument |
| [架构决策 ADR](docs/04-architecture/decisions.md) | 引擎选择、版本化、LLM 限权 |
| [质量与评估](docs/05-quality/evaluation.md) | 内容、语义、视觉、可信度 |
| [安全与威胁模型](docs/05-quality/security.md) | 不可信 TeX 的隔离与资源限额 |
| [测试计划](docs/05-quality/test-strategy.md) | Goldens、故障回归、验收指标 |
| [分阶段路线图](docs/06-planning/roadmap.md) | 文档 → 原型 → 恢复 → 验证 → 服务 |
| [来源目录](docs/REFERENCES.md) | 官方资料、研究论文、实际反馈链接 |

## 设计原则

1. **Source-first**：保留原始压缩包、准确记录来源和版本。
2. **Deterministic-first**：先应用 `00README` 与静态依赖分析，后用有限的修复策略。
3. **Never overwrite originals**：所有修复都生成隔离副本与差异记录。
4. **Separate availability from fidelity**：能输出 HTML ≠ 内容正确。
5. **Fail explicitly**：缺失公式/图表/引用必须体现在结果状态中。
6. **Sandbox by default**：禁止把任意论文 TeX 当可信构建脚本执行。

> 本仓库当前**只有文档**。设计中的 `src/`、`tests/`、API、命令均为未来规划，不意味着已经存在或经过验证。

## 研究边界

参考项目：[LaTeXML](https://github.com/brucemiller/LaTeXML)、[ar5iv](https://github.com/dginev/ar5iv)、[ar5ivist](https://github.com/dginev/ar5ivist)、[arXiv HTML](https://info.arxiv.org/about/accessible_HTML.html)。nano-ar5iv 不是这些项目的官方实现，也不声称兼容所有 LaTeX 宏包。
