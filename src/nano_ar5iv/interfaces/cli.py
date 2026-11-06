"""M01 CLI for snapshot inventory and a single ar5ivist baseline conversion."""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from nano_ar5iv.application.discover import discover_entries
from nano_ar5iv.application.probe import probe_candidates
from nano_ar5iv.application.recover import save_plan, execute_wrapper
from nano_ar5iv.recovery.planner import create_wrapper_plan
from nano_ar5iv.recovery.classifier import classify_failure
from nano_ar5iv.source.archive import extract_archive
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.application.ingest import ingest_source
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore, UnsafeSource
from nano_ar5iv.infrastructure.sandbox import DockerRuntime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nano-ar5iv", description="M03: auditable snapshots, discovery and explicit conservative recovery")
    parser.add_argument("--output", required=True, type=Path, help="snapshot and run artifact directory outside input")
    sub = parser.add_subparsers(dest="cmd", required=True)
    diagnose = sub.add_parser("diagnose", help="heuristic log root-cause triage, no patch")
    diagnose.add_argument("logfile", type=Path)
    diagnose.add_argument("--status", default="FAILED")
    diagnose.add_argument("--exit-code", type=int)
    diagnose.add_argument("--timed-out", action="store_true")
    recover = sub.add_parser("recover-wrapper", help="explicit synthetic wrapper; preview unless --execute")
    recover.add_argument("source", type=Path)
    recover.add_argument("--fragment", action="append", required=True, dest="fragments")
    recover.add_argument("--documentclass", required=True)
    recover.add_argument("--execute", action="store_true", help="one trusted Docker attempt, remains review-required")
    recover.add_argument("--image", default="latexml/ar5ivist:2512.17")
    recover.add_argument("--timeout", type=int, default=180)
    inspect = sub.add_parser("inspect", help="hash and snapshot a directory or ZIP/TAR archive")
    inspect.add_argument("source", type=Path)
    discover = sub.add_parser("discover", help="metadata-first entry discovery (no conversion)")
    discover.add_argument("source", type=Path)
    probe = sub.add_parser("probe", help="explicit bounded candidate trial; trusted source only")
    probe.add_argument("source", type=Path)
    probe.add_argument("--top-k", type=int, default=3)
    probe.add_argument("--timeout", type=int, default=90)
    probe.add_argument("--image", default="latexml/ar5ivist:2512.17")
    convert = sub.add_parser("convert", help="one baseline conversion; optional safe auto-entry")
    convert.add_argument("source", type=Path)
    convert.add_argument("--entry", help="explicit .tex/.ltx entry; otherwise requires one unambiguous discovered root")
    convert.add_argument("--image", default="latexml/ar5ivist:2512.17", help="pre-pulled versioned Docker image")
    convert.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if args.cmd == "diagnose":
            if args.logfile.is_symlink() or not args.logfile.is_file() or args.logfile.stat().st_size > 2_000_000:
                raise ValueError("Expected a regular log file at most 2 MiB")
            log = args.logfile.read_text(encoding="utf-8", errors="replace")
            print(json.dumps(classify_failure(log, status=args.status, exit_code=args.exit_code,
                                              timed_out=args.timed_out), ensure_ascii=False, indent=2))
            return 0
        with tempfile.TemporaryDirectory(prefix="nano-ar5iv-archive-") as staging:
            input_path = args.source
            if input_path.is_file():
                extracted = Path(staging) / "extracted"
                extracted.mkdir()
                extract_archive(input_path, extracted)
                input_path = extracted
            bundle = ingest_source(input_path, SnapshotStore(output))
        if args.cmd == "recover-wrapper":
            plan = create_wrapper_plan(bundle, tuple(args.fragments), args.documentclass)
            plan_path = save_plan(plan, output)
            if not args.execute:
                print(json.dumps({"status": "PLANNED_REVIEW_REQUIRED", "plan_path": str(plan_path),
                                  "plan": plan.to_dict(), "quality_status": "NOT_EVALUATED"},
                                 ensure_ascii=False, indent=2))
                return 0
            engine = Ar5ivistEngine(DockerRuntime(image=args.image))
            report, report_path = execute_wrapper(bundle, plan, engine, output, args.timeout)
            print(json.dumps({"report_path": str(report_path), **report}, ensure_ascii=False, indent=2))
            return 0 if report["engine_status"] == "SUCCEEDED" else 2
        if args.cmd == "inspect":
            print(json.dumps({**bundle.to_dict(), "manifest_path": str(bundle.manifest_path)}, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "discover":
            decision = discover_entries(bundle)
            location = output / "discoveries" / bundle.bundle_id
            location.mkdir(parents=True, exist_ok=True)
            result_path = location / "entry-decision.json"
            tmp_path = location / ("entry-decision." + str(os.getpid()) + ".tmp")
            try:
                tmp_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                os.replace(tmp_path, result_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            print(json.dumps({"status": decision["decision"]["status"], "manifest_path": str(result_path),
                              "selected_roots": decision["decision"]["selected_roots"],
                              "diagnostics": decision["decision"]["diagnostics"]}, ensure_ascii=False, indent=2))
            return 0 if decision["decision"]["status"] in {"SELECTED", "MULTIPLE_ROOTS", "PDF_ONLY"} else 2
        if args.cmd == "probe":
            findings = probe_candidates(bundle, Ar5ivistEngine(DockerRuntime(image=args.image)),
                                        ArtifactStore(output), args.top_k, args.timeout)
            directory = output / "probes" / bundle.bundle_id
            directory.mkdir(parents=True, exist_ok=True)
            summary = directory / "probe-summary.json"
            summary.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"summary_path": str(summary), **findings}, ensure_ascii=False, indent=2))
            return 0 if findings["attempts"] and all(
                a["status"] == "SUCCEEDED" for a in findings["attempts"]) else 2
        entry = args.entry
        if entry is None:
            decision = discover_entries(bundle)["decision"]
            if decision["status"] != "SELECTED" or len(decision["selected_roots"]) != 1:
                print("nano-ar5iv: automatic entry requires one unambiguous root; "
                      + json.dumps(decision, ensure_ascii=False), file=sys.stderr)
                return 2
            entry = decision["selected_roots"][0]
        engine = Ar5ivistEngine(DockerRuntime(image=args.image))
        attempt, manifest_path = convert_source(bundle, entry, engine, ArtifactStore(output), args.timeout)
        print(json.dumps({"status": attempt.status, "manifest_path": str(manifest_path),
                          "engine_image_id": attempt.image_id, "quality_status": "NOT_EVALUATED"}, indent=2))
        return 0 if attempt.status == "SUCCEEDED" else 2
    except (OSError, ValueError, UnsafeSource) as exc:
        print(f"nano-ar5iv: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
