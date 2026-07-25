"""Read-only host and storage summaries."""

import os
import platform
import shutil
from pathlib import Path


def system_summary() -> dict:
    model_path = Path("/proc/device-tree/model")
    model = model_path.read_text().rstrip("\0") if model_path.exists() else "unknown"
    return {
        "hostname": platform.node(),
        "model": model,
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "python": platform.python_version(),
    }


def storage_summary(path: Path) -> dict:
    probe = path if path.exists() else next(p for p in path.parents if p.exists())
    usage = shutil.disk_usage(probe)
    return {"path": os.fspath(path), "total": usage.total,
            "used": usage.used, "free": usage.free}
