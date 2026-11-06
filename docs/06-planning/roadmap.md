# 15｜分阶段交付路线图（M01–M03 已验收，M04.1 正在 CI 验证）

## M00 — Documentation & Evidence（本 PR 目标）

交付：原理、源码恢复、外部博客及 issue 研究、架构/目录、IR 契约、威胁模型、测试矩阵、ADR。M00-B 进一步添加完整 README、逐文件复现与时序设计、50 个 docstring-only .py 模块、14 个 __init__ 包占位及 tests/configs/deployment/examples/scripts 等真实占位目录。**状态：文档与源码占位已提交 PR 待审；业务代码、转换测试、运行服务均未实现。**

## M01 — Foundation + Real Baseline

**已实现（PR #3）**：Python 包/CLI、SHA256 内容寻址源码快照、显式入口、Docker ar5ivist 单次转换适配、诊断日志及 artifact manifest、15 个通过的 unittest 和一个条件跳过的真实集成测试。**新增验收证据**：GitHub-hosted Linux runner 已成功运行固定 ar5ivist 镜像、真实 LaTeX→HTML 与正式 CLI 产物哈希校验（[GitHub Actions M01 real CLI verification](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42189149532)）；生产级沙箱安全、复杂论文兼容性、性能及科学保真仍未验证。详见 [M01 baseline](../07-reproduction/m01-baseline.md)。

## M02 — Entrypoint Discovery

**已实现（PR #7）**：`00README.json`/legacy 入口、静态 TeX 命令扫描、依赖边、候选评分与多 root 选择、拒绝歧义/无效清单、可选 top-k 试转换（仅作为观察，不宣称科学正确）、CLI 自动入口和逐篇多根转换。**阶段基线验收已通过**：[GitHub Actions #42198296310](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42198296310) 中 Python 3.11/3.13 单元与模拟测试、真实 ar5ivist 元数据驱动自动入口 HTML 转换及原 M01 转换都成功；仍需更大真实 arXiv 样本评价入口准确率、复杂宏包兼容与科学保真。[M02 documentation](../07-reproduction/m02-entry-discovery.md)。

## M03 — Conservative Recovery

**M03.1 实现（PR #8）**：基线错误根因分类、显式有序 fragment wrapper、以源码和 LaTeXML 日志双重证据补全缺少的 `\end{document}`、至多 1 次重试、源码 SHA256 校验、隔离副本、patch diff + before/after hash 审计与 parent run 关联；未知宏包等无证据场景拒绝修复。**尚未覆盖**：通用路径重写、任意宏包修复、动态 TeX 宏、PDF 兜底和 M05 质量认证。[M03 implementation](../07-reproduction/m03-conservative-recovery.md)。

## M04 — Canonical PaperDocument

**M04.1 实现（PR #10）**：LaTeXML XML→IR、ar5ivist HTML 回退、PaperDocument schema 1.0、公式 source_tex / MathML（可空）、图/表/单元格跨度、citation/ref 连边、未知科学结构、结构稳定 ID、来源工件 SHA256、幂等派生目录和 `normalize` CLI；真实 Docker 贯通测试与跨版本 Python 回归在 PR 检查中。**剩余**：PDF-only fallback（M04.2）、完整原文 source spans、真实论文长尾语料覆盖率、科学保真质量门禁（M05）。[M04 guide](../07-reproduction/m04-paper-document.md)。

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
