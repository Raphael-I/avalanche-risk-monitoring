"""Base storage adapter interfaces."""

from __future__ import annotations

from typing import Protocol

from avalanche_risk_monitoring.domain.entities import (
    AvalancheRiskAssessment,
    MonitoringRun,
    SensorReading,
    ZoneAnalytics,
    ZoneHistoryPoint,
)


class MonitoringRepository(Protocol):
    """Persistence contract for monitoring runs."""

    def initialize(self) -> None:
        """Create storage schema if needed."""

    def save_run(
        self,
        run_id: str,
        readings: list[SensorReading],
        assessments: list[AvalancheRiskAssessment],
    ) -> MonitoringRun:
        """Persist a monitoring run and return the saved payload."""

    def list_latest_assessments(self) -> list[AvalancheRiskAssessment]:
        """Return the latest assessment for each zone."""

    def get_run(self, run_id: str) -> MonitoringRun | None:
        """Fetch a run by id."""

    def list_zone_analytics(self, limit: int = 10) -> list[ZoneAnalytics]:
        """Return zone score history analytics."""

    def get_zone_history(self, zone_id: str, limit: int = 24) -> list[ZoneHistoryPoint]:
        """Return recent history points for a single zone."""
