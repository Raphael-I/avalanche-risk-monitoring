"""Local scheduler abstraction for repeated monitoring execution."""

from __future__ import annotations

from avalanche_risk_monitoring.bootstrap.container import ApplicationContainer
from avalanche_risk_monitoring.domain.entities import MonitoringRun


class LocalScheduler:
    """Thin job runner for local repeated execution and future scheduler integration."""

    def __init__(self, container: ApplicationContainer) -> None:
        self._container = container

    def run_once(self, tick: int = 0) -> MonitoringRun:
        return self._container.execute_monitoring_run(tick=tick)
