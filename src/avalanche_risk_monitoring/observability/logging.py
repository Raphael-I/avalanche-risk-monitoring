"""Logging bootstrap utilities."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml


def configure_logging(config_path: str = "config/logging.yaml") -> None:
    """Configure logging from YAML, falling back to a sensible console setup."""

    path = Path(config_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as file_handle:
            config = yaml.safe_load(file_handle) or {}
        logging.config.dictConfig(config)
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
