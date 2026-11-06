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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nano-ar5iv",
                                     description="M02: inspect source, discover TeX roots, convert trusted sources")
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
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
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
