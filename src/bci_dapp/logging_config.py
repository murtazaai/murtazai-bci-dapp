"""Centralised logging setup for bci_dapp.

Call :func:`configure_logging` once at application startup (in ``cli.main``
or an ASGI lifespan handler).  Library modules must never call this —
only the application entry-point does.

Usage::

    from bci_dapp.logging_config import configure_logging
    configure_logging(level="DEBUG")
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging(
    level: LogLevel = "INFO",
    *,
    fmt: str = _DEFAULT_FORMAT,
    datefmt: str = _DEFAULT_DATE_FORMAT,
    force: bool = False,
) -> None:
    """Configure the root logger for the application.

    Args:
        level:   Minimum log level to emit (default ``"INFO"``).
        fmt:     Log record format string.
        datefmt: Date/time format string.
        force:   If ``True``, remove existing handlers before adding new ones.
                 Pass ``True`` during testing to prevent handler accumulation.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    logging.basicConfig(level=level, handlers=[handler], force=force)
    logging.getLogger("bci_dapp").setLevel(level)
