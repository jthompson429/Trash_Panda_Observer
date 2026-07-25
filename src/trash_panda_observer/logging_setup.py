"""Application logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(config: dict, override: str | None = None) -> None:
    level = getattr(logging, (override or config["level"]).upper())
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.get("log_to_file"):
        path = Path(config["log_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(
            path,
            maxBytes=int(config["maximum_log_size_mb"] * 1024**2),
            backupCount=config["backup_count"],
        ))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
        handlers=handlers,
        force=True,
    )
