# M04｜Canonical PaperDocument：从 LaTeXML XML / ar5ivist HTML 到结构化论文

> **实现：M04.1，PR #10（2026-11-06）；真实 Docker+Python CI 已通过**。本阶段交付版本化科学文档 IR、XML 原生语义解析、HTML 回退、引用关系与表格模型、来源与完整性审计。**未实现科学保真质量认证、通用 PDF 提取或 RAG 服务**。输出始终为 `quality_status=NOT_EVALUATED`。

## 1. 为什么需要 Canonical IR

M01–M03 解决源码存档、主文件选择、容器转换和受限恢复，但 HTML 结构不适合直接做可靠的论文索引。M04 将转换结果转成可版本化、可追溯的 JSON，使 M05 可以独立验证 MathML、公式、引用、图表与数据一致性。

~~~text
SourceBundle + EntryDecision + EngineAttempt
                |
             run manifest (immutable)
                | validate input SHA256, size, path, source hashes
                v
   XML preferred if included in same run, else HTML
             /                      \
LaTeXML native XML              ar5ivist HTML5
 XML element semantics          bounded HTML parser
             \                      /
          M04 canonical PaperDocument
             |
       normalizations/<run_id>/<derivation_id>/
           paper-document.json
           normalization-manifest.json
             |
       M05 quality gate [NOT IMPLEMENTED]
~~~

上游依据：[LaTeXML XML Schema](https://math.nist.gov/~BMiller/LaTeXML/manual/schema/LaTeXML-common/)、[latexmlpost 交叉引用和 MathML](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)、[HTML/CSS classes](https://math.nist.gov/~BMiller/LaTeXML/manual/cssclasses/)。

## 2. 真实可用命令

先在**可信本地源码**目录上执行原有转换（Docker 和预先拉取的 ar5ivist 镜像是前提）：

~~~bash
python -m pip install -e .
nano-ar5iv --output ./run-data convert ./examples/trusted-minimal \
  --entry manuscript.tex --timeout 300 > ./convert-result.json
~~~

找到 `convert-result.json` 中的 `manifest_path`，例如 `./run-data/runs/<run-id>/manifest.json`，再运行：

~~~bash
nano-ar5iv --output ./run-data normalize \
  ./run-data/runs/<run-id>/manifest.json --format auto
~~~

当用户提供的 run manifest 包含经哈希验证的原生 XML 产物时，`--format auto` 优先 XML；否则使用已保存的 HTML（当前默认 ar5ivist 转换）。`--format xml` 只允许 XML，缺失即拒绝；`--format html` 强制 HTML 回退。

`normalize` **无需 Docker**，但必须指向 **M01–M03 已生成、属于同一 `--output` 目录的可信 run manifest**。它不接受任意互联网 URL，不从 HTML 下载外链，不更改原来的 `runs/<id>/` 及源码快照。

返回示例（计数以实际运行结果为准）：

~~~json
{
  "status": "NORMALIZED",
  "document_id": "paper:<sha256-derived-id>",
  "document_path": "run-data/normalizations/<run-id>/<derivation-id>/paper-document.json",
  "source_kind": "latex_html",
  "schema_version": "1.0",
  "quality_status": "NOT_EVALUATED",
  "counts": {
    "nodes": 3,
    "equations": 2,
    "assets": 0,
    "citations": 0,
    "unresolved_relations": 0,
    "unknown_nodes": 0
  }
}
~~~

上面的计数、路径与 ID 为**解释结构的示例**，不是已运行真实论文的报告。

## 3. 正式数据契约（M04.1）

### PaperDocument 顶层

| 字段 | 类型 | 语义 |
|---|---|---|
| `schema_version` | string | 当前为 `1.0`，后续应迁移/兼容 |
| `normalizer_version` | string | 当前为 `m04.1` |
| `document_id` | string | 来源 bundle ID + root path 派生的稳定文档标识 |
| `root_path` | string | M01/M02 确认的主文件 |
| `source_kind` | string | `latex_xml` / `latex_html`，不能伪装 PDF 为 LaTeX |
| `engine` | object | 转换镜像引用、image ID、进程状态、退出码 |
| `provenance` | object | run ID、bundle ID、原 run manifest SHA256、输入文件 SHA256 |
| `nodes` | array | 章节/段落/方程组/参考条目，含 parent/children ID |
| `equations` | array | source_tex（可空）、Presentation MathML（可空）、verified=false |
| `assets` | array | 图片/表格、标题、href、是否外链、表格行/列及跨度 |
| `citations` | array | citation/ref 的显示文本及其原始目标 |
| `relations` | array | 引用边，含 RESOLVED/UNRESOLVED 和 target ID |
| `unknown_nodes` | array | 显式收录无法归一化的特定科学结构的有界 raw markup |
| `warnings` | array | 有损回退、未知内容、截断等说明 |
| `quality_status` | string | **固定 NOT_EVALUATED**（M05 之前） |

`source_ref` 只接受有独立证据支持的 TeX span。当前 XML/HTML 解析器不会按段落顺序推断 `source_ref`；不存在源坐标时是 `null`。`source_id` 只是转换输出里已有的 xml:id / id，并**不等同**于作者源码行号。

### 公式

`Equation`：`id/source_tex/presentation_mathml/parent_id/source_id/source_ref/verified`。XML 直接保存 LaTeXML 数学元素的 `tex` 属性（如果有）；MathML 保存完整 XML 子树。HTML fallback 仅在实际 HTML 中存在 `annotation encoding=*tex*` 或明确 `data-tex` 才能填 `source_tex`，不通过 MathML 反推原始公式。

### 章节、表格和引用

`DocumentNode` 支持 `section/subsection/paragraph_text/equation/bibliography_item` 等结构；`parent_id` 和 `children` 表示归属。表格 `Asset.table_rows` 是二维 `TableCell` 列表，每格含 text、rowspan、colspan、source_id。它是结构化单元格数据，不是视觉布局验证。

`Citation` 可区分 `citation` 与 `reference`。`Relation` 保存原始 `idref` / `href`，当目标 xml:id/id 可映射到本篇文档的节点时标 `RESOLVED`；无法映射或跨文档链接则保留 `UNRESOLVED`，**不会构造不存在的目标**。

### ID 稳定性边界

相同 bundle/root、相同标记树和位置，会得到相同 ID；路径/层级发生变化时节点 ID 可能发生改变。**不承诺节点任意重排后的 ID 不变**。版本迁移时需要记录文档 schema/normalizer 版本。

## 4. XML 优先与 HTML 回退的区别

| 能力 | 原生 LaTeXML XML | ar5ivist HTML5 回退 |
|---|---|---|
| 文档层级 | 标准 LaTeXML 命名空间 | `ltx_*` class 和 HTML 结构 |
| 公式源码 | 若有 `ltx:Math.tex` 则保存 | 通常缺失，仅从明确 annotation 等字段读取 |
| MathML | 保留子树 | 从 HTML 中的 math 元素重建；可能损失原始序列化 |
| 参考文献 | `idref` 与 `xml:id` | `href="#..."` 与 `id` |
| 图表 | `ltx:figure/table/graphics` | `ltx_figure/ltx_table/table/img` |
| 未识别结构 | 特定 theorem/proof/listing 等保留有界 XML | 特定 `ltx_*` 结构保留重建后的标记 |
| TeX 原始 span | 未验证则 null | 未验证则 null |
| 科学保真认证 | **没有** | **没有** |

HTML 模式会产生 `HTML_DOM_RECONSTRUCTED` warning。不执行 JS、CSS、TeX 宏，也不联网；不会因为 HTML 视觉上正确而自动标 `ACCEPTED`。

## 5. 产物与重放

~~~text
run-data/
  sources/<bundle_id>/...                     # M01 原始输入（保持不变）
  runs/<run_id>/manifest.json                # M01–M03 运行证据（保持不变）
  runs/<run_id>/artifacts/html/index.html
  normalizations/<run_id>/<derivation_id>/
    paper-document.json                       # PaperDocument schema 1.0
    normalization-manifest.json               # input hash, output hash, IR version
~~~

派生 ID 来自原始 run ID、输入工件 SHA256、schema/normalizer 版本和格式。重复输入会指向同一目录；如果既有派生文件被篡改，会显式失败，不覆盖原记录。

`normalize` 在写出前会验证输入 run manifest 路径、ID、artifact 相对路径、SHA256/大小和原先记录的引擎信息。产物写入时使用独立临时目录并最终原子重命名。

## 6. 安全限制与验收边界

- XML 禁止 DOCTYPE/ENTITY 声明、单个输入上限 20 MiB；最多 25,000 个元素、128 级深度。
- HTML 用 Python 标准库重建有限 DOM，不执行 scripts/styles；不能将任意 HTML 当作可执行或可信的网页在高权限页面渲染。
- 路径不能跨出已有 run artifact 根目录；独立派生文件不能覆盖原始 run。
- 外部图片 URL 仅归类为 `EXTERNAL_UNFETCHED`；本地相对资源仅标 `NOT_CHECKED`，不会盲目下载/解析 SVG 或图片内容。
- 仅保留**特定未知科学结构**（theorem/proof/listing 等）；非全部宏及未知 CSS 结构都能在 M04 自动恢复。M05 应追加未知节点覆盖率验证。
- 当前没有 PDF-only 转结构化 `PaperDocument` 的实现；PDF 降级路径单列为后续 M04.2，不假装其已完成。
- 编译成功、HTML 有章节、数学节点数存在，都**不是科学事实得到验证**；M05 必须针对公式符号、引用闭合、图表以及 PDF 对照设立独立质量门禁。

## 7. 测试与证据

`tests/test_m04_normalization.py`：LaTeXML 命名空间章节、XML MathML/TeX、引用、表格跨度、unknown preservation、HTML5 class 模型、失效 IDREF、DTD 拒绝、大小/深度预算。

`tests/test_m04_run_integration.py`：模拟 EngineAttempt → manifest → XML/HTML 自动选择 → 版本化派生文件、SHA256 校验、幂等、篡改拒绝、CLI 结果。

`tests/test_real_m04_opt_in.py`：GitHub-hosted 独立 Docker job 中，实际转换一篇自编最小 TeX，再运行 `normalize`，检查至少一个章节/公式与 MathML、provenance、派生文档 SHA256。测试通过与否应以 PR #10 的具体 CI run 为准。

### 已完成的实际验收

- [GitHub Actions #42204716397](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42204716397)：三组作业全部 success。
- Python 3.11、3.13：各运行 76 个 unittest，**72 通过、4 个需要实际 Docker 的用例按矩阵设计跳过**；byte-compile 成功。
- 独立真实 Docker 作业：自编最小 LaTeX → ar5ivist HTML → `normalize` → `PaperDocument`；确认 MathML 存在、结构节点/公式已提取、输入转换 run hash 和独立派生 JSON SHA256 匹配，并通过 M01/M02/M03 真实回归。
- **仅证明自编样本链路可运行**，不代表大规模真实论文的公式、图表、引用保真、PDF fallback 或 M05 质量门禁通过。

上游参考：[LaTeXML XML element schema](https://math.nist.gov/~BMiller/LaTeXML/manual/schema/LaTeXML-common/)；[latexmlpost mathematics/cross references](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)；[LaTeXML HTML classes](https://math.nist.gov/~BMiller/LaTeXML/manual/cssclasses/)。

## 8. 下一阶段 M05

构建跨源可测量的科学质量门禁：方程/数学符号缺失、引用断链、图表资源缺失及结构异常；仅当必需证据完整且 hard gates 通过，才允许使用 `ACCEPTED`。M04 的归一化状态与科学质量状态必须始终分开。
