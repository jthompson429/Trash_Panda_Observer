#!/usr/bin/env python3
"""Verify a Picamera2 camera and capture one headless test image."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    from libcamera import controls
    from picamera2 import Picamera2
except ImportError as exc:  # pragma: no cover - depends on Raspberry Pi packages
    print(
        "Camera verification requires Raspberry Pi OS packages "
        "python3-picamera2 and libcamera.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


AF_MODES = {
    "manual": controls.AfModeEnum.Manual,
    "auto": controls.AfModeEnum.Auto,
    "continuous": controls.AfModeEnum.Continuous,
}


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect a Picamera2 camera and save one verification JPEG."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/trash-panda-observer-verification.jpg"),
        help="JPEG output path (default: %(default)s)",
    )
    parser.add_argument("--width", type=positive_int, default=2304)
    parser.add_argument("--height", type=positive_int, default=1296)
    parser.add_argument(
        "--autofocus-mode",
        choices=tuple(AF_MODES),
        default="continuous",
    )
    parser.add_argument(
        "--manual-lens-position",
        type=float,
        default=None,
        help="Lens position to use with --autofocus-mode manual",
    )
    parser.add_argument(
        "--warmup-seconds",
        type=positive_float,
        default=2.0,
    )
    return parser.parse_args(argv)


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return str(value)


def print_json(label: str, value: Any) -> None:
    print(f"{label}: {json.dumps(json_safe(value), sort_keys=True)}")


def choose_size(
    requested: tuple[int, int], sensor_modes: list[dict[str, Any]]
) -> tuple[int, int]:
    supported = [tuple(mode["size"]) for mode in sensor_modes]
    if requested in supported:
        return requested
    options = ", ".join(f"{width}x{height}" for width, height in supported)
    raise ValueError(
        f"requested size {requested[0]}x{requested[1]} is unsupported; "
        f"available sensor modes: {options}"
    )


def validate_focus_options(args: argparse.Namespace, camera: Picamera2) -> None:
    camera_controls = camera.camera_controls
    if "AfMode" not in camera_controls:
        raise RuntimeError("camera does not expose autofocus mode controls")
    if args.manual_lens_position is not None and args.autofocus_mode != "manual":
        raise ValueError(
            "--manual-lens-position requires --autofocus-mode manual"
        )
    if args.autofocus_mode == "manual":
        if args.manual_lens_position is None:
            raise ValueError(
                "manual autofocus mode requires --manual-lens-position"
            )
        minimum, maximum, _default = camera_controls["LensPosition"]
        if not minimum <= args.manual_lens_position <= maximum:
            raise ValueError(
                f"manual lens position must be between {minimum} and {maximum}"
            )


def verification_controls(args: argparse.Namespace) -> dict[str, Any]:
    selected: dict[str, Any] = {"AfMode": AF_MODES[args.autofocus_mode]}
    if args.autofocus_mode == "manual":
        selected["LensPosition"] = args.manual_lens_position
    return selected


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cameras = Picamera2.global_camera_info()
    print_json("Detected cameras", cameras)
    if not cameras:
        print("No cameras detected.", file=sys.stderr)
        return 1

    camera = Picamera2(0)
    started = False
    try:
        sensor_modes = camera.sensor_modes
        print_json("Sensor modes", sensor_modes)
        print_json("Supported controls", camera.camera_controls)

        size = choose_size((args.width, args.height), sensor_modes)
        validate_focus_options(args, camera)

        config = camera.create_still_configuration(
            main={"size": size, "format": "RGB888"},
            buffer_count=4,
            queue=False,
        )
        camera.align_configuration(config)
        print_json("Selected configuration", config)
        camera.configure(config)
        camera.set_controls(verification_controls(args))
        camera.start()
        started = True
        time.sleep(args.warmup_seconds)

        if args.autofocus_mode == "auto":
            success = camera.autofocus_cycle()
            print(f"Autofocus cycle successful: {success}")

        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        metadata = camera.capture_file(str(output))
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"camera did not create a valid file at {output}")

        print(f"Image path: {output}")
        print(f"Image dimensions: {size[0]}x{size[1]}")
        print(f"Image bytes: {output.stat().st_size}")
        print_json("Capture metadata", metadata)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Camera verification failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if started:
            camera.stop()
        camera.close()


if __name__ == "__main__":
    raise SystemExit(main())
