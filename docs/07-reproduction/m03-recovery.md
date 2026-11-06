# M03 first engineering slice — diagnostic triage and manual fragment wrapper

This release intentionally implements NO autonomous LaTeX source editing. It is a narrow, auditable, user-directed recovery route for trusted fragment-only TeX inputs. M01/M02 PRs remain upstream dependencies.

## M03.1: evidence-first failure triage

Command:

    PYTHONPATH=src python -m nano_ar5iv --output ./runs diagnose ./attempt.latexml.log --status FAILED --exit-code 1

The recovery/classifier.py heuristic reports the first observed ERROR/FATAL as evidence, counts later errors as possible cascade, and labels DEPENDENCY_MISSING, UNKNOWN_MACRO, MATH_PARSE, ASSET_MISSING, BIB_MISSING, TIMEOUT, ENGINE_UNAVAILABLE, OUTPUT_MISSING and PROCESS_FAILED. It records root_cause_proven=false even when a message suggests a cause. It never installs TeX packages or suppresses macros.

## M03.2: explicit wrapper for fragment-only sources

Suppose a paper has chapters/introduction.tex and chapters/results.tex but no top-level document:

    PYTHONPATH=src python -m nano_ar5iv --output ./runs recover-wrapper ./paper \
      --fragment chapters/introduction.tex --fragment chapters/results.tex --documentclass article

That creates deterministic plan.json WITHOUT executing a converter; the operator explicitly chooses class and fragment order.

Trusted local material may be converted in one bounded attempt:

    PYTHONPATH=src python -m nano_ar5iv --output ./runs recover-wrapper ./paper \
      --fragment chapters/introduction.tex --fragment chapters/results.tex \
      --documentclass article --execute --timeout 180

The generated __nano_ar5iv_wrapper.tex is added to a distinct, hash-addressed derived source bundle through a temporary copy. Original snapshot files remain unchanged. The derived bundle must contain exactly the original hashed files plus the generated wrapper, whose SHA256 equals the plan.

Output: recoveries/<plan_id>/plan.json, attempt-<uuid>.json, and a conversion attempt manifest. Engine success retains status=REVIEW_REQUIRED and quality_status=NOT_EVALUATED pending scientific fidelity verification.

### Hard policy

- Only explicitly selected article, report, book, amsart; no class guessing or TeX package installation.
- 1–10 unique, explicitly ordered .tex/.ltx fragments with restricted ASCII safe relative paths.
- Refuse fragments with documentclass, document boundaries, plain TeX bye, or unresolved dynamic input at the static scanning level.
- Reserved wrapper path, unexpected derived file changes and tampered plan hashes are rejected.
- One engine attempt maximum per requested wrapper execution. No autonomous retry loop.
- No LLM patch, unknown macro suppression, mathematical edits, bibliography invention or author-source overwriting.
- Not a complete TeX parser. Macro/catcode complexity and content quality require review. The M01 Docker runtime is not approved for arbitrary public TeX workloads.

## Verification

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_recovery_classifier.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -p 'test_recover_wrapper.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -v
    PYTHONPATH=src python -m compileall -q src tests

The 23 additional tests check error evidence, source immutability, plan determinism and tamper detection, bounded attempts, and CLI behavior. Fake engine tests do NOT establish real conversion. A separate real Docker self-authored fragment smoke is included in CI; verify its status before reporting it as passed.

Remaining M03: autonomous fragment ordering, path/package/Bib/asset recovery, bounded multi-strategy retry scheduling, large real-paper evaluation and model-generated patch audit are NOT_IMPLEMENTED. M04/M05 scientific fidelity remains unvalidated.

References: recovery playbook (docs/02-source-recovery/recovery-playbook.md), M03 slices (docs/07-reproduction/implementation-slices.md), GitHub CI workflow.
