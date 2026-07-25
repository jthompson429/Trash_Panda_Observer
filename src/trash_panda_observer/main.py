"""Headless motion-analysis entry point."""

import argparse
import logging
import signal
import threading
import time
from pathlib import Path

import yaml
from libcamera import controls
from picamera2 import Picamera2

from .capture import capture_burst
from .coordinator import EventCoordinator
from .motion import MotionDetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--capture-test", action="store_true")
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--motion-debug", action="store_true")
    parser.add_argument("--max-runtime-minutes", type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = yaml.safe_load(args.config.read_text())
    camera_cfg, motion_cfg = config["camera"], config["motion"]
    logging.basicConfig(
        level=config.get("logging", {}).get("level", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("trash_panda_observer")
    detector = MotionDetector(
        pixel_threshold=motion_cfg["pixel_threshold"],
        minimum_total_area=motion_cfg["minimum_total_area"],
        minimum_largest_area=motion_cfg["minimum_largest_region_area"],
        consecutive_frames=motion_cfg["consecutive_frames"],
        blur_kernel=motion_cfg["blur_kernel_size"],
        morphology_kernel=motion_cfg["morphology_kernel_size"],
        background_alpha=motion_cfg["background_alpha"],
        roi=motion_cfg.get("region_of_interest"),
    )
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    camera = Picamera2()
    fps = camera_cfg["analysis_fps"]
    configuration = camera.create_video_configuration(
        main={
            "size": (camera_cfg["capture_width"], camera_cfg["capture_height"]),
            "format": "RGB888",
        },
        lores={
            "size": (camera_cfg["analysis_width"], camera_cfg["analysis_height"]),
            "format": "YUV420",
        },
        controls={"FrameDurationLimits": (round(1_000_000 / fps),) * 2},
        buffer_count=4,
        queue=False,
    )
    camera.configure(configuration)
    af_modes = {
        "continuous": controls.AfModeEnum.Continuous,
        "auto": controls.AfModeEnum.Auto,
        "manual": controls.AfModeEnum.Manual,
    }
    camera.set_controls({"AfMode": af_modes[camera_cfg["autofocus_mode"]]})
    if args.capture_test:
        event_dir = capture_burst(camera, config)
        camera.close()
        print(event_dir)
        return 0
    if not (args.dry_run or args.observe):
        raise SystemExit("Specify --dry-run, --observe, or --capture-test")
    started = time.monotonic()
    warmup_until = started + motion_cfg["warmup_seconds"]
    debug_interval = config.get("logging", {}).get(
        "motion_debug_interval_seconds", 5
    )
    next_debug = started
    log.info("Starting dry-run motion analysis at %s FPS", fps)
    camera.start()
    coordinator = EventCoordinator(
        config["capture"]["maximum_pending_events"],
        motion_cfg["cooldown_seconds"],
    )
    worker_stop = threading.Event()

    def capture_worker() -> None:
        while not worker_stop.is_set() or not coordinator.events.empty():
            try:
                event = coordinator.begin()
            except Exception:
                time.sleep(0.05)
                continue
            try:
                path = capture_burst(
                    camera, config, warmup_seconds=0, manage_camera=False
                )
                log.info("Captured event path=%s trigger=%s", path, event)
            except Exception:
                log.exception("Capture worker failed")
            finally:
                coordinator.complete()

    worker = threading.Thread(target=capture_worker, name="capture-worker")
    if args.observe:
        worker.start()
    try:
        while not stop:
            now = time.monotonic()
            if (
                args.max_runtime_minutes is not None
                and now - started >= args.max_runtime_minutes * 60
            ):
                break
            yuv = camera.capture_array("lores")
            grayscale = yuv[: camera_cfg["analysis_height"], :]
            result = detector.process(grayscale)
            if now < warmup_until:
                detector.reset_streak()
            elif result.triggered:
                if args.dry_run:
                    log.info(
                        "DRY-RUN trigger total_area=%d largest_area=%.0f",
                        result.total_area, result.largest_area,
                    )
                else:
                    reason = coordinator.submit({
                        "total_area": result.total_area,
                        "largest_area": result.largest_area,
                    })
                    log.info("Trigger admission=%s", reason)
            if args.motion_debug and now >= next_debug:
                log.info(
                    "motion total_area=%d largest_area=%.0f qualifying=%s warmup=%s",
                    result.total_area,
                    result.largest_area,
                    result.qualifying,
                    now < warmup_until,
                )
                next_debug = now + debug_interval
    finally:
        worker_stop.set()
        if args.observe:
            worker.join(timeout=30)
        camera.stop()
        camera.close()
        log.info("Motion analysis stopped cleanly")
    return 0
