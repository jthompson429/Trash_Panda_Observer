"""Headless motion-analysis entry point."""

import argparse
import logging
import queue
import signal
import threading
import time
from pathlib import Path

from libcamera import controls
from picamera2 import Picamera2

from .capture import capture_burst
from .config import load_config
from .coordinator import EventCoordinator
from .logging_setup import configure_logging
from .motion import MotionDetector
from .system_info import storage_summary, system_summary


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
    config = load_config(args.config)
    camera_cfg, motion_cfg = config["camera"], config["motion"]
    configure_logging(config["logging"])
    log = logging.getLogger("trash_panda_observer")
    log.info("System summary %s", system_summary())
    log.info("Storage summary %s", storage_summary(Path(config["storage"]["base_path"])))
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
    camera = None
    last_camera_error = None
    for attempt in range(1, config["system"]["camera_retry_count"] + 1):
        try:
            camera = Picamera2()
            break
        except Exception as exc:
            last_camera_error = exc
            log.exception("Camera initialization attempt %d failed", attempt)
            if attempt < config["system"]["camera_retry_count"]:
                time.sleep(config["system"]["camera_retry_delay_seconds"])
    if camera is None:
        raise RuntimeError("camera initialization retries exhausted") from last_camera_error
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
    mode = "observation" if args.observe else "dry-run"
    log.info("Starting %s motion analysis at %s FPS", mode, fps)
    camera.start()
    coordinator = EventCoordinator(
        config["capture"]["maximum_pending_events"],
        motion_cfg["cooldown_seconds"],
    )
    worker_stop = threading.Event()
    worker_errors: queue.SimpleQueue[BaseException] = queue.SimpleQueue()

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
                worker_errors.put(RuntimeError("capture worker failed"))
            finally:
                coordinator.complete()

    worker = threading.Thread(target=capture_worker, name="capture-worker")
    if args.observe:
        worker.start()
    try:
        while not stop:
            if not worker_errors.empty():
                raise worker_errors.get()
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
