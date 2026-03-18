"""Typed application settings."""

from __future__ import annotations

from pydantic import BaseModel, Field

from avalanche_risk_monitoring.domain.entities import ZoneDefinition
from avalanche_risk_monitoring.integrations.fabric.models import FabricSettings


class AppSettings(BaseModel):
    """Runtime configuration for local execution."""

    app_name: str = "avalanche-risk-monitoring"
    environment: str = "local"
    timezone: str = "America/Toronto"
    database_path: str = "data/processed/avalanche_monitoring.db"
    simulation_seed: int = 42
    default_tick: int = 0
    bootstrap_history_runs: int = 12
    alert_score_threshold: int = 65
    alert_level_threshold: str = "high"
    fabric: FabricSettings = Field(default_factory=FabricSettings)
    zones: list[ZoneDefinition] = Field(
        default_factory=lambda: [
            ZoneDefinition(
                zone_id="alpine-north",
                name="Raven Pass North Bowl",
                elevation_m=2280,
                slope_angle=38,
                aspect="NE",
                tree_line_m=1850,
            ),
            ZoneDefinition(
                zone_id="glacier-south",
                name="Granite Glacier South Face",
                elevation_m=2450,
                slope_angle=41,
                aspect="S",
                tree_line_m=1900,
            ),
            ZoneDefinition(
                zone_id="timber-west",
                name="Timberline West Shoulder",
                elevation_m=1920,
                slope_angle=34,
                aspect="W",
                tree_line_m=1700,
            ),
        ]
    )
