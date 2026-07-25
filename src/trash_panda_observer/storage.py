"""Event storage primitives."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


class LowStorageError(RuntimeError):
    """Capture is temporarily disabled because free space is below the limit."""


def event_id(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S_") + f"{now.microsecond // 1000:03d}"


def require_free_space(base: Path, minimum_gb: float) -> None:
    probe = base if base.exists() else next(p for p in base.parents if p.exists())
    if shutil.disk_usage(probe).free < int(minimum_gb * 1024**3):
        raise LowStorageError("free storage is below configured minimum")


def create_event_directory(base: Path, now: datetime) -> tuple[str, Path]:
    identifier = event_id(now)
    path = base / "captures" / now.strftime("%Y-%m-%d") / f"event_{identifier}"
    path.mkdir(parents=True, exist_ok=False)
    return identifier, path


def durable_replace(temporary: Path, final: Path) -> None:
    """Commit a completed file and its directory entry to durable storage."""
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, final)
    directory_fd = os.open(final.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n")
        durable_replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
