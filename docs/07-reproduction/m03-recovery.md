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

The 23 additional tests check error evidence, source immutability, plan determinism and tamper detection, bounded attempts, and CLI behavior. Fake-engine tests do not establish real conversion. The separately configured real Docker smoke test PASSED, as shown in the evidence below.


## Verified CI evidence (2026-11-06)

- [GitHub Actions run #42192898339](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42192898339): 3 of 3 jobs succeeded for source commit 4ceb986d85d899537633120e729afeab1accf953.
- Python 3.11: 64 unittest cases, 63 passed, 1 intentional skip (the real Docker test is executed in another job).
- Python 3.13: 64 unittest cases, 63 passed, 1 intentional skip.
- Real Docker job: successful M01 LaTeXML minimal sample, successful M02 discover/probe sample and successful M03 recover-wrapper explicit fragment sample. Pinned upstream image tag latexml/ar5ivist:2512.17, pulled registry digest sha256:9a8d577d6df6cdf088f1764c38bddab54d7c21c857fef68ae46ea3ff9676d70e.
- Real M03 smoke log marker: M03_REAL_WRAPPER_PASS fd6cd5e0e922ebdb671acb3d57ed704534dae2fd9c941c59d09261caa3a62911 b910e1110611b7c499b1f79b625fe292e1cd91d2cc6ed0c7af4e5decd4a64547.
- Assertion verifies original_files_unchanged=True, original and derived snapshot IDs differ, conversion manifest entry is __nano_ar5iv_wrapper.tex, single engine attempt succeeds, final status remains REVIEW_REQUIRED and quality_status NOT_EVALUATED.
- This is a self-authored, trusted minimal fragment only. Independent scientific fidelity, math/references preservation, complex manuscript recovery and production sandbox audit were NOT_RUN.

Remaining M03: autonomous fragment ordering, path/package/Bib/asset recovery, bounded multi-strategy retry scheduling, large real-paper evaluation and model-generated patch audit are NOT_IMPLEMENTED. M04/M05 scientific fidelity remains unvalidated.

References: recovery playbook (docs/02-source-recovery/recovery-playbook.md), M03 slices (docs/07-reproduction/implementation-slices.md), GitHub CI workflow.
