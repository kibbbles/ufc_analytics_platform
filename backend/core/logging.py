"""core/logging.py — Structured JSON logging with rotating file output.

Call configure_logging() once at application startup (lifespan in main.py).
After that, use standard logging.getLogger(__name__) throughout the app.

Log levels:
  - development : DEBUG
  - production  : INFO  (or override via LOG_LEVEL env var)

Output:
  - Console — JSON lines to stdout
  - File    — JSON lines, rotated at 10 MB, 5 backups kept
              Written to logs/app.log relative to the project root.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

from pythonjsonlogger.json import JsonFormatter


_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")
_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per file
_BACKUP_COUNT = 5                # keep 5 rotated files


def configure_logging(log_level: str = "DEBUG") -> None:
    """Configure the root logger with JSON console + rotating file handlers.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
                   Passed from settings.log_level at startup.
    """
    os.makedirs(_LOG_DIR, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.DEBUG)
    fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
    formatter = JsonFormatter(fmt)

    # ── Console handler ────────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # ── Rotating file handler ──────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # ── Root logger ────────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    logging.getLogger(__name__).debug(
        "Logging configured",
        extra={"log_level": log_level, "log_file": os.path.abspath(_LOG_FILE)},
    )
