# 10｜数据契约与事件设计（Proposal v0.1）

本页为未来 JSON Schema / Pydantic / dataclass 的**语义约定**。以下 JSON 示例合法，但**尚未实现、未执行 Schema 校验**。

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
