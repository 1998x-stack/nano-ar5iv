"""Docker isolation boundary for M01 trusted/local LaTeXML baseline.

Requires a pre-pulled pinned Docker image. No arbitrary host TeX execution.
This defense-in-depth configuration needs real Docker validation before describing
it as production secure. Do not mount credential-bearing source trees.
"""
from __future__ import annotations
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*:(?!latest$)[A-Za-z0-9._-]+$|^[A-Za-z0-9][A-Za-z0-9._/-]*@sha256:[0-9a-f]{64}$")


class DockerUnavailable(RuntimeError):
    """Docker binary/image is missing or inaccessible."""


@dataclass(frozen=True)
class RuntimeResult:
    image_id: str
    exit_code: int | None
    elapsed_seconds: float
    timed_out: bool
    stdout: str
    stderr: str
    command: tuple[str, ...]


class DockerRuntime:
    def __init__(self, image: str = "latexml/ar5ivist:2512.17", docker_binary: str = "docker",
                 memory: str = "2g", cpus: str = "2", pids: int = 128) -> None:
        if not _IMAGE.fullmatch(image):
            raise ValueError("Use a non-latest version tag or sha256-pinned image")
        if pids < 1 or not re.fullmatch(r"[0-9]+[kmg]", memory) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cpus):
            raise ValueError("Invalid sandbox resource limits")
        self.image = image
        self.docker_binary = docker_binary
        self.memory = memory
        self.cpus = cpus
        self.pids = pids

    @staticmethod
    def _env() -> dict[str, str]:
        # Avoid accidental remote Docker contexts and remote daemon execution.
        return {k: v for k, v in os.environ.items() if not k.startswith("DOCKER_")}

    def image_id(self) -> str:
        try:
            result = subprocess.run([self.docker_binary, "image", "inspect", "--format", "{{.Id}}", self.image],
                                    capture_output=True, text=True, errors="replace", timeout=15, env=self._env(), check=False)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
            raise DockerUnavailable("Docker executable/daemon unavailable") from exc
        image_id = result.stdout.strip()
        if result.returncode != 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise DockerUnavailable("Pinned image not available locally; pull explicitly in a trusted environment")
        return image_id

    def build_command(self, workdir: Path, entry: str, container_name: str) -> list[str]:
        if not workdir.is_dir() or not workdir.is_absolute():
            raise ValueError("Isolated workspace must be an absolute directory")
        if not re.fullmatch(r"nano-ar5iv-[0-9a-f]{32}", container_name):
            raise ValueError("Invalid container name")
        # Bind mounts are writable by default; Docker --mount rejects bare ,rw.
        return [
            self.docker_binary, "run", "--rm", "--pull=never", "--name", container_name,
            "--network=none", "--security-opt=no-new-privileges", "--cap-drop=ALL",
            "--read-only", "--pids-limit", str(self.pids), "--memory", self.memory,
            "--cpus", self.cpus,
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--mount", f"type=bind,src={workdir},dst=/docdir", "--workdir", "/docdir",
            self.image, f"--source={entry}", "--destination=html/index.html"
        ]

    def execute(self, workdir: Path, entry: str, timeout_seconds: int) -> RuntimeResult:
        if timeout_seconds < 1 or timeout_seconds > 2700:
            raise ValueError("timeout_seconds must be in 1..2700")
        image_id = self.image_id()
        name = "nano-ar5iv-" + uuid.uuid4().hex
        command = self.build_command(workdir, entry, name)
        started = time.monotonic()
        try:
            result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                    timeout=timeout_seconds, env=self._env(), check=False)
            return RuntimeResult(image_id, result.returncode, time.monotonic()-started, False,
                                 result.stdout[:2_000_000], result.stderr[:2_000_000], tuple(command))
        except subprocess.TimeoutExpired as exc:
            # Killing Docker CLI alone does not guarantee container termination.
            try:
                subprocess.run([self.docker_binary, "rm", "-f", name], capture_output=True,
                               timeout=15, env=self._env(), check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            return RuntimeResult(image_id, None, time.monotonic()-started, True,
                                 stdout[:2_000_000], stderr[:2_000_000], tuple(command))
        except (FileNotFoundError, OSError) as exc:
            raise DockerUnavailable("Cannot invoke local Docker CLI") from exc
