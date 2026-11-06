# M00-A｜从 ar5iv 到 nano-ar5iv：函数级复现蓝图

> 本页所有接口、伪代码和结构是**设计**。没有对应运行代码、没有实测转换结果。本项目复用 LaTeXML，而非按 TeX 语法标准重新实现 TeX。

## 一、复现对象分级

| Level | 目标对象 | 技术事实 | nano-ar5iv 计划输出 |
|---|---|---|---|
| L0 | 上游 `ar5ivist` | 一键 LaTeXML 转换为 ar5iv 风格 HTML | baseline HTML、日志、引擎信息 |
| L1 | `latexml` | TeX 控制序列、宏与文档模型 → XML | 原始 XML 与诊断 |
| L2 | `latexmlpost` | 交叉引用、文献、MathML、图形、XSLT | HTML5 + assets |
| L3 | 不规范源码入口 | arXiv 元数据/静态 TeX 图分析 | EntryDecision、DocumentSet |
| L4 | 可信恢复 | 只在副本修复，根因驱动重试 | RecoveryPlan + attempts |
| L5 | 结构与质量 | 从 XML 构建 Canonical IR，验证保真 | PaperDocument + QualityReport |

官方依据：[LaTeXML architecture](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/)、
[latexmlpost filters](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)。

## 二、端到端伪代码（不可执行）

~~~python
# DESIGN PSEUDOCODE ONLY — not a runnable implementation.
def process(request: ConversionRequest, ports: ConversionPorts) -> JobResult:
    bundle = ports.ingest_and_snapshot(request.input)
    inventory = ports.inventory(bundle)
    roots = ports.find_roots(bundle, inventory)
    if roots.status == "AMBIGUOUS":
        return JobResult(status="REVIEW_REQUIRED", evidence=roots.evidence)
    if roots.status == "NO_TEX":
        return ports.pdf_fallback_or_review(bundle, request.policy)

    results = []
    for root in roots.selected_roots:
        attempts = []
        current = ports.engine.convert(bundle, root, request.config)
        attempts.append(current)

        def inspect(attempt):
            paper = (ports.normalizer.to_paper_document(attempt)
                     if attempt.has_readable_structure else None)
            return paper, ports.quality.assess(bundle, paper, attempts)

        best_paper, best_report = inspect(current)
        best_attempt = current

        for repair_round in range(request.max_repair_rounds):
            if best_report.decision == "ACCEPTED":
                break
            cause = ports.diagnostics.root_cause(current.logs)
            repair = ports.recovery.propose(cause, current, bundle)
            if repair is None or not ports.recovery.is_allowlisted(repair):
                break
            workspace = ports.workspace.apply_copy_on_write(repair)
            candidate = ports.engine.convert(workspace, root, request.config)
            attempts.append(candidate)
            candidate_paper, candidate_report = inspect(candidate)

            if ports.quality.has_verified_non_regression(
                best_report, candidate_report, bundle
            ):
                best_attempt, best_paper, best_report = (
                    candidate, candidate_paper, candidate_report
                )
            else:
                ports.audit.record_rejected_candidate(candidate, candidate_report)
            current = candidate

        results.append((best_attempt, best_paper, best_report, attempts))

    return ports.artifacts.persist_with_manifest(results)
~~~

**重要**：每次候选转换先规范化与评估，再依据已验证的证据决定是否替代上一结果；证据不足时不宣称修复改善。伪代码里所有 Port/函数都是设计接口，尚不可执行。只有 PDF 的输入应独立降级并保留来源。

## 三、入口发现具体分支

~~~text
read 00README.json?
  YES -> validate file existence / multiple roots / declared order
  NO  -> legacy 00README.XXX?
           YES -> parse toplevelfile/include/ignore
           NO  -> inventory TeX candidates
                   -> tokenize static command candidates
                   -> graph {input/include/import/subfile + package/class/bib}
                   -> candidate roots = zero-in-degree + document markers
                   -> rank candidates with evidence (not probability)
                   -> trial convert top-k under resource limit
                   -> accept unique supported root OR emit AMBIGUOUS
~~~

**输入** `SourceBundle + SourceManifest?`，**输出** `EntryDecision`，可包含 `DocumentSet`（多个有序 root）与 `unresolved_edges`。元数据也可能不一致；只有文件存在且安全合法时才采信，不可偷偷自动修正冲突。

## 四、静态扫描的边界

不要用正则充当完整 TeX 解析器。需要最小 tokenizer 识别转义 `%`、comments、verbatim/math contexts、`\\input` 等；对于动态构造（`\\csname`、宏展开生成路径、catcode 改写），返回 `UNKNOWN_DYNAMIC` 并由受限 trial conversion 或用户决策解决。不能对假引用文件产生真实边。

文件映射：`source/arxiv_manifest.py`、`source/tex_scanner.py`、`source/dependency_graph.py`、`source/entry_ranker.py`；实现时按 M02 切片开发，不在此阶段直接运行。

## 五、引擎 Adapter Contract

~~~text
ConversionEngine.convert(
  workspace: ReadOnlySourceWithWritableOutput,
  roots: list[RelativePath],
  config: EngineConfig,
  limit: ExecutionBudget
) -> EngineAttempt {
  engine/version/container_digest, root, command_template,
  exit_status, started_at/elapsed, logs, diagnostic_events,
  xml_uri?, html_uri?, assets[], artifact_hashes[]
}
~~~

要求：不隐藏原始 stderr；失败也返回结构化 attempt；entrypoint 及 environment 参与缓存键；无网络、超时和内存限额是运行前提；用户可在可信本地另行手动运行上游示例。

先实现 `adapters/latexml/runner.py` 的单文件基线，再补细分 XML/HTML 输出；不直接把 ar5iv Web 页面抓取结果当作 TeX 引擎输出。

## 六、根因诊断与安全恢复决策表

| 识别信号 | 诊断族 | 只允许的初始策略 | 必须保留 |
|---|---|---|---|
| 无 root / 有多 root | ENTRY | 元数据 / 图 / 单独试转 | 未选择入口列表 |
| 找不到 input 相对路径 | MISSING_INPUT | 工作目录内路径修正 | 原始命令和相对路径 |
| 仅有完整子章节 | FRAGMENT | 外部 preamble/postamble 或合成 wrapper | synthetic_root=true |
| 未知 .sty/.cls | UNKNOWN_PACKAGE | 已知 binding / 原始包配置对照 | 不认识宏警告 |
| 图片缺失 | ASSET | 证据支持的本地路径映射 | 图注与引用 |
| BibTeX 无数据 | BIBLIOGRAPHY | .bib/.bbl 依赖检测 | cite edge、缺失标志 |
| 公式 MathML 异常 | MATH | 保留 source_tex 和 unresolved | 原公式 |
| 反复错误/超时 | RESOURCE / CASCADE | 有限重试/首因聚类 | first-cause 与资源信息 |

修复操作：`create_file`（仅隔离 workspace）、`rewrite_relative_path`（范围受控）、`inject_preamble`、`change_working_directory`、`select_compatible_binding`；每一项都必须保留 before/after hash 和决策证据。对源码内容的意义性改写默认拒绝。

## 七、结构化归一化逻辑

将 `ltx:section`、`ltx:para`、`ltx:equation`、`ltx:figure`、`ltx:table`、`ltx:bibliography` 等来源实体映射到**versioned** `PaperDocument`。保持 source anchors、raw math TeX、MathML、labels、crossrefs 和 asset paths，生成 canonical node IDs。不能硬编码只匹配 HTML CSS class 名称；IR 类型扩展需兼容旧版本。

对于多个 root，DocumentSet 保留原文件顺序与 cross-document links；绝不静默合并两个正文；被忽略/无法识别节点保存 `unknown_nodes` 而非丢弃。

## 八、QualityGate 如何决定“成功”

**先判定运行结果可读取，再判断结构和科学保真**：

1. XML/HTML 必须合法，错误信息可追踪；
2. math: 提取原始公式和输出公式，检查计数、关键符号和映射；无可靠真值标 `unknown`；
3. bibliography: cite→bib item 是否完整，错误目标是否存在；
4. tables/assets: 节点及资源是否真实存在；
5. PDF baseline（如可获取且同版本）做独立差异，而不是绝对真值；
6. `NOT_RUN/UNKNOWN` 不能默认 `PASS`。

最终 `ACCEPTED` 要求规定的 hard gate 通过；`PARTIAL` 表示已有内容但存在已知降级；`REVIEW_REQUIRED` 表示不能判断；`REJECTED` 表示不可安全发布。用户看到的“可读 HTML”与“保真认证”必须分栏展示。

## 九、失败与成本预算

每个 document root 独立 attempt 序号和时间/CPU/内存/产物限制；重试次数建议先设 **0**（仅 baseline），M03 才引入受控策略（默认上限初稿可为 2，具体依据压测设置）。无限循环、在线下载不受信任宏包、脱离来源的 LLM 补全都禁止。

## 十、逐文件映射

- 输入：`source/inventory.py` + `source/arxiv_manifest.py`。
- 入口：`source/tex_scanner.py` + `source/dependency_graph.py` + `source/entry_ranker.py`。
- 执行：`application/convert.py` → `ports/engines.py` → `adapters/latexml/runner.py`。
- 诊断：`adapters/latexml/diagnostics.py` → `recovery/classifier.py`。
- 修复：`recovery/planner.py` → `recovery/patch_policy.py` → `infrastructure/workspaces.py`。
- 归一化：`normalization/xml_to_ir.py` + `normalization/citation_graph.py`。
- 质量：`quality/structural.py` + `mathematical.py` + `bibliography.py` + `reporting.py`。
- 输出：`application/evaluate.py` → `infrastructure/repositories.py`。

每个文件的 contract 和首批测试见 [模块目录](module-catalog.md)，顺序见 [implementation slices](../07-reproduction/implementation-slices.md)。
