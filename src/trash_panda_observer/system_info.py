"""Read-only host and storage summaries."""

import os
import platform
import shutil
import subprocess
from importlib import metadata
from pathlib import Path


def system_summary() -> dict:
    model_path = Path("/proc/device-tree/model")
    model = model_path.read_text().rstrip("\0") if model_path.exists() else "unknown"
    os_release = {}
    release_path = Path("/etc/os-release")
    if release_path.exists():
        for line in release_path.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip('"')
    packages = {}
    for name in ("picamera2", "numpy", "PyYAML", "psutil"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "hostname": platform.node(),
        "model": model,
        "os": os_release.get("PRETTY_NAME", platform.platform()),
        "os_codename": os_release.get("VERSION_CODENAME"),
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "packages": packages,
    }


def storage_summary(path: Path) -> dict:
    probe = path if path.exists() else next(p for p in path.parents if p.exists())
    usage = shutil.disk_usage(probe)
    capture_path = path / "captures"
    capture_bytes = sum(
        item.stat().st_size for item in capture_path.rglob("*") if item.is_file()
    ) if capture_path.exists() else 0
    return {"path": os.fspath(path), "total": usage.total,
            "used": usage.used, "free": usage.free,
            "capture_bytes": capture_bytes}


def git_revision(project_path: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(project_path), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True, timeout=2,
        ).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
