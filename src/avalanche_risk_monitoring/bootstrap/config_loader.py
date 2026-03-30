"""Configuration loading entry points."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from avalanche_risk_monitoring.bootstrap.settings import AppSettings
from avalanche_risk_monitoring.integrations.fabric.models import FabricSettings


def load_settings(base_config_path: str = "config/base.yaml") -> AppSettings:
    """Load settings from YAML when available, otherwise return defaults."""

    config_path = Path(base_config_path)
    if not config_path.exists():
        project_root = Path(__file__).resolve().parents[3]
        candidate = project_root / base_config_path
        if candidate.exists():
            config_path = candidate

    if not config_path.exists():
        return AppSettings()

    with config_path.open("r", encoding="utf-8") as file_handle:
        raw_config: dict[str, Any] = yaml.safe_load(file_handle) or {}

    paths = raw_config.get("paths", {})
    app = raw_config.get("app", {})
    monitoring = raw_config.get("monitoring", {})

    # App Service deploys code into a location that should be treated as read-only.
    # Prefer /home/site for mutable runtime data when Azure-specific env vars are present.
    default_processed_root = "data/processed"
    if os.getenv("WEBSITE_INSTANCE_ID"):
        default_processed_root = "/home/site/data/processed"

    processed_root = os.getenv("APP_PROCESSED_DATA_PATH", paths.get("processed_data", default_processed_root))
    bootstrap_history_runs = int(os.getenv("APP_BOOTSTRAP_HISTORY_RUNS", monitoring.get("bootstrap_history_runs", 12)))
    alert_score_threshold = int(os.getenv("APP_ALERT_SCORE_THRESHOLD", monitoring.get("alert_score_threshold", 65)))
    environment = os.getenv("APP_ENVIRONMENT", app.get("environment", AppSettings().environment))
    timezone = os.getenv("APP_TIMEZONE", app.get("timezone", AppSettings().timezone))
    app_name = os.getenv("APP_NAME", app.get("name", AppSettings().app_name))

    return AppSettings(
        app_name=app_name,
        environment=environment,
        timezone=timezone,
        database_path=str(Path(processed_root) / "avalanche_monitoring.db"),
        bootstrap_history_runs=bootstrap_history_runs,
        alert_score_threshold=alert_score_threshold,
        fabric=FabricSettings.model_validate(raw_config.get("integrations", {}).get("fabric", {})),
    )
