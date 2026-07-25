"""High-resolution event burst capture."""

import os
import time
from datetime import datetime
from pathlib import Path

from .storage import atomic_json, create_event_directory, require_free_space


def capture_burst(camera, config: dict, *, warmup_seconds: float = 2) -> Path:
    capture, storage = config["capture"], config["storage"]
    base = Path(storage["base_path"])
    require_free_space(base, storage["minimum_free_space_gb"])
    now = datetime.now().astimezone()
    identifier, event_dir = create_event_directory(base, now)
    metadata = {
        "schema_version": 1,
        "event_id": identifier,
        "status": "incomplete",
        "trigger_timestamp": now.isoformat(timespec="milliseconds"),
        "capture": {"frames_requested": capture["frames_per_event"],
                    "frames_saved": 0, "interval_ms": capture["interval_ms"]},
        "frames": [], "errors": [],
    }
    camera.start()
    try:
        time.sleep(warmup_seconds)
        for index in range(capture["frames_per_event"]):
            tick = time.monotonic()
            final = event_dir / f"frame_{index:03d}.jpg"
            temporary = event_dir / f".{final.name}.tmp"
            request = camera.capture_request()
            try:
                image = request.make_image("main")
                frame_metadata = request.get_metadata()
                image.save(temporary, format="JPEG", quality=capture["jpeg_quality"])
            finally:
                request.release()
            os.replace(temporary, final)
            metadata["frames"].append({
                "filename": final.name,
                "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
                "metadata": {k: v for k, v in frame_metadata.items()
                             if isinstance(v, (str, int, float, bool))},
                "write_success": True,
            })
            metadata["capture"]["frames_saved"] += 1
            time.sleep(max(0, capture["interval_ms"] / 1000 -
                           (time.monotonic() - tick)))
        metadata["status"] = "complete"
    except Exception as exc:
        metadata["errors"].append(str(exc))
        raise
    finally:
        camera.stop()
        metadata["capture_end_timestamp"] = datetime.now().astimezone().isoformat(
            timespec="milliseconds")
        atomic_json(event_dir / "event.json", metadata)
    return event_dir
