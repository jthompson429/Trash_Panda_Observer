import numpy as np
import pytest

from trash_panda_observer.motion import MotionDetector


def detector(**overrides):
    values = dict(
        pixel_threshold=10,
        minimum_total_area=100,
        minimum_largest_area=50,
        consecutive_frames=2,
        blur_kernel=3,
        morphology_kernel=3,
        background_alpha=0.02,
    )
    values.update(overrides)
    return MotionDetector(**values)


def test_requires_consecutive_qualifying_frames():
    subject = detector()
    background = np.zeros((100, 100), np.uint8)
    moving = background.copy()
    moving[20:60, 20:60] = 255
    assert not subject.process(background).triggered
    assert not subject.process(moving).triggered
    assert subject.process(moving).triggered


def test_normalized_roi_excludes_outside_motion():
    subject = detector(roi=[0.5, 0.5, 0.5, 0.5])
    background = np.zeros((100, 100), np.uint8)
    outside = background.copy()
    outside[0:30, 0:30] = 255
    subject.process(background)
    assert not subject.process(outside).qualifying


def test_streak_can_be_reset_after_warmup():
    subject = detector()
    background = np.zeros((100, 100), np.uint8)
    moving = background.copy()
    moving[20:60, 20:60] = 255
    subject.process(background)
    subject.process(moving)
    subject.reset_streak()
    assert not subject.process(moving).triggered
    assert subject.process(moving).triggered


def test_full_reset_discards_background_and_streak():
    subject = detector()
    background = np.zeros((100, 100), np.uint8)
    moving = background.copy()
    moving[20:60, 20:60] = 255
    subject.process(background)
    subject.process(moving)
    subject.reset()
    result = subject.process(moving)
    assert result.total_area == 0
    assert subject.streak == 0


@pytest.mark.parametrize("roi", [[0, 0, 0, 1], [0.8, 0, 0.5, 1], [0, 0, 2, 1]])
def test_invalid_roi_is_rejected(roi):
    subject = detector(roi=roi)
    with pytest.raises(ValueError):
        subject.process(np.zeros((100, 100), np.uint8))
