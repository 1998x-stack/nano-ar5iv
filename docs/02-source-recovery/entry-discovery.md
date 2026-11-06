# 04｜没有 main.tex：入口发现与依赖图

## 输入并非规范工程

论文主文件可能是 `paper.tex`、`ms.tex`、`thesis.ltx`，可能位于子目录，且可能有多个顶层文档或仅有 `.tex` 片段。**文件名不能决定入口**。[arXiv TeX 提交指南](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/submit_tex.md)

## 推荐的候选优先顺序 [D]

1. **读取提交元数据**：若存在有效 `00README.json`，按 `sources[].usage == "toplevel"` 与声明顺序选择顶层文档；记录 `compiler` 和 `ignore/include`。但需验证文件实际存在且路径没有越界。
2. **兼容旧元数据**：解析旧 `00README.XXX` 的 `toplevelfile`、`ignore` 等；和 JSON 冲突时生成诊断而不是静默猜测。
3. **图分析**：从 `\\input`、`\\include`、`\\subfile`、`\\import` 等静态可识别形式建立依赖边；标注 `dynamic/unresolved/cycle`，禁止将潜在依赖当作普通正文。
4. **启发式排序**：`\\documentclass` / `\\documentstyle`、`\\begin{document}` / `\\end{document}`、作者/章节特征、是否被其他文件引用、文件内容长度；排除 `.bib`、明显模板、`%auto-ignore` 等。
5. **试转换验证**：对 top-k 候选并行度受限地调用转换器；选出结构和质量更好的候选，同时保存其他结果与歧义标志。

参考：[现代 00README 规范](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md)、[Rust `main_tex` API](https://docs.rs/latexml/latest/latexml/main_tex/index.html)。

## 一个可审计的评分草案（非实际训练结果） [D]

`score = 12*explicit_toplevel + 8*has_documentclass + 5*has_begin_document + 3*has_end_document + 2*chapter_presence - 9*is_included_by_other - 6*looks_like_template`。元数据作为“高优先级证据”独立处理，分数仅给**无权威元数据**的候选排序，避免把自定义分值伪装成概率。

## 多个入口≠多个错误

例：`main.tex` + `supplement.tex` 都是完整文档，或 arXiv JSON 显式列出两个 toplevel。计划输出 `DocumentSet`：ordered list of root documents，不把二者拼成一个新的正文字符串。若仅有正文片段则进入包装器恢复，且标注 `synthetic_root`。

## 文件发现必须处理的边界

- 多层目录、重复 basename、大小写、空格与 Unicode 路径；
- 注释中的假 `\\input`、verb/verbatim 中的伪命令；
- `\\includeonly`、条件命令、动态宏构造路径；
- 引入子文档的 `subfiles`、`import` 系列；
- Windows 路径与 PDF 被改名成 `.tex`；
- 孤立 .bib、.bbl、.sty、.cls 和附件；
- 缺失引用、环、同名多目标、超出工作目录的相对路径。

静态扫描器只能标明“不确定”，不能宣称处理完整 TeX 语法。

## 入口发现结果契约 [D]

`EntryCandidate{relative_path, evidence[], score?, referenced_by[], missing_dependencies[], rank, confidence_band}`；`EntryDecision{selected_roots[], alternatives[], ambiguity_reason?, metadata_source, algorithm_version}`。要求支持 `no_tex`、`ambiguous`、`multiple_roots`、`confidence_insufficient`。

## 验收规则

对有明确有效 `00README.json` 的样本，优先尊重 metadata；对“未找到确定入口”的包返回结构化原因和候选表，不直接随机选 `main.tex`。
