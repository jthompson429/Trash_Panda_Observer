import pytest

from trash_panda_observer.coordinator import EventCoordinator


def test_queue_full_is_reported():
    subject = EventCoordinator(1, 0)
    assert subject.submit({"id": 1}, 0) == "accepted"
    assert subject.submit({"id": 2}, 0) == "queue_full"


def test_active_burst_suppresses_trigger():
    subject = EventCoordinator(1, 0)
    subject.submit({}, 0)
    subject.begin()
    assert subject.submit({}, 1) == "burst_active"


def test_cooldown_after_completion():
    subject = EventCoordinator(1, 15)
    subject.submit({}, 0)
    subject.begin()
    subject.complete(10)
    assert subject.submit({}, 24) == "cooldown"
    assert subject.submit({}, 25) == "accepted"


@pytest.mark.parametrize("size", [0, -1])
def test_invalid_queue_size(size):
    with pytest.raises(ValueError):
        EventCoordinator(size, 1)
