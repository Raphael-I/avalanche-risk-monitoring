"""Configuration loading entry points."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from avalanche_risk_monitoring.bootstrap.settings import AppSettings
from avalanche_risk_monitoring.integrations.fabric.models import FabricSettings


def load_settings(base_config_path: str = "config/base.yaml") -> AppSettings:
    """Load settings from YAML when available, otherwise return defaults."""

    config_path = Path(base_config_path)
    if not config_path.exists():
        return AppSettings()

    with config_path.open("r", encoding="utf-8") as file_handle:
        raw_config: dict[str, Any] = yaml.safe_load(file_handle) or {}

    paths = raw_config.get("paths", {})
    app = raw_config.get("app", {})

    return AppSettings(
        app_name=app.get("name", AppSettings().app_name),
        environment=app.get("environment", AppSettings().environment),
        timezone=app.get("timezone", AppSettings().timezone),
        database_path=str(Path(paths.get("processed_data", "data/processed")) / "avalanche_monitoring.db"),
        bootstrap_history_runs=raw_config.get("monitoring", {}).get("bootstrap_history_runs", 12),
        alert_score_threshold=raw_config.get("monitoring", {}).get("alert_score_threshold", 65),
        fabric=FabricSettings.model_validate(raw_config.get("integrations", {}).get("fabric", {})),
    )
