"""LaTeXML/ar5ivist one-shot Docker adapter; no automatic recovery (M01)."""
from __future__ import annotations
from pathlib import Path
from nano_ar5iv.adapters.latexml.diagnostics import parse_diagnostics
from nano_ar5iv.domain.states import AttemptStatus
from nano_ar5iv.infrastructure.sandbox import DockerRuntime, DockerUnavailable
from nano_ar5iv.ports.engines import EngineAttempt


class Ar5ivistEngine:
    def __init__(self, runtime: DockerRuntime) -> None:
        self.runtime = runtime

    def convert(self, workspace: Path, entry: str, timeout_seconds: int = 300) -> EngineAttempt:
        if (workspace / "html").exists():
            raise ValueError("Reserved html output path already exists in source bundle")
        (workspace / "html").mkdir(parents=True, exist_ok=False)
        try:
            result = self.runtime.execute(workspace, entry, timeout_seconds)
        except DockerUnavailable as exc:
            (workspace / "engine.stderr.txt").write_text(str(exc), encoding="utf-8")
            return EngineAttempt(AttemptStatus.ENGINE_UNAVAILABLE.value, self.runtime.image, None,
                                 entry, None, 0., False, (), 0, None, str(exc))
        (workspace / "engine.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (workspace / "engine.stderr.txt").write_text(result.stderr, encoding="utf-8")
        logfile = workspace / Path(entry).with_suffix(".latexml.log")
        log_text = logfile.read_text(encoding="utf-8", errors="replace") if logfile.is_file() and not logfile.is_symlink() else ""
        diagnostics = parse_diagnostics(log_text + "\n" + result.stderr)
        output = workspace / "html" / "index.html"
        if result.timed_out:
            status = AttemptStatus.TIMED_OUT
        elif result.exit_code != 0 or any(d.severity in {"ERROR", "FATAL"} for d in diagnostics):
            status = AttemptStatus.FAILED
        elif not output.is_file() or output.stat().st_size == 0:
            status = AttemptStatus.OUTPUT_MISSING
        else:
            status = AttemptStatus.SUCCEEDED
        return EngineAttempt(status.value, self.runtime.image, result.image_id, entry,
                             result.exit_code, round(result.elapsed_seconds, 3), result.timed_out,
                             result.command, len(diagnostics), "html/index.html" if output.is_file() else None)
