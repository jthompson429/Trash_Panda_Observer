import logging

from trash_panda_observer.logging_setup import configure_logging
from trash_panda_observer.system_info import storage_summary, system_summary


def test_rotating_log_is_created(tmp_path):
    path = tmp_path / "logs/observer.log"
    configure_logging({"level": "INFO", "log_to_file": True,
                       "log_path": str(path), "maximum_log_size_mb": 1,
                       "backup_count": 2})
    logging.getLogger("test").info("hello")
    assert "hello" in path.read_text()


def test_summaries_are_serializable(tmp_path):
    assert system_summary()["python"]
    assert storage_summary(tmp_path)["free"] > 0
