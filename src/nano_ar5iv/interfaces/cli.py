"""CLI: M01 immutable snapshots + M02 deterministic entry discovery.

Never silently select a main.tex. Conversion of multiple roots is explicit and
each root produces a separate, evidence-bearing artifact manifest.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.application.discover import discover_entries, probe_candidates
from nano_ar5iv.application.ingest import ingest_source
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore, UnsafeSource
from nano_ar5iv.infrastructure.sandbox import DockerRuntime
from nano_ar5iv.application.recover import recover_existing_root, recover_fragments
from nano_ar5iv.recovery.strategies import RecoveryPolicy
from nano_ar5iv.recovery.wrapper import plan_wrapper
from nano_ar5iv.application.normalize import normalize_run
from nano_ar5iv.application.evaluate import evaluate_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nano-ar5iv",
                                     description="M01-M05: conversion, recovery, paper normalization and evidence-based quality evaluation")
    parser.add_argument("--output", required=True, type=Path,
                        help="snapshot and artifact directory (must be outside input)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    inspect = sub.add_parser("inspect", help="hash and snapshot an explicit source directory")
    inspect.add_argument("source", type=Path)

    discover = sub.add_parser("discover", help="report source roots, dependency evidence, ambiguity")
    discover.add_argument("source", type=Path)
    discover.add_argument("--probe", action="store_true",
                          help="OPT-IN: try up to K candidates with real Docker; requires trusted local TeX")
    discover.add_argument("--top-k", type=int, default=2)
    discover.add_argument("--timeout", type=int, default=120)
    discover.add_argument("--image", default="latexml/ar5ivist:2512.17")

    convert = sub.add_parser("convert", help="baseline conversion, using root discovery if --entry omitted")
    convert.add_argument("source", type=Path)
    convert.add_argument("--entry", help="explicit relative TeX root, overrides discovery")
    convert.add_argument("--all-roots", action="store_true",
                         help="convert each discovered top-level file separately (never merge)")
    convert.add_argument("--image", default="latexml/ar5ivist:2512.17")
    convert.add_argument("--timeout", type=int, default=300)

    recovery = sub.add_parser("recover", help="OPT-IN conservative patch recovery, trusted local TeX only")
    recovery.add_argument("source", type=Path)
    mode = recovery.add_mutually_exclusive_group(required=True)
    mode.add_argument("--entry", help="existing TeX root; one baseline then at most one safe patch")
    mode.add_argument("--fragments", nargs="+", help="explicitly ordered incomplete .tex/.ltx fragments")
    recovery.add_argument("--document-class", default="article", choices=("article", "report", "book"))
    recovery.add_argument("--preamble", help="optional explicit macro fragment used before begin{document}")
    recovery.add_argument("--plan-only", action="store_true",
                          help="only preview an explicit-fragment wrapper; no Docker")
    recovery.add_argument("--max-repairs", type=int, default=1, choices=(0, 1))
    recovery.add_argument("--image", default="latexml/ar5ivist:2512.17")
    recovery.add_argument("--timeout", type=int, default=300)

    normalize = sub.add_parser("normalize", help="derive a versioned PaperDocument from an existing run")
    normalize.add_argument("run_manifest", type=Path)
    normalize.add_argument("--format", choices=("auto", "xml", "html"), default="auto",
                           help="prefer a verified native XML artifact; fall back to HTML")

    evaluate = sub.add_parser("evaluate", help="M05: audit one existing M04 PaperDocument")
    evaluate.add_argument("paper_document", type=Path,
                          help="paper-document.json in the configured normalizations store")
    evaluate.add_argument("--golden", type=Path, default=None,
                          help="OPTIONAL externally reviewed, source-bound JSON assertions")

    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if args.cmd == "evaluate":
            report, path = evaluate_run(args.paper_document, output, args.golden)
            print(json.dumps({
                "status": "ASSESSED", "decision": report.decision,
                "quality_report_path": str(path),
                "document_id": report.document_id,
                "reference_sha256": report.reference_sha256,
                "dimensions": {name: result.status for name, result in report.dimensions.items()},
                "reason_codes": list(report.reason_codes),
            }, ensure_ascii=False, indent=2))
            return {"ACCEPTED": 0, "PARTIAL": 3, "REVIEW_REQUIRED": 3, "REJECTED": 4}[report.decision]
        if args.cmd == "normalize":
            document, path = normalize_run(args.run_manifest, output, args.format)
            print(json.dumps({
                "status": "NORMALIZED", "document_id": document.document_id,
                "document_path": str(path), "source_kind": document.source_kind,
                "schema_version": document.schema_version,
                "quality_status": document.quality_status,
                "counts": {
                    "nodes": len(document.nodes), "equations": len(document.equations),
                    "assets": len(document.assets), "citations": len(document.citations),
                    "unresolved_relations": sum(1 for x in document.relations if x.resolution != "RESOLVED"),
                    "unknown_nodes": len(document.unknown_nodes),
                },
            }, ensure_ascii=False, indent=2))
            return 0
        bundle = ingest_source(args.source, SnapshotStore(output))
        if args.cmd == "inspect":
            print(json.dumps({**bundle.to_dict(), "manifest_path": str(bundle.manifest_path)},
                             ensure_ascii=False, indent=2))
            return 0

        if args.cmd == "discover":
            decision = discover_entries(bundle)
            if args.probe:
                runtime = DockerRuntime(image=args.image)
                decision = probe_candidates(bundle, decision, Ar5ivistEngine(runtime),
                                            ArtifactStore(output), args.top_k, args.timeout)
            print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
            return 0 if decision.status in {"SELECTED", "MULTIPLE_ROOTS"} else 3

        if args.cmd == "recover":
            if args.plan_only:
                if not args.fragments:
                    raise ValueError("--plan-only is supported only with explicitly ordered --fragments")
                plan = plan_wrapper(bundle, tuple(args.fragments), args.document_class, args.preamble)
                print(json.dumps({"status": "PLAN_ONLY", "plan": plan.public_dict(),
                                  "quality_status": "NOT_EVALUATED"},
                                 ensure_ascii=False, indent=2))
                return 0
            engine = Ar5ivistEngine(DockerRuntime(image=args.image))
            store = ArtifactStore(output)
            if args.entry:
                if args.preamble is not None or args.document_class != "article":
                    raise ValueError("Class/preamble options apply only to explicit fragments")
                result = recover_existing_root(bundle, args.entry, engine, store, args.timeout,
                                               RecoveryPolicy(max_repairs=args.max_repairs))
            else:
                if args.max_repairs == 0:
                    raise ValueError("Explicit fragment wrapper requires max-repairs=1")
                result = recover_fragments(bundle, tuple(args.fragments), engine, store,
                                           args.document_class, args.preamble, args.timeout)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0 if result.status in {"BASELINE_SUCCEEDED", "RECOVERED_UNVERIFIED"} else 3

        if args.entry and args.all_roots:
            raise ValueError("Use --entry OR --all-roots, not both")
        decision = None if args.entry else discover_entries(bundle)
        if args.entry:
            roots = (args.entry,)
            provenance = {"schema_version": "1.0", "selection": "explicit", "entry": args.entry}
        elif decision.status == "SELECTED":
            roots = decision.selected_roots
            provenance = decision.to_dict()
        elif decision.status == "MULTIPLE_ROOTS" and args.all_roots:
            roots = decision.selected_roots
            provenance = decision.to_dict()
        else:
            print(json.dumps({
                "status": decision.status,
                "error": "No unique safe root; choose --entry or explicitly --all-roots",
                "entry_decision": decision.to_dict()
            }, ensure_ascii=False, indent=2))
            return 3

        engine = Ar5ivistEngine(DockerRuntime(image=args.image))
        results = []
        for root in roots:
            attempt, path = convert_source(bundle, root, engine, ArtifactStore(output),
                                           args.timeout, selection=provenance)
            results.append({"entry": root, "status": attempt.status,
                            "manifest_path": str(path), "engine_image_id": attempt.image_id,
                            "quality_status": "NOT_EVALUATED"})
        if len(results) == 1:
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"status": "MULTI_ROOT_ATTEMPTS", "results": results,
                              "entry_decision": provenance}, ensure_ascii=False, indent=2))
        return 0 if all(record["status"] == "SUCCEEDED" for record in results) else 2
    except (OSError, ValueError, UnsafeSource) as exc:
        print(f"nano-ar5iv: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
