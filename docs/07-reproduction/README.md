# 复现手册｜先复现上游，再实现 nano-ar5iv

> 本文是**操作设计和上游实验指导**，本仓库目前不提供可运行代码。只在**可信论文源码**的独立工作目录操作；不可信 TeX 必须先建设安全隔离工作环境。本页实验尚未由项目执行验证。

## 目标、环境与验收输出

实验 R0：证实从一个明确 TeX 主文件转换为 HTML5/MathML，收集 XML、log、引擎版本、根入口和资源，建立 baseline。

要求：Linux/macOS、Docker（ar5ivist 路径），或受控环境安装的 LaTeXML CLI（两阶段路径）；测试目录内无密钥/私人文件；上游 Docker 镜像按版本固定，例如 `latexml/ar5ivist:2512.17`。正式对照实验进一步记录 image digest，单纯 tag 可能被重发。

> `Docker -v "$(pwd)"` 会把整个工作目录挂载给容器：仅对隔离、经过信任的论文素材使用，不可直接拿生产主机共享仓库或任意网友上传档案执行。

## R0.1 手动确认论文入口（无需 main.tex）

1. 列出输入文件：`.tex/.ltx/.sty/.cls/.bib/.bbl`、图片及 `00README.json`。
2. 新版 arXiv metadata 的 `sources[].usage="toplevel"` 优先；旧版 `00README.XXX` 的 `toplevelfile` 次之。
3. 无元数据则检查 `\\documentclass`、`\\begin{document}`、`\\input/\\include` 引用关系；记录是“候选”而非断言。
4. 有多个 root 时**分别转换**，不要人为将正文和 supplement 混合；缺 preamble 的片段作为独立恢复实验。

参考：[arXiv 00README](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md)。

## R0.2 ar5ivist 一体化基线

~~~bash
# 示例：paper/ 中的主文件叫 manuscript.tex
cd paper
mkdir -p html
docker run --rm -v "$(pwd)":/docdir -w /docdir \
  --user "$(id -u):$(id -g)" \
  latexml/ar5ivist:2512.17 \
  --source=manuscript.tex \
  --destination=html/manuscript.html
~~~

若成功，读取 `html/manuscript.html` 及 `manuscript.latexml.log`（上游常见日志命名）；记录镜像版本、输入哈希、依赖列表、实际命令、退出码、耗时和输出 SHA256。[ar5ivist 官方 README](https://github.com/dginev/ar5ivist)。

## R0.3 拆分成 TeX→XML→HTML5

在**已独立安装**的 LaTeXML 环境运行，具体依赖与版本由实验者记录：

~~~bash
latexml --destination=manuscript.xml manuscript.tex
latexmlpost --format=html5 --destination=manuscript.html manuscript.xml
~~~

确认 XML 中的章节、math、label、cite 与 HTML 中的 `<math>`、目标链接和资源。对同一输入不得假定两条路径的样式完全相同。参数来源：[latexml](https://math.nist.gov/~BMiller/LaTeXML/manual/commands/latexml.html) / [latexmlpost](https://math.nist.gov/~BMiller/LaTeXML/manual/commands/latexmlpost.html)。

## R0.4 没有完整文档头尾

在**隔离副本**中先评估 `--preamble=header.tex` 与 `--postamble=footer.tex`（低层级 latexml 参数），只提供确实缺失的部分，必要时使用合成 wrapper；注明文档类来源与 synthetic flag。对没有明确章节顺序的多个 fragment **不要猜测合并**。

## R0.5 错误诊断与保真

查看首个有意义错误而不只看总错误数；例如未知 class 的 `\\ExecuteOptions` 可能间接造成数学宏未加载（[case #437](https://github.com/dginev/ar5iv/issues/437)）。数值、公式、引用、图像检查须独立于命令退出码；重大丢失标 `REVIEW_REQUIRED`。

## 建议实验记录（模板）

~~~yaml
experiment_id: R0-001
input_source: local_trusted
paper_identifier: null
version: null
root: manuscript.tex
source_sha256: "<fill_after_run>"
engine: latexml/ar5ivist
engine_tag: "2512.17"
engine_digest: "<record_actual_digest>"
command: "<record_shell_command>"
environment: "<OS-and-architecture>"
resources: "<CPU/memory/time-limits>"
exit_status: "<observed>"
artifacts:
  xml_sha256: null
  html_sha256: "<fill_after_run>"
  log_sha256: "<fill_after_run>"
diagnostics: "<record_original_errors>"
quality:
  structure: NOT_RUN
  math: NOT_RUN
  bibliography: NOT_RUN
  visual: NOT_RUN
result: UNVERIFIED
~~~

该模板不是已经发生的实验报告。正式复现应同时保留 baseline 与故障样本的失败证据。

## 下一阶段 nano-ar5iv 的自动化复现

M01 把上述 R0 结果标准化为 `EngineAttempt` 和 artifact manifest；M02 增加 root discovery；M03 加 recovery；M04–M05 构建 PaperDocument/质量门禁；M06 引入任务服务。逐文件顺序见 [implementation slices](implementation-slices.md)。
