"""High-resolution event burst capture."""

import os
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path

from .storage import atomic_json, create_event_directory, require_free_space


def capture_burst(
    camera, config: dict, *, warmup_seconds: float = 2, manage_camera: bool = True
) -> Path:
    capture, storage = config["capture"], config["storage"]
    base = Path(storage["base_path"])
    require_free_space(base, storage["minimum_free_space_gb"])
    now = datetime.now().astimezone()
    identifier, event_dir = create_event_directory(base, now)
    free_before = shutil.disk_usage(base).free
    camera_cfg = config["camera"]
    metadata = {
        "schema_version": 1,
        "event_id": identifier,
        "status": "incomplete",
        "trigger_timestamp": now.isoformat(timespec="milliseconds"),
        "capture_start_timestamp": datetime.now().astimezone().isoformat(
            timespec="milliseconds"),
        "hostname": platform.node(),
        "platform": {
            "model": Path("/proc/device-tree/model").read_text().rstrip("\0")
            if Path("/proc/device-tree/model").exists() else "unknown",
            "os": platform.platform(),
            "architecture": platform.machine(),
        },
        "camera": {
            "capture_width": camera_cfg["capture_width"],
            "capture_height": camera_cfg["capture_height"],
            "analysis_width": camera_cfg["analysis_width"],
            "analysis_height": camera_cfg["analysis_height"],
            "jpeg_quality": capture["jpeg_quality"],
            "autofocus_mode": camera_cfg["autofocus_mode"],
        },
        "motion": {
            "pixel_threshold": config["motion"]["pixel_threshold"],
            "minimum_total_area": config["motion"]["minimum_total_area"],
            "minimum_largest_region_area":
                config["motion"]["minimum_largest_region_area"],
            "consecutive_frames": config["motion"]["consecutive_frames"],
            "cooldown_seconds": config["motion"]["cooldown_seconds"],
        },
        "storage": {"free_bytes_before": free_before},
        "software": {"name": "Trash Panda Observer", "version": "0.1.0"},
        "environment": {
            "lighting_mode": config.get("environment", {}).get(
                "lighting_mode", "unknown")
        },
        "capture": {"frames_requested": capture["frames_per_event"],
                    "frames_saved": 0, "interval_ms": capture["interval_ms"]},
        "frames": [], "errors": [],
    }
    if manage_camera:
        camera.start()
    try:
        time.sleep(warmup_seconds)
        for index in range(capture["frames_per_event"]):
            tick = time.monotonic()
            final = event_dir / f"frame_{index:03d}.jpg"
            temporary = event_dir / f".{final.name}.tmp"
            try:
                request = camera.capture_request()
                try:
                    image = request.make_image("main")
                    frame_metadata = request.get_metadata()
                    image.save(
                        temporary, format="JPEG", quality=capture["jpeg_quality"])
                finally:
                    request.release()
                os.replace(temporary, final)
                metadata["capture"]["frames_saved"] += 1
                success = True
                error = None
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                frame_metadata = {}
                success = False
                error = f"{type(exc).__name__}: {exc}"
                metadata["errors"].append(
                    {"frame": index, "error": error})
            metadata["frames"].append({
                "filename": final.name,
                "timestamp": datetime.now().astimezone().isoformat(
                    timespec="milliseconds"),
                "metadata": {k: v for k, v in frame_metadata.items()
                             if isinstance(v, (str, int, float, bool))},
                "write_success": success,
                "error": error,
            })
            time.sleep(max(0, capture["interval_ms"] / 1000 -
                           (time.monotonic() - tick)))
        if metadata["capture"]["frames_saved"] == capture["frames_per_event"]:
            metadata["status"] = "complete"
    except Exception as exc:
        metadata["errors"].append(str(exc))
        raise
    finally:
        if manage_camera:
            camera.stop()
        metadata["capture_end_timestamp"] = datetime.now().astimezone().isoformat(
            timespec="milliseconds")
        metadata["storage"]["free_bytes_after"] = shutil.disk_usage(base).free
        atomic_json(event_dir / "event.json", metadata)
    return event_dir
