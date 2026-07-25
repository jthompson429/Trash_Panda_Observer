import logging

from trash_panda_observer.logging_setup import configure_logging
from trash_panda_observer.system_info import (
    git_revision, storage_summary, system_summary,
)


def test_rotating_log_is_created(tmp_path):
    path = tmp_path / "logs/observer.log"
    configure_logging({"level": "INFO", "log_to_file": True,
                       "log_path": str(path), "maximum_log_size_mb": 1,
                       "backup_count": 2})
    logging.getLogger("test").info("hello")
    assert "hello" in path.read_text()


def test_rotating_log_keeps_bounded_backups(tmp_path):
    path = tmp_path / "logs/observer.log"
    configure_logging({"level": "INFO", "log_to_file": True,
                       "log_path": str(path), "maximum_log_size_mb": 0.001,
                       "backup_count": 2})
    logger = logging.getLogger("rotation-test")
    for index in range(200):
        logger.info("message %03d %s", index, "x" * 100)
    assert path.exists()
    assert (path.parent / "observer.log.1").exists()
    assert len(list(path.parent.glob("observer.log.*"))) <= 2


def test_summaries_are_serializable(tmp_path):
    assert system_summary()["python"]
    assert storage_summary(tmp_path)["free"] > 0


def test_capture_directory_size_is_reported(tmp_path):
    capture = tmp_path / "captures/event"
    capture.mkdir(parents=True)
    (capture / "frame.jpg").write_bytes(b"1234")
    assert storage_summary(tmp_path)["capture_bytes"] == 4


def test_missing_git_repository_has_no_revision(tmp_path):
    assert git_revision(tmp_path) is None
