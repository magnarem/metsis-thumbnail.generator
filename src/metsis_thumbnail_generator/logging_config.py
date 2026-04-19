"""Central logging setup."""

from __future__ import annotations

import logging

try:
    import coloredlogs
    _HAS_COLOREDLOGS = True
except ImportError:
    _HAS_COLOREDLOGS = False


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """Configure console and optional file logging."""
    normalized_level = level.upper()
    logger = logging.getLogger("metsis_thumbnail_generator")
    logger.setLevel(normalized_level)

    if _HAS_COLOREDLOGS:
        coloredlogs.install(
            logger=logger,
            level=normalized_level,
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        handler = logging.StreamHandler()
        handler.setLevel(normalized_level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        if not logger.handlers:
            logger.addHandler(handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(normalized_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(file_handler)

    return logger
