# 15｜分阶段交付路线图（尚未执行）

## M00 — Documentation & Evidence（本 PR 目标）

交付：原理、源码恢复、外部博客及 issue 研究、架构/目录、IR 契约、威胁模型、测试矩阵、ADR。验收：所有文档均有导航，重要外部事实可追溯，明确“没有代码实现”。**状态：文档提交待审。**

## M01 — Foundation + Real Baseline

交付计划：`pyproject.toml`、`domain` 结构、最简 CLI、固定 LaTeXML/ar5ivist 镜像、单篇有效论文转换、日志与产物保存。**验收**：最小真实样本端到端输出、版本和哈希可核验；暂不自动修复。

## M02 — Entrypoint Discovery

计划：`00README.json`/legacy 兼容、目录 inventory、静态依赖图、候选评分、top-k 试转换、多个 root。**验收**：F01–F12 fixture 全覆盖；不确定性显式报告；与已知正例 baseline 比较。

## M03 — Conservative Recovery

计划：合成包装入口、路径与依赖修复、错误分类、首因分析、有限重试、修复审计。**验收**：R01–R09；没有无审计覆盖作者原文件；无静默吞宏。

## M04 — Canonical PaperDocument

计划：从 XML/HTML 规范化章节、公式、图表、文献、交叉引用，维护 source spans 与 provenance；支持 PDF fallback 的单独来源。**验收**：schema/版本回归、稳定节点 ID、引用完整性。

## M05 — Quality Gate & Golden Dataset

计划：保真度多维门禁、数学符号对照、文献图、资源差分、必要的浏览器视觉检查。**验收**：Q01–Q08，测量 false acceptance/false rejection，报告 `not_run`，禁止零证据 ACCEPTED。

## M06 — Batch Runtime & Service

计划：任务队列、幂等键、缓存、重试、限额、API/UI（按需要），多租户隔离。**验收**：可恢复任务、超时隔离、性能基准、数据许可与安全检查。

## M07 — Research Agent / LLM (Optional)

计划：仅在 M05 基础上引入受限的补丁建议、RAG/知识图谱索引、证据链接。**验收**：预注册消融、补丁可解释/可拒绝、失败时不改变论文科学事实。

## 先后依赖

~~~text
M00 → M01 → M02 → M03 → M04 → M05 → M06
                          └────────────→ M07 (needs M05)
~~~

以**问题验证与数据证据**作为阶段切换条件，不以“目录都创建了”作为完成标准。任何声称完成某阶段必须附实际 commit、测试报告和可重复运行命令。

## 推荐首批迭代议题

1. `P0-M01`：固定 LaTeXML 环境，定义 EngineAttempt 契约并跑通最小样本；
2. `P0-M02`：先实现元数据优先的多 root 发现；
3. `P0-M03`：修复副本策略和首因日志分类；
4. `P0-M05`：公式丢失和断链引用硬门禁；
5. `P1-M06`：任务队列和压力测试。
