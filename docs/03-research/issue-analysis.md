# 07｜真实 GitHub 评论与故障证据样本

> 采样日期：2026-11-06。样本是**人工定向选择的案例**，不代表 issue 总体发生率。列出用户报告、状态与推导，尚未在 nano-ar5iv 环境复现。

## 样本登记

| Issue | 时间 / 观察 [O] | 状态（检索时） | 设计影响 [D] |
|---|---|---|---|
| [dginev/ar5iv #437](https://github.com/dginev/ar5iv/issues/437) | 2024-01：未知 `.cls` 默认选项影响 amsmath 加载，引发后续多条错误；维护者给出根因 | open | 依赖扫描不能忽略 `\\ExecuteOptions` |
| [dginev/ar5iv #477](https://github.com/dginev/ar5iv/issues/477) | 2024-06：缺 `circledsteps.sty` 支持，导致超时/错误级联 | open | 区分宏包兼容与资源超时 |
| [arXiv/html_feedback #6317](https://github.com/arXiv/html_feedback/issues/6317) | 2026-04：用户报告表格覆盖图片 | open | 独立视觉排版检查 |
| [arXiv/html_feedback #6475](https://github.com/arXiv/html_feedback/issues/6475) | 2026-05：用户报告化学公式、正文文献链接及文献列表异常 | open | 科学领域宏包+文献同时检查 |
| [arXiv/html_feedback #6544](https://github.com/arXiv/html_feedback/issues/6544) | 2026-05：用户报告文献区、目录及图片问题；**随后自行澄清目录在左侧且可正常使用** | open | **更正传播**：不能保留“目录缺失”作为已核实缺陷；加强导航可发现性 |
| [arXiv/html_feedback #7007](https://github.com/arXiv/html_feedback/issues/7007) | 2026-09：`mathdesign/mdbch` 报告希腊字母缺失、PDF 正常 | open | 符号级 PDF/HTML 差分与字体绑定 |
| [arXiv/html_feedback #7230](https://github.com/arXiv/html_feedback/issues/7230) | 2026-11-04：用户报告 `bib` 区域参考文献异常 | open | 参考文献结构/内容比对 |

## 为什么要保留反馈讨论与更正

[#6544 的用户后续评论](https://github.com/arXiv/html_feedback/issues/6544#issuecomment-4535367309) 明确把“目录消失”更正为“目录在左侧，自己没有发现”。这一例子证明：**用户体验问题与转换数据缺损不同**。我们的 issue taxonomy 必须设置 `reported / clarified / reproduced / fixed / regression_verified` 状态，而不是直接复制最初描述。

## 结合维护者的因果判断

[#437](https://github.com/dginev/ar5iv/issues/437) 的工程价值高于一般“页面有问题”的报告：它提供了最小 TeX 例子、缺失依赖的具体机制，以及三个候选修复方向（raw TeX、选项扫描、class binding）。可转成 **dependency-cause-001** 回归集。[F]

## 五大需求聚类 [D]

1. **Entrypoint/Dependency**：找不到 root、多个 root、缺 .cls/.sty、动态包配置。
2. **Scientific semantics**：公式符号/化学式错误、数学解析歧义、定理丢失。
3. **Bibliography/Graph**：文献列表空、引用断链、编号冲突。
4. **Visual fidelity**：图表重叠、缺图、附录目录位置、CSS。
5. **Operational recovery**：超时、无限级联、错误可观测性、重试/缓存。

## 优先级模型（提案，不是实际统计）

`Priority = Impact_on_scientific_content × Reproducibility × Recoverability × Corpus_frequency`；其中各维度需以具体样本数据评分。数学符号和文献被无声删除通常应优先于纯颜色偏差，但必须以用户场景确认。

## 如何扩大调研

后续应按月对 `dginev/ar5iv` 与 `arXiv/html_feedback` 的公开 issue 做带日期窗口的分层采样：每层记录 topic、引擎日志、论文 ID+version、用户浏览器、是否有复现/维护者结论；按 bug 分组去重，避免讨论热度直接等于发生频率。**不能把自动 bot 的确认消息当作修复证据**。
