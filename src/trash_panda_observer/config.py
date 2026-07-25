"""Configuration loading and validation."""

from pathlib import Path

import yaml


def load_config(path: Path) -> dict:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("configuration root must be a mapping")
    for section in ("camera", "motion", "capture", "storage", "logging", "system"):
        if not isinstance(value.get(section), dict):
            raise ValueError(f"missing required section: {section}")
    camera, motion, capture = value["camera"], value["motion"], value["capture"]
    for key in ("analysis_width", "analysis_height", "capture_width",
                "capture_height", "analysis_fps"):
        if not isinstance(camera.get(key), int) or camera[key] <= 0:
            raise ValueError(f"camera.{key} must be a positive integer")
    if camera.get("autofocus_mode") not in {"continuous", "auto", "manual"}:
        raise ValueError("unsupported autofocus mode")
    if capture.get("maximum_pending_events", 0) < 1:
        raise ValueError("capture.maximum_pending_events must be positive")
    if motion.get("cooldown_seconds", -1) < 0:
        raise ValueError("motion.cooldown_seconds cannot be negative")
    roi = motion.get("region_of_interest")
    if roi is not None:
        if (not isinstance(roi, list) or len(roi) != 4 or
                any(not isinstance(v, (int, float)) for v in roi)):
            raise ValueError("motion.region_of_interest must contain four numbers")
        x, y, width, height = roi
        if min(x, y, width, height) < 0 or width == 0 or height == 0 or \
                x + width > 1 or y + height > 1:
            raise ValueError("motion.region_of_interest must fit within the frame")
    if value["storage"].get("minimum_free_space_gb", -1) < 0:
        raise ValueError("storage.minimum_free_space_gb cannot be negative")
    if value["storage"].get("retention_enabled") and \
            value["storage"].get("retention_days", 0) <= 0:
        raise ValueError("enabled retention requires positive retention_days")
    system = value["system"]
    if system.get("camera_retry_count", 0) < 1:
        raise ValueError("system.camera_retry_count must be positive")
    if system.get("camera_retry_delay_seconds", -1) < 0:
        raise ValueError("system.camera_retry_delay_seconds cannot be negative")
    return value
