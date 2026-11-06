"""Copy-on-write isolated attempt workspaces (M01); repairs reserved for M03."""
from __future__ import annotations
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from nano_ar5iv.domain.source import SourceBundle


@contextmanager
def attempt_workspace(bundle: SourceBundle) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="nano-ar5iv-attempt-") as tmp:
        dest = Path(tmp).resolve() / "input"
        shutil.copytree(bundle.source_root, dest)
        for root, dirs, files in os.walk(dest):
            os.chmod(root, 0o755)
            for name in files:
                os.chmod(Path(root) / name, 0o644)
        yield dest
