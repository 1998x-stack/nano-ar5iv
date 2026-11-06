# 03｜科研文档的六类核心对象

## 1. 标题与章节

源码中的 `\\section`、`\\subsection` 与段落组织通常能映射成 XML/HTML 的层级结构。实际 HTML 标签/类名由 XSLT 与样式决定，不应将展示 CSS 类名当成永久稳定的数据契约。[LaTeXML 架构](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/)

## 2. 数学公式：排版树 ≠ 数学真值

TeX 公式经数学解析可进入 Presentation MathML；它通常描述**显示结构**，并不保证符号的全部语义（如上标含义、隐式乘法、变量角色）。应同步保留 `source_tex`、`presentation_mathml`、`parse_warnings`、`display_mode`。不能仅凭“有 <math> 标签”判断公式无损。[数学解析文档](https://math.nist.gov/~BMiller/LaTeXML/manual/math/details/)

## 3. 文献引用与交叉引用

识别 `\\label`、`\\ref`、`\\eqref`、`\\cite`、`\\bibliography`/`biblatex` 路径；规范化 `source label → target ID`，找不到目标时保留 unresolved edge；不能丢弃未解析的引用。

## 4. 图形与表格

- 图：保存原始资源路径、文件类型、图注、交叉引用、转换资产路径和替代文本的来源状态。
- 表：保存单元格跨度、内容、注释；对无法解释的嵌套宏保留原始片段。
- SVG：支持矢量输出，但某些 TikZ/PGF 等复杂宏可能不可转换，需记录占位及保真降级。
- CSS 重叠与文本遗漏属于不同错误家族，应有独立测试。

## 5. PaperDocument 的价值 [D]

建议先建完整的结构节点和引用边，再映射到 HTML、RAG Chunk、知识图谱。每个节点同时具备 `source_span?`、`confidence`、`warnings[]` 与 provenance 信息；不强求每个节点在已损坏源码中都有准确行号。

## 6. 必须覆盖的回归样本

- 数学字体丢失导致希腊字母缺失：[arXiv HTML issue #7007](https://github.com/arXiv/html_feedback/issues/7007)（2026-09，用户报告，未在本项目复现）。
- 参考文献/化学公式同时异常：[issue #6475](https://github.com/arXiv/html_feedback/issues/6475)（2026-05，报告）。
- 表格覆盖图片：[issue #6317](https://github.com/arXiv/html_feedback/issues/6317)（2026-04，报告）。
- 文献列表异常：[issue #7230](https://github.com/arXiv/html_feedback/issues/7230)（2026-11，报告）。

**注意**：这些案例是优先级线索而非 nano-ar5iv 测试通过的证据。
