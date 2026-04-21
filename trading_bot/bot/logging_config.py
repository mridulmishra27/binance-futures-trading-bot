from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

LOGGER_NAME = "trading_bot"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def mask_secret(value: str | None, keep: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= keep:
        return "***"
    return f"{value[:keep]}***"


def configure_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trading_bot.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Idempotent: clear any handlers left over from a previous CLI invocation in the same process.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(file_handler)

    console_handler = RichHandler(
        level=logging.INFO,
        show_time=True,
        show_path=False,
        markup=False,
        rich_tracebacks=True,
    )
    logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
