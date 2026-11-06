# 资料索引与证据等级

> 检索更新：2026-11-06。链接不等于已通过本项目复现实验。引用原文应遵守版权及许可证，仓库记录的是简短事实、出处及独立设计结论。

## 一手官方与项目源码 [F]

1. [LaTeXML Manual — Architecture](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/)：`latexml`/`latexmlpost` 分工。
2. [LaTeXML — Core pipeline](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexml/)：Digestion、Construction、Rewriting、Math Parsing。
3. [LaTeXML — Postprocessing](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)：CrossRef/Bib/Graphics/MathML/XSLT。
4. [LaTeXML — Math Details](https://math.nist.gov/~BMiller/LaTeXML/manual/math/details/)：数学树与语义歧义。
5. [LaTeXML — Error Codes](https://math.nist.gov/~BMiller/LaTeXML/manual/errorcodes/index.html)：等级、分类、错误来源警告。
6. [dginev/ar5iv](https://github.com/dginev/ar5iv)：Web 服务。
7. [dginev/ar5ivist](https://github.com/dginev/ar5ivist)：本地 Docker 转换。
8. [brucemiller/LaTeXML](https://github.com/brucemiller/LaTeXML)：主转换器源码。
9. [arXiv TeX Submission](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/submit_tex.md)：多文件提交规范。
10. [arXiv 00README JSON and legacy](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md)：入口及编译配置。
11. [Rust latexml main_tex](https://docs.rs/latexml/latest/latexml/main_tex/index.html)：已有入口发现算法参考。
12. [Rust latexml post](https://docs.rs/latexml/latest/latexml/post/index.html)：后处理接口。
13. [arXiv HTML accessibility](https://github.com/arXiv/arxiv-docs/blob/develop/source/about/accessible_HTML.md)：HTML 价值及限制。
14. [ar5iv dataset 04.2024](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/)：历史快照和使用许可。

## 研究、讲座、博客和开发者观点 [F/O]

15. [HTML papers on arXiv — why it is important (2024)](https://arxiv.org/abs/2402.08954)：可访问性与 HTML 的论文说明。
16. [Deyan Ginev — Welcome to ar5iv! (2022)](https://prodg.org/talks/welcome_to_ar5iv)：技术长尾、规模化与长期演进。
17. [TeX Users Group — Why LaTeXML rather than tex4ht? (2022)](https://tug.tug.org/pipermail/tex4ht/2022q1/003167.html)：开发者明确未做官方统一性能选型。
18. [W3C Math list — 2024 ar5iv dataset announcement](https://lists.w3.org/Archives/Public/www-math/2024Apr/0016.html)：作者公告与历史数据集。

## GitHub issue 与具体用户评论 [O]

19. [dginev/ar5iv #437](https://github.com/dginev/ar5iv/issues/437)：未知类选项引发级联。
20. [dginev/ar5iv #477](https://github.com/dginev/ar5iv/issues/477)：circledsteps 包支持与 timeout。
21. [arXiv/html_feedback #6317](https://github.com/arXiv/html_feedback/issues/6317)：表格/图片重叠报告。
22. [arXiv/html_feedback #6475](https://github.com/arXiv/html_feedback/issues/6475)：化学公式及参考文献报告。
23. [arXiv/html_feedback #6544](https://github.com/arXiv/html_feedback/issues/6544)：内容布局与导航混淆。
24. [#6544 用户后续更正](https://github.com/arXiv/html_feedback/issues/6544#issuecomment-4535367309)：目录可用，原报告应更正。
25. [arXiv/html_feedback #7007](https://github.com/arXiv/html_feedback/issues/7007)：mathdesign Greek symbol fidelity。
26. [arXiv/html_feedback #7230](https://github.com/arXiv/html_feedback/issues/7230)：2026-11 的 bib 段落异常。

## 引用和复现说明

- [F] 官方资料/官方项目文档/可验证仓库源码；不代表 nano-ar5iv 自己验证。
- [O] 外部个人报告或主张；在独立最小复现前不直接称为已确证的技术缺陷。
- [D] 本项目建议和技术决策；与外部事实区分。
- [H] 尚待实验检验的假设；不应写成达成的性能结论。

有些博客或 GitHub issue 可能在未来更改，正式实现时要保留 `retrieved_at` 和已固定的提交/文档版本。 
