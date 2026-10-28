"""Logging configuration for local runs (Airflow configures its own)."""

import logging
import os

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger. Level comes from the argument, then LOG_LEVEL, then INFO."""
    chosen = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    if chosen not in logging.getLevelNamesMapping():
        raise ValueError(f"Invalid log level: {chosen!r}")
    logging.basicConfig(level=chosen, format=LOG_FORMAT)
