from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO", *, verbose: bool = False) -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("lessondigest")
    resolved = "DEBUG" if verbose else level.upper()
    if not _CONFIGURED:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)
        _CONFIGURED = True
    logger.setLevel(resolved)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger("lessondigest" if not name else f"lessondigest.{name}")
