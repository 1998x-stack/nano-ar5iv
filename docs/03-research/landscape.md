# 06｜外部论文、博客与工具调研

> 截止 2026-11-06 的选取样本。下面的作者主张与本项目推论明确区分，避免把博客观点当成评测结论。

## A. 一手官方与研究材料

| 来源 | 可确认内容 [F] | 对 nano-ar5iv 的启示 [D] |
|---|---|---|
| [LaTeXML 官方架构](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/) | TeX → XML 与 post 责任分开 | 将核心引擎作为 Adapter |
| [LaTeXML 错误码](https://math.nist.gov/~BMiller/LaTeXML/manual/errorcodes/index.html) | Warn/Error/Fatal，错误有时源于转换器本身 | 先分类根因再修复 |
| [arXiv 00README 文档](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md) | JSON `usage:toplevel`、旧 `toplevelfile`、compiler | 元数据优先 |
| [arXiv TeX 提交指南](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/submit_tex.md) | 多文件、子目录、资源和源码清理 | 入口和依赖并非固定布局 |
| [ar5iv 04.2024 数据集](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/) | 2,170,799 HTML；区分无问题/警告/错误 | 建立不同级别质量门禁 |
| [HTML papers on arXiv (2024)](https://arxiv.org/abs/2402.08954) | HTML 可访问性的需求及上线历程 | 将可访问性作为评价维度 |
| [ar5iv Web](https://github.com/dginev/ar5iv) | Web 服务，HTML 由 LaTeXML 转换 | 不能把 Web 层当引擎 |
| [ar5ivist](https://github.com/dginev/ar5ivist) | 独立本地转换封装 | 先做引擎集成原型 |

2024 数据集具体分类：`no_problem=366,232`、`warning=1,304,052`、`error=500,515`（均为**历史结果分类**，非当前覆盖率）。发布页注明数据许可与申请方式，不默认允许自由再分发。

## B. 开发者博客/访谈/邮件讨论

**[Welcome to ar5iv! Wrestling with the Open Problems of Scholarly Writing（Deyan Ginev, 2022）](https://prodg.org/talks/welcome_to_ar5iv)**：回顾 arXMLiv→ar5iv 长期演化，强调宏包长尾、复杂图形/版面、数学排版树与语义区别，以及批量回归。**启示**：不要用一次全量“转换成功率”掩盖版面/公式问题，也不要低估兼容包长尾。[F]

**[Why arXiv chose LaTeXML rather than tex4ht（TeX Users Group 邮件，2022）](https://tug.tug.org/pipermail/tex4ht/2022q1/003167.html)**：开发者明确解释，arXiv 纳入已有可用的 HTML 预览服务，并非官方做过 LaTeXML vs tex4ht 的系统基准比较。**启示**：引擎选择应依据我们自己语料的客观评测，不应宣称 LaTeXML 在全部场景“绝对最好”。[F]

**[arXiv HTML 可访问性说明](https://github.com/arXiv/arxiv-docs/blob/develop/source/about/accessible_HTML.md)**：指出 HTML 转换是渐进过程且存在失败文档。**启示**：允许可解释的部分结果，但要清楚告知读者质量等级。[F]

## C. 可参考的实现生态

- `brucemiller/LaTeXML`：主力结构化转换器。
- `dginev/ar5iv`、`ar5iv-css`、`ar5ivist`：Web、样式、本地转换。
- [`latexml` Rust 主文件检测](https://docs.rs/latexml/latest/latexml/main_tex/index.html)：已有 `find_main_tex` / `find_top_level_texs`，值得直接对照。
- [Rust latexml post 接口](https://docs.rs/latexml/latest/latexml/post/index.html)：展示扫描、书目、交叉引用、MathML 和 XSLT 等后处理组织。
- `Pandoc` / `make4ht` / `plasTeX`：候选备选引擎；各自能力需用同一真实集评测，不在缺少实验时虚列赢家。

## D. 引擎比较计划 [D]

使用同一组 source bundle，统计可读 HTML、无 Fatal、公式完整率、引用边解析率、图表保真、资源成本、最长超时、隔离要求；必须把环境/版本固定。对每个引擎保留原始日志与输出，不将“正常退出码”作为唯一正确标准。

## E. 研究结论

最有价值的不是再写一份“如何运行 docker”的教程，而是将**真问题→最小失败样本→恢复策略→可验证指标**连接起来。下一篇文档将把社区 issue 映射到候选测试案例。
