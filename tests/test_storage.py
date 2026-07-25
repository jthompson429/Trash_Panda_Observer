import json
from datetime import datetime, timezone

import pytest

from trash_panda_observer.storage import (
    LowStorageError, atomic_json, create_event_directory, event_id,
    require_free_space,
)


def test_event_id_has_millisecond_precision():
    now = datetime(2026, 7, 24, 19, 41, 1, 606999, tzinfo=timezone.utc)
    assert event_id(now) == "20260724_194101_606"


def test_date_based_event_directory(tmp_path):
    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    identifier, path = create_event_directory(tmp_path, now)
    assert path == tmp_path / "captures/2026-07-24" / f"event_{identifier}"
    assert path.is_dir()


def test_collision_is_not_silently_reused(tmp_path):
    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    create_event_directory(tmp_path, now)
    with pytest.raises(FileExistsError):
        create_event_directory(tmp_path, now)


def test_atomic_json_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "event.json"
    atomic_json(path, {"status": "complete"})
    assert json.loads(path.read_text())["status"] == "complete"
    assert not (tmp_path / ".event.json.tmp").exists()


def test_impossible_free_space_threshold_fails(tmp_path):
    with pytest.raises(LowStorageError):
        require_free_space(tmp_path, 10**9)
