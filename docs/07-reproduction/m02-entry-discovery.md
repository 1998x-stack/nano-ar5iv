# M02｜LaTeX Entrypoint Discovery 与依赖图（实现记录）

> 2026-11-06 · 对照 [M01 baseline](m01-baseline.md)。本阶段聚焦**定位正确的 TeX 根文件**，不是实现完整 TeX 解释器、损坏源码恢复或科学保真保证。**M02 发现成功不代表 LaTeXML 转换一定成功**。

## 操作指令

~~~bash
python -m pip install -e .
# 只做元数据与静态依赖扫描，不需要 Docker
nano-ar5iv --output ./run-data discover ./paper

# 省略 --entry：唯一高置信 root 自动选择；运行 Docker 必须使用受信任的 TeX
nano-ar5iv --output ./run-data convert ./paper --timeout 300

# 如果有多个主文档，必须显式同意逐个转换；绝不会静默合成
nano-ar5iv --output ./run-data convert ./paper --all-roots

# 仍可覆盖自动选择
nano-ar5iv --output ./run-data convert ./paper --entry manuscript.tex

# 歧义根的诊断试运行：仅显式请求，最多 5 个，单个超时<=900s
nano-ar5iv --output ./run-data discover ./paper --probe --top-k 2 --timeout 120
~~~

所有命令的 `--output` 必须位于输入目录外。`discover` 不需要 Docker，`convert` 和 `--probe` 依赖预先拉取的 ar5ivist Docker 镜像，且**只可处理可信来源的本地 TeX**。M01 的 Docker 参数不等同于已通过生产安全审查。

## 解析优先级

1. `00README.json`：解析 `sources[].filename`、`usage=toplevel|include|ignore`、可选 `process.compiler`。保留显式顺序；当没有任何显式 `toplevel` 时，未标记的 `usage` 可视作候选。若指定的主文件缺失、路径越界或元数据矛盾，立即返回 `MANIFEST_ERROR`，不退回启发式猜测。
2. 旧版 `00README.XXX`：解析 `toplevelfile`、`ignore` 等；新旧格式同时存在则报告冲突，不能随机二选一。
3. 无权威主入口元数据：遍历 `.tex/.ltx`，扫描 `\\documentclass`、`\\begin{document}`、`\\end{document}`、章节命令及引用关系；依据 `\\input`、`\\include`、`\\subfile`、`\\import` 等判断文件是否被其他文件包含。
4. 只有唯一**完整且未被其他文档引用**的候选时自动选择；多个独立主文件返回 `MULTIPLE_ROOTS`；只有片段、动态不明或不能确定时返回 `AMBIGUOUS`。
5. 可选择对歧义候选做最多 top-k 次 trial conversion：记录状态和 run manifest，但**即使两个候选都返回 `SUCCEEDED`，也不自动宣告选择了正确主文件**。

参考：[arXiv 00README 规范](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md)、[arXiv TeX 文件说明](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/submit_tex.md)、[latexml Rust main_tex 发现算法](https://docs.rs/latexml/latest/latexml/main_tex/index.html)。

## 元数据示例

~~~json
{
  "process": {"compiler": "pdflatex"},
  "sources": [
    {"filename": "manuscript.tex", "usage": "toplevel"},
    {"filename": "supplement.tex", "usage": "toplevel"},
    {"filename": "draft.tex", "usage": "ignore"}
  ]
}
~~~

此例返回有序的 `MULTIPLE_ROOTS`；默认的 `convert` 会拒绝含糊选择，显式 `--all-roots` 才分别进行转换，不会将论文及附件错误拼接为一个 TeX 文件。

## 输出数据契约（v1）

`EntryDecision`：

~~~json
{
  "schema_version": "1.0",
  "algorithm_version": "m02.1",
  "status": "SELECTED",
  "selected_roots": ["manuscript.tex"],
  "candidates": [
    {"path": "manuscript.tex", "score": 21,
     "evidence": ["documentclass", "begin_document", "end_document", "not_included"],
     "referenced_by": [], "complete_document": true}
  ],
  "edges": [],
  "diagnostics": [],
  "metadata_source": "00README.json",
  "compiler": "pdflatex",
  "ignored": [],
  "trial_results": []
}
~~~

`score` 是可解释的**启发式排序分数而非概率**。真实文件依赖边记录 `source`、`kind`、`requested`、`line`、`resolution`、`target`、`alternatives`；`resolution` 可以为 `resolved`、`missing`、`dynamic`、`ambiguous`、`external`。

## 状态含义

| 状态 | 自动转换 | 处理建议 |
|---|---|---|
| SELECTED | 可以，仍需 Docker 与独立质量检查 | 自动 root 与来源记录 |
| MULTIPLE_ROOTS | 默认禁止；`--all-roots` 后逐篇转换 | 单独保存每个 run |
| AMBIGUOUS | 禁止自动转换 | 显式 `--entry`，或试运行后人工确认 |
| MANIFEST_ERROR | 禁止自动转换 | 修正无效/冲突元数据，必要时显式入口 |
| NO_TEX | 禁止 | M04 计划支持 PDF 单独来源降级 |

`convert` 的 run manifest 新增 `entry_selection`，保留 root 选择方法、候选列表和证据。结果的 `quality_status` 仍是 `NOT_EVALUATED`，直到 M05 独立质量门禁完成。

## 技术边界

- 这是有限的静态分析，不能模拟 catcode 更改、任意宏展开、条件编译、复杂 `\\csname` 生成路径。
- 屏蔽普通 TeX 百分号注释、常见 verbatim 环境和行内 `\\verb`，但不是严格完整 TeX tokenizer。
- 对 `\\input{\\myfile}` 返回 dynamic；跨目录相对路径存在多个匹配时返回 ambiguous；不会擅自删除未知引用。
- 路径解析优先检测提交目录与子文件相对目录；arXiv 官方说明在上传包根目录执行编译，不能将“文件所在目录”误设为工作根。
- 不提供目录外引用、符号链接穿透或无限大小读取；复用 M01 的 snapshot 边界，每个扫描的 TeX 文件另设 8 MiB 上限。
- `--probe` 对未经过安全审查的素材不安全；必须事先确认信任源和隔离。
- 元数据有效性与论文内容保真是两个独立判定；对真实 arXiv 长尾语料的准确率尚未测量。

## 测试与验收

- `tests/test_entry_discovery.py`：现代/旧版元数据、隐式/显式 top-level、nested root、多个 root、被引用的 `subfiles`、动态/缺失/歧义引用、comments/verbatim、无 TeX、稳定输出。
- `tests/test_m02_cli.py`：无需 Docker 的 `discover`、模拟引擎自动选择、显式多根执行、歧义拒判、试运行不擅自选择、来源审计。
- `tests/test_real_m02_opt_in.py`：PR CI 上的真实 ar5ivist 入口自动选择和 HTML 生成测试（需 `RUN_REAL_LATEXML=1`）。
- 原 M01 单元与真实引擎测试应当保持通过；实际 CI 结果见 PR 检查页面，未有结果前不称之为通过。

## 后续阶段

M03 处理缺入口 wrapper/缺宏包/源文件修复和有界重试；M04 负责 XML→PaperDocument；M05 才建立数学公式、图表与参考文献的科学保真硬门禁。它们不属于 M02 已实现功能。
