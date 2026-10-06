"""Application logging configuration."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from loguru import logger as _logger

logger = _logger
__all__ = ["configure_logging", "logger"]

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)
DEFAULT_LOG_DIR = Path.cwd() / "logs"
_configured = False


class InterceptHandler(logging.Handler):
    """Forward standard-library records from NiceGUI and Uvicorn to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 0
        while frame is not None and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> Path:
    """Configure console and rotating file logs, returning the log file path."""
    global _configured

    log_directory = Path(
        os.getenv("EXAMADMIN_LOG_DIR", str(DEFAULT_LOG_DIR))
    ).expanduser()
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = log_directory / "examadmin.log"

    if _configured:
        return log_file

    log_level = os.getenv("EXAMADMIN_LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=log_level,
        colorize=sys.stderr.isatty(),
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        log_file,
        format=LOG_FORMAT,
        level=log_level,
        rotation=os.getenv("EXAMADMIN_LOG_ROTATION", "10 MB"),
        retention=os.getenv("EXAMADMIN_LOG_RETENTION", "14 days"),
        compression="gz",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    intercept_handler = InterceptHandler()
    for logger_name in ("nicegui", "uvicorn", "uvicorn.error", "uvicorn.access"):
        standard_logger = logging.getLogger(logger_name)
        standard_logger.handlers = [intercept_handler]
        standard_logger.propagate = False

    _configured = True
    logger.info("Logging configured | level={level} file={file}", level=log_level, file=log_file)
    return log_file


configure_logging()
