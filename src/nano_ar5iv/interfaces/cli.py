"""M01 CLI for snapshot inventory and a single ar5ivist baseline conversion."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from nano_ar5iv.application.convert import convert_source
from nano_ar5iv.application.ingest import ingest_source
from nano_ar5iv.adapters.latexml.runner import Ar5ivistEngine
from nano_ar5iv.infrastructure.repositories import ArtifactStore, SnapshotStore, UnsafeSource
from nano_ar5iv.infrastructure.sandbox import DockerRuntime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nano-ar5iv", description="M01: immutable source inventory and Docker baseline conversion")
    parser.add_argument("--output", required=True, type=Path, help="snapshot and run artifact directory outside input")
    sub = parser.add_subparsers(dest="cmd", required=True)
    inspect = sub.add_parser("inspect", help="hash and snapshot an explicit source directory")
    inspect.add_argument("source", type=Path)
    convert = sub.add_parser("convert", help="one baseline conversion; no auto-repair")
    convert.add_argument("source", type=Path)
    convert.add_argument("--entry", required=True, help="explicit relative .tex/.ltx entry; M02 auto-detection not implemented")
    convert.add_argument("--image", default="latexml/ar5ivist:2512.17", help="pre-pulled versioned Docker image")
    convert.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        bundle = ingest_source(args.source, SnapshotStore(output))
        if args.cmd == "inspect":
            print(json.dumps({**bundle.to_dict(), "manifest_path": str(bundle.manifest_path)}, ensure_ascii=False, indent=2))
            return 0
        engine = Ar5ivistEngine(DockerRuntime(image=args.image))
        attempt, manifest_path = convert_source(bundle, args.entry, engine, ArtifactStore(output), args.timeout)
        print(json.dumps({"status": attempt.status, "manifest_path": str(manifest_path),
                          "engine_image_id": attempt.image_id, "quality_status": "NOT_EVALUATED"}, indent=2))
        return 0 if attempt.status == "SUCCEEDED" else 2
    except (OSError, ValueError, UnsafeSource) as exc:
        print(f"nano-ar5iv: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
