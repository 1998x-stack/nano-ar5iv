# M05.1｜Evidence-first Scientific Quality Gate（证据优先的科学质量门禁）

> Status: **implemented in PR #11**. This is the first functional M05 slice, not a peer-reviewed, paper-wide scientific truth checker. M05.1 does not support visual PDF overlays, original PDF comparison, or production-calibrated false-acceptance estimates. No output is scientifically certified beyond the explicit checks performed.

## 1. Core principle

A LaTeXML process with exit code 0, generated HTML, MathML elements and nonbroken citations can still omit or corrupt scientific content. **A successful M04 normalization cannot automatically become an accepted paper**. We require **source-bound, independently prepared golden assertions supplied by the caller** and separately report structural, mathematical, bibliography, asset, visual and provenance evidence.

The golden reference must be prepared from original author source and/or independently reviewed materials, **not copied from the candidate converted output**. The software validates its shape, SHA256 source-bundle binding and asserted content. It **does not cryptographically authenticate the reviewer identity or verify that the reference was independently prepared**. Accordingly, `ACCEPTED` means only "all checked assertions from a supplied golden passed under M05.1 policy", not a universal scientific correctness certificate.

## 2. CLI commands

Install Python 3.11+, and first obtain a real M01–M03 run and M04 normalized document (the initial conversion uses pre-pulled Docker ar5ivist; `normalize` and `evaluate` do not require Docker):

~~~bash
python -m pip install -e .
nano-ar5iv --output ./run-data convert ./examples/trusted-minimal \
  --entry manuscript.tex > ./convert-result.json

nano-ar5iv --output ./run-data normalize \
  ./run-data/runs/<run_id>/manifest.json

# Default, with NO external golden: evaluate and explicitly abstain from certification.
nano-ar5iv --output ./run-data evaluate \
  ./run-data/normalizations/<run_id>/<derivation_id>/paper-document.json

# Explicit source-bound, manually reviewed golden JSON:
nano-ar5iv --output ./run-data evaluate \
  ./run-data/normalizations/<run_id>/<derivation_id>/paper-document.json \
  --golden ./my-independent-golden.json
~~~

The default no-golden evaluation returns `REVIEW_REQUIRED` unless a clear hard failure requires `REJECTED`. Exit codes: `0=ACCEPTED` (only when all hard gates pass against provided golden), `3=PARTIAL/REVIEW_REQUIRED`, `4=REJECTED`, `2=invalid source/evidence/CLI input`.

For real ar5ivist HTML, automatic `ACCEPTED` is **blocked even when an external golden is provided**, because M04 HTML reconstruction does not preserve the full original XML and TeX source. Native XML can be assessed if it is actually present as a SHA256-recorded artifact within the M01–M03 run. We do not invent an XML artifact.

## 3. QualityReport v1.0 / Gate policy m05.1

Separate dimensions and statuses:

| Dimension | Actual checks | When uncertain or not run |
|---|---|---|
| `structure` | Duplicate IDs, orphan/cyclic hierarchy, child-parent edges, meaningful IR, golden section titles and paragraph passages | No golden: `UNKNOWN` |
| `mathematics` | Formula count, source TeX exact comparison when available, parsed MathML token sequence comparison, unusable/absent MathML | No golden: `UNKNOWN`; different symbols: `FAIL` |
| `bibliography` | Relation closure, existing target IDs, expected citation kind/target and bibliography ID/text | No golden: `UNKNOWN`; dangling targets: `FAIL` |
| `assets` | Figure URI safety, SHA256-verified saved figure artifacts, number of figures/tables, table cell text + rowspan/colspan | Missing comparison evidence: `UNKNOWN`; mismatch: `FAIL` |
| `visual` | **No actual screenshot/PDF rendering test implemented** | `NOT_RUN` unless explicitly declared N/A and no image/table exists |
| `provenance` | Conversion status, native XML vs lossy HTML, unknown scientific structures, normalizer warnings, gold-to-bundle identity | HTML or unknown nodes: `UNKNOWN`, source mismatch: `FAIL` |

Dimensions have `status=PASS|FAIL|UNKNOWN|NOT_RUN|NOT_APPLICABLE` plus reason-coded findings and checked counts. Report decisions are `ACCEPTED|PARTIAL|REVIEW_REQUIRED|REJECTED`.

The aggregator is deliberately **not a weighted average**. Any `FAIL` yields `REJECTED`. `ACCEPTED` requires an explicit source-bound golden, every applicable dimension `PASS`, and only a grounded visual `NOT_APPLICABLE` exception. `NOT_RUN` blocks acceptance. `PARTIAL` means some golden-supported checks passed, but unknowns remain and no check outright failed; it is **not** an alias for accepted.

## 4. Manually authored golden reference schema

The following is a **shape example**, not an assertion that a specific real paper passed. Replace source bundle ID with the actual 64-character hash from `inspect` / M01 run, and ground each golden expectation in independently inspected original source:

~~~json
{
  "schema_version": "1.0",
  "source_bundle_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "root_path": "paper.tex",
  "review": {
    "reviewer": "fixture-reviewer-or-external-review-id",
    "evidence_method": "manual review of original TeX and expected formula tokens"
  },
  "expected": {
    "sections": ["Introduction"],
    "paragraphs_contain": ["Independent test text"],
    "equations": [
      {"tex": "a+b", "mathml_tokens": ["a", "+", "b"]}
    ],
    "citations": [],
    "bibliography": [],
    "figures": [],
    "tables": [],
    "visual": "NOT_APPLICABLE"
  }
}
~~~

Every `expected` key is mandatory, including intentionally empty arrays. Citation expectation objects are `{"kind":"citation|reference", "target":"bib1"}`. Bibliography items are `{"source_id":"bib1", "text":"..."}`. Figure objects are `{"href":"images/x.png", "sha256":"<64 hex>"}`; the run must retain a matching, SHA256-checked local asset. Tables use `{"rows":[[{"text":"7","colspan":1,"rowspan":1}]]}`. TeX can be absent in HTML; if a golden requires exact TeX but the conversion did not preserve it, mathematics stays `UNKNOWN`, not falsely PASS.

`visual=NOT_APPLICABLE` is only permitted when the normalized document contains no figures, images or tables. Otherwise `visual=REQUIRED` honestly produces `NOT_RUN` until actual rendered comparison is implemented. Golden identity fields are unverified human claims; follow real provenance review procedures independently.

## 5. Immutable evidence and hashing

~~~text
run-data/
  sources/<bundle_sha256>/manifest.json
  sources/<bundle_sha256>/files/...
  runs/<run_id>/manifest.json
  runs/<run_id>/artifacts/...
  normalizations/<run_id>/<derivation_id>/
    paper-document.json
    normalization-manifest.json
  quality-reports/<run_id>/<derivation_id>/<report_id>/
    quality-report.json
    quality-manifest.json
~~~

M05 verifies the source snapshot file SHA256 and bundle fingerprint; original conversion manifest, artifact hashes/sizes; canonical normalization derivation ID and paper-document checksum; source-bundle/run/root identity; optional golden source binding. Quality runs are deterministic for the same document digest, golden digest and policy. Repeating identical inputs returns the same immutable quality report; tampering must cause a hard error rather than overwriting.

**Important:** locally stored hashes protect consistency but are not cryptographic signatures or a remote trusted timestamp. An attacker controlling all evidence files could modify content and recompute hash metadata; trustworthy independent golden provenance and secure storage remain requirements.

## 6. Regression matrix / no false claims

- Synthetic golden fixture can reach `ACCEPTED` under a controlled *native XML* fixture after explicit math tokens, TeX and structural expectations match.
- With no golden, successful converter output must remain `REVIEW_REQUIRED`.
- Mutation of an expected math symbol (with engine status still SUCCEEDED), missing MathML or formula count mismatch → `REJECTED`.
- Dangling cross-reference, wrong citation/bibliography target, altered table cell/span or unsafe figure URI → `REJECTED`.
- HTML fallback, unrecognized theorem/proof/other semantics, absent source TeX for expected comparison, non-run visual check → never `ACCEPTED`.
- Original source bundle, artifact, derivation or prior quality report tampering → explicit error.
- Real Docker smoke: trusted authored LaTeX → ar5ivist HTML → PaperDocument → M05 quality report, **must abstain without golden**; M01–M04 regressions must pass.

Unit/golden fixtures can verify implementation mechanics but cannot establish real-world false acceptance / false rejection rates. M05.2 should implement independent PDF-source alignment and browser visual comparison, then measure actual thresholds on licensed real arXiv papers (with splits by mathematics, packages, references, figures and error types). **No accuracy percentage or production SLA is asserted here.**

## 7. Later work

M05.2: rendered PDF comparison, math-structure alignment rather than basic token sequences, source-to-output coverage, complex crossreferences/figure detection. M05.3: independent human-labeled golden set; report recall, precision, false-acceptance/false-rejection and abstention rates. Only then consider using `ACCEPTED` for broader product workflows.
