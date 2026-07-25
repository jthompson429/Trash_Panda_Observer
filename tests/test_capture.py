import json

from trash_panda_observer.capture import capture_burst


class Image:
    def __init__(self, fail=False):
        self.fail = fail

    def save(self, path, **_kwargs):
        if self.fail:
            raise OSError("injected write failure")
        path.write_bytes(b"jpeg")


class Request:
    def __init__(self, fail=False):
        self.fail = fail
        self.released = False

    def make_image(self, _name):
        return Image(self.fail)

    def get_metadata(self):
        return {"ExposureTime": 123}

    def release(self):
        self.released = True


class Camera:
    def __init__(self):
        self.index = 0

    def capture_request(self):
        current = self.index
        self.index += 1
        return Request(fail=current == 1)


def test_failed_frame_does_not_abort_burst(tmp_path):
    config = {
        "camera": {"capture_width": 10, "capture_height": 10,
                   "analysis_width": 5, "analysis_height": 5,
                   "autofocus_mode": "continuous"},
        "motion": {"pixel_threshold": 25, "minimum_total_area": 1,
                   "minimum_largest_region_area": 1, "consecutive_frames": 2,
                   "cooldown_seconds": 15},
        "capture": {"frames_per_event": 3, "interval_ms": 1,
                    "jpeg_quality": 90},
        "storage": {"base_path": str(tmp_path), "minimum_free_space_gb": 0},
        "environment": {"lighting_mode": "unknown"},
    }
    event = capture_burst(Camera(), config, warmup_seconds=0, manage_camera=False)
    metadata = json.loads((event / "event.json").read_text())
    assert metadata["status"] == "incomplete"
    assert metadata["capture"]["frames_saved"] == 2
    assert [frame["write_success"] for frame in metadata["frames"]] == [
        True, False, True]
    assert not list(event.glob(".*.tmp"))
