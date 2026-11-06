"""Ingest one trusted local directory into the content-addressed snapshot store."""
from pathlib import Path
from nano_ar5iv.domain.source import SourceBundle
from nano_ar5iv.infrastructure.repositories import SnapshotStore


def ingest_source(source_dir: Path, store: SnapshotStore) -> SourceBundle:
    return store.capture(source_dir)
