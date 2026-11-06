# M01 — Source Snapshot & LaTeXML Baseline (implementation evidence)

> Implemented in branch `feat/m01-source-snapshot-latexml-baseline`. This is the **first functional slice**, not a production converter and not a full ar5iv recreation. M02 entry discovery, M03 repair, M04 IR and M05 scientific quality validation remain unimplemented.

## Implemented scope

- `nano-ar5iv inspect`: ingest an explicit local directory; reject symlinks, special files, private/cache entries and oversized trees; copy to a content-addressed source store; SHA256 each file; verify existing source snapshot hashes.
- `nano-ar5iv convert`: require a **user-specified** relative `.tex/.ltx` entry; convert once through the pre-pulled `latexml/ar5ivist:2512.17` image; stage a separate writable copy; retain HTML, logs, stderr/stdout, exit state, command, inspected image ID and output checksums.
- The Docker command constrains network (`--network=none`), capabilities (`--cap-drop=ALL`), rootfs (`--read-only`), privileges, non-root UID, PID/CPU/RAM/time limits and tmpfs. **Actual Docker security and compatibility have not been verified** in this environment. Never treat these flags alone as production sandbox approval.
- Baseline diagnostic parser extracts Warning/Error/Fatal. A zero exit and HTML present show *process execution*, not scientific fidelity; Error/Fatal forces FAILED. Every run records `quality_status=NOT_EVALUATED`.

## Quick start

Requires Python 3.11+, Docker with a local pre-pulled ar5ivist image for conversion.

~~~bash
python -m pip install -e .
nano-ar5iv --output ./run-data inspect ./examples/trusted-minimal

# Explicitly pull in a trusted local environment. No automatic pulls are performed.
docker pull latexml/ar5ivist:2512.17
nano-ar5iv --output ./run-data convert ./examples/trusted-minimal \
  --entry manuscript.tex --image latexml/ar5ivist:2512.17 --timeout 300
~~~

`run-data` must be **outside** the source folder. If Docker is absent, the conversion produces `ENGINE_UNAVAILABLE` and a failure manifest, not a fake HTML. For source inspection without installation:

~~~bash
PYTHONPATH=src python -m nano_ar5iv --output ./run-data inspect ./examples/trusted-minimal
~~~

**Scope restriction:** Run only locally trusted and authorized TeX. This prototype has not completed a real Docker sandbox audit, has no auth/multitenancy and is not a public arbitrary-TeX processing service.

## Recorded output

~~~text
run-data/
  sources/<source_sha256>/manifest.json
  sources/<source_sha256>/files/...
  runs/<unique_run_id>/manifest.json
  runs/<unique_run_id>/artifacts/html/index.html      # only when produced
  runs/<unique_run_id>/artifacts/logs/*.latexml.log    # when emitted
  runs/<unique_run_id>/artifacts/engine.stdout.txt
  runs/<unique_run_id>/artifacts/engine.stderr.txt
~~~

Manifest includes source bundle hash, file hashes, entry, engine image reference and inspected local image ID, arguments, elapsed seconds, exit code, diagnostics count, artifact sizes/hashes. `run_id` intentionally uses UUID (one record per attempt), rather than pretending to have M06 deterministic caching/checkpointing.

## M01 validation evidence (2026-11-06)

Local Python: 3.13.5. Commands:

~~~bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m nano_ar5iv --output /tmp/nano-m01 inspect examples/trusted-minimal
~~~

Result: **16 unittest cases, 15 pass, 1 skip** (`RUN_REAL_LATEXML` not configured); compileall passes; CLI inspect returns SHA256 bundle; CLI convert without Docker returns `ENGINE_UNAVAILABLE`, nonzero exit, and a run manifest. A fake engine integration test proves orchestration and artifact capture, **not a real LaTeXML conversion**. The optional test `RUN_REAL_LATEXML=1` should run only after the pinned image has been pulled and independently reviewed.

Unverified: real Docker/ar5ivist conversion, real TeX→HTML/MathML, font/package compatibility, production hardening, benchmark throughput and scientific fidelity. All must remain `NOT_RUN` until actual evidence exists.

## Known limitations and exit criteria

1. Only folder input; no .tar/.zip or 00README discovery yet (M02).
2. Caller must provide exact entry; no multi-root handling, no automatic recovery (M02/M03).
3. Any page may look readable while equations/citations are corrupted; all results have `NOT_EVALUATED` until M05.
4. Sandbox options are only planned defenses; test image behavior on Linux/macOS with controlled sample before using untrusted inputs.
5. No PDF fallback, IR normalization, RAG, UI, job queue, durable replay or multi-tenant API.

Next gate: verify one *real* Docker run with recorded image digest, XML/HTML/logs and source hashes; then implement M02 metadata-first entry discovery with actual fixtures.

Related: [Reproduction blueprint](../04-architecture/reproduction-blueprint.md) · [Security](../05-quality/security.md) · [Experiment matrix](experiment-matrix.md).


## Verified real CI run: 2026-11-06

- [Workflow run #42189149532](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42189149532): all three jobs passed — Python 3.11 and 3.13 unit matrix, real ar5ivist smoke conversion **and** the full `nano-ar5iv convert` CLI.
- The CLI read back its JSON manifest, required status `SUCCEEDED` and quality status `NOT_EVALUATED`, verified explicit entry `manuscript.tex`, inspected the Docker image ID and exit=0, confirmed `html/index.html` exists, and recalculated SHA256 for **all 4 produced artifacts**.
- Captured source bundle SHA256: `03bcf80d0c08bcf50605cfa681aedceccbd660b26dee6dee99171ff9fde0eb10`.
- Inspected local image ID: `sha256:c221bea1ad4852946acf50d59cb6a5550c54c550e047cf48df872f7ef3f70638`. Image registry pull manifest digest: `sha256:9a8d577d6df6cdf088f1764c38bddab54d7c21c857fef68ae46ea3ff9676d70e`; **these identifiers are different types and must not be conflated**.
- Root-cause debugging: initial Docker smoke failed with exit code **125**, as `--mount type=bind,src=...,dst=/docdir,rw` is invalid; Docker `--mount` bind is writable by default. The exact error was captured in [failed run #42188492703](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42188492703). Removing `,rw` and adding an assertion in `tests/test_docker_runtime.py` fixed it. Official reference: https://docs.docker.com/engine/storage/bind-mounts/ .
- This proves the M01 **single trusted sample** end-to-end baseline, not author-provided arXiv corpus support, MathML/citation correctness at scale, or production sandbox security.
