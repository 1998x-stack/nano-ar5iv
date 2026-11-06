# 15｜分阶段交付路线图（M02 基础实现，真实引擎与语料待验收）

## M00 — Documentation & Evidence（本 PR 目标）

交付：原理、源码恢复、外部博客及 issue 研究、架构/目录、IR 契约、威胁模型、测试矩阵、ADR。M00-B 进一步添加完整 README、逐文件复现与时序设计、50 个 docstring-only .py 模块、14 个 __init__ 包占位及 tests/configs/deployment/examples/scripts 等真实占位目录。**状态：PR #1/#2 已合并；M01/M02 有独立实现，M03–M07 仍为设计。**

## M01 — Foundation + Real Baseline

**已实现（PR #3）**：Python 包/CLI、SHA256 内容寻址源码快照、显式入口、Docker ar5ivist 单次转换适配、诊断日志及 artifact manifest、15 个通过的 unittest 和一个条件跳过的真实集成测试。**自编最小样本真实转换已在 GitHub Actions 通过**：修复 Docker bind mount 参数后 CI 成功；仍未完成生产沙箱安全、性能与科学保真评估，待 PR #4 合入 main。详见 [M01 baseline](../07-reproduction/m01-baseline.md)。

## M02 — Entrypoint Discovery

**已实现（M02 分支）**：现代/旧版 00README、源码清单和哈希验证、受限 ZIP/TAR 暂存、静态依赖图、候选评分、多 root 与 review-required、CLI discover、唯一入口自动 convert 和受限显式 top-k probe。E01–E12 与附加安全/假引擎探测单测已编写。**已核实**：Python 3.11/3.13 各 41 项测试（40 pass、1 skip）以及自编样本真实 Docker discover→probe（[CI run](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42190208723)）。**尚待验收**：真实 arXiv 样本准确率、多候选真实试转换、复杂 TeX 宏解析与生产安全审查。见 [M02 实施报告](../07-reproduction/m02-entry-discovery.md)。

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
