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


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temporary, path)
