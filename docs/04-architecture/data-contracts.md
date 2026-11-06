# 10｜数据契约与事件设计（早期 Proposal + M04 已实现 IR）

本页早期样例属于 M00 研究提案，**不要将 schema_version 0.1 或示例字段当作当前运行时 API**。M01–M03 的源码/转换数据契约已经演进，**M04 版本化 PaperDocument dataclass schema 1.0 已实际实现**。真实字段、校验、M04 运行演示请查 [M04 guide](../07-reproduction/m04-paper-document.md)，而非依赖下面的旧草图。

## SourceBundle

~~~json
{
  "schema_version": "0.1",
  "bundle_id": "sha256:<archive-hash>",
  "origin": {"kind": "arxiv_source", "arxiv_id": "2402.08954", "version": 1},
  "files": [
    {"path": "paper.tex", "sha256": "<file-hash>", "role": "unknown", "size_bytes": 1234}
  ],
  "immutable_archive_uri": "artifact://archives/...",
  "extraction_policy_version": "v1"
}
~~~

`path` 为解压根目录内的规范相对路径；不接受绝对路径、`..`、软链接越界、特殊文件；文件系统身份与 arXiv 版本分离。

## EntryDecision & DependencyEdge

~~~json
{
  "selected_roots": ["manuscript.tex"],
  "alternative_roots": ["supplement.tex"],
  "selection_basis": "heuristics_and_trial_conversion",
  "ambiguous": true,
  "edges": [
    {"from": "manuscript.tex", "to": "sections/method.tex",
     "kind": "input", "resolution": "static", "evidence": {"line": 12}}
  ]
}
~~~

枚举：`kind=input|include|subfile|import|bibliography|graphics|class|package`；`resolution=static|dynamic|missing|external|unknown`。动态引用必须承认未知。

## Diagnostics 与 RecoveryPlan

~~~json
{
  "diagnostic": {
    "severity": "Error",
    "family": "UNKNOWN_MACRO",
    "origin": "latexml",
    "raw_code": "undefined",
    "source_span": null,
    "is_cascade": false
  },
  "repair_plan": {
    "strategy": "synthetic_wrapper",
    "operations": [{"action": "create", "target": "__generated_main.tex",
                    "source_file_sha256": null, "reason": "missing_root"}],
    "modifies_original": false,
    "requires_review": true
  }
}
~~~

所有 repair operation 必须可定位可回滚；不允许无来源的 `replace_entire_document` 操作。

## Canonical PaperDocument

~~~json
{
  "schema_version": "0.1",
  "document_id": "paper:<source-hash>:root-0",
  "source_kind": "latex",
  "root_path": "manuscript.tex",
  "engine": {"name": "latexml", "version": "<pinned-version>",
             "image_digest": "<sha256>"},
  "nodes": [
    {"id": "s1", "kind": "section", "title": "Introduction",
     "children": ["p1"], "source_ref": "manuscript.tex:25-42",
     "synthetic": false}
  ],
  "equations": [
    {"id": "eq1", "source_tex": "E=mc^2",
     "presentation_mathml": null, "verified": false}
  ],
  "assets": [],
  "citations": [],
  "relations": [],
  "warnings": [],
  "quality_status": "REVIEW_REQUIRED"
}
~~~

`source_ref` 只在有可信映射时出现；无源码 span 时为 null，不得按 HTML 位置伪造。稳定 ID 的生成不能依赖运行时随机数；节点重排应有 versioned ID 语义。

## QualityReport

~~~json
{
  "job_id": "job:<stable-key>",
  "attempt": 2,
  "output_created": true,
  "dimensions": {
    "structure": {"status": "pass", "evidence": []},
    "math": {"status": "unknown", "evidence": ["missing_source_alignment"]},
    "bibliography": {"status": "fail", "evidence": ["unresolved_ref_17"]},
    "visual": {"status": "not_run", "evidence": []}
  },
  "decision": "REVIEW_REQUIRED",
  "reason_codes": ["BIB_UNRESOLVED"]
}
~~~

**禁止**把 `unknown / not_run` 自动记为 `pass`。分类输出可为 `ACCEPTED|PARTIAL|PDF_FALLBACK|REVIEW_REQUIRED|REJECTED`；应用任务层另有 `SUCCEEDED|DEGRADED|FAILED` 等状态，二者不要混用。

## Port Interfaces（文字约定）

- `SourceRepository.get_bundle(bundle_id) -> SourceBundle`
- `EntryDiscoverer.discover(bundle) -> EntryDecision`
- `ConversionEngine.convert(workspace, roots, options) -> EngineAttempt`
- `DiagnosticClassifier.classify(raw_log) -> DiagnosticSet`
- `RepairPlanner.plan(bundle, attempts, policy) -> RecoveryPlan`
- `Normalizer.normalize(attempt) -> PaperDocument`
- `QualityGate.assess(bundle, document, attempts) -> QualityReport`
- `ArtifactStore.put_immutable(data) -> content_addressed_uri`

以上是未来接口签名草图，不是现成 Python 函数。

## M04.1 已实现的数据契约（schema_version 1.0）

真实 Python 类型位于 `src/nano_ar5iv/domain/documents.py`，有 `PaperDocument.to_dict()`。重要字段：

- `document_id / root_path / source_kind (latex_xml|latex_html)`；
- `engine / provenance`，含 `run_id / source_bundle_id / source_run_manifest_sha256 / input_artifact / input_sha256 / source_span_status`；
- `nodes[]`：`id/kind/parent_id/title/text/source_id/source_ref/children[]`；
- `equations[]`：`id/source_tex/presentation_mathml/parent_id/source_id/source_ref/verified=false`；
- `assets[]`：`id/kind/href/caption/parent_id/source_id/availability/table_rows[][]`；
- `citations[]` 与 `relations[]`：原始目标、映射后的 target ID、RESOLVED/UNRESOLVED；
- `unknown_nodes[] / warnings[]`：异常语义结构与有损回退证据；
- `quality_status=NOT_EVALUATED`；M05 质量认证尚不存在。

每个输出独立保存 `paper-document.json` 与 `normalization-manifest.json`。来源 run artifact 需要通过 SHA256/大小核验；已有派生被篡改要明确失败。`source_ref` 未有可信原始 TeX 对齐时为 null，不能从 HTML 位置伪造。此代码使用 dataclass（并非已生成独立 JSON Schema），因此字段 JSON 表达通过 `to_dict()` 而不是声称完整 Schema 校验通过。

正式说明：[M04 PaperDocument](../07-reproduction/m04-paper-document.md)。

## M05.1 已实现 QualityReport（正式字段）

`src/nano_ar5iv/ports/quality.py` 的 `QualityReport`, `Dimension`, `Finding` 为真实 dataclass，含 `schema_version=1.0`, `policy_version=m05.1`, `document_id`, `derivation_id`, `document_sha256`, `reference_sha256`, `dimensions`, `decision`, `reason_codes`, `provenance`。每个 dimension 独立为 `PASS|FAIL|UNKNOWN|NOT_RUN|NOT_APPLICABLE`，全局 decision 为 `ACCEPTED|PARTIAL|REVIEW_REQUIRED|REJECTED`；没有 PDF_FALLBACK 可运行实现。输出 `quality-reports/.../quality-report.json` 和哈希 manifest，**不改写 M04 PaperDocument 的原始 quality_status=NOT_EVALUATED**。

`ACCEPTED` 仅覆盖用户提供且与 SourceBundle 绑定的黄金断言。人类 reviewer 字段不提供任何真实身份验证。详情：[M05 Quality Gate](../07-reproduction/m05-quality-gate.md)。
