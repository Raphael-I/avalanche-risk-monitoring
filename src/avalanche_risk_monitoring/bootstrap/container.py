"""Dependency container and service assembly."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from avalanche_risk_monitoring.bootstrap.config_loader import load_settings
from avalanche_risk_monitoring.bootstrap.settings import AppSettings
from avalanche_risk_monitoring.connectors.storage.sqlite import SQLiteMonitoringRepository
from avalanche_risk_monitoring.domain.entities import MonitoringRun
from avalanche_risk_monitoring.domain.scoring import AvalancheRiskScoringService
from avalanche_risk_monitoring.domain.value_objects import RiskLevel
from avalanche_risk_monitoring.integrations.fabric.publisher import MicrosoftFabricPublisher
from avalanche_risk_monitoring.observability.logging import configure_logging
from avalanche_risk_monitoring.observability.metrics import InMemoryMetrics
from avalanche_risk_monitoring.services.alerts.dispatcher import AlertDispatcher
from avalanche_risk_monitoring.services.analytics.summary import SummaryService
from avalanche_risk_monitoring.services.monitoring.service import MonitoringService
from avalanche_risk_monitoring.services.simulation.engine import SensorSimulationEngine


LOGGER = logging.getLogger(__name__)


@dataclass
class ApplicationContainer:
    """Shared runtime dependencies."""

    settings: AppSettings
    simulator: SensorSimulationEngine
    scorer: AvalancheRiskScoringService
    repository: SQLiteMonitoringRepository
    alerts: AlertDispatcher
    summary: SummaryService
    fabric: MicrosoftFabricPublisher
    metrics: InMemoryMetrics
    monitoring: MonitoringService

    def initialize(self) -> None:
        self.repository.initialize()
        self.metrics.hydrate(self.repository.get_repository_stats())
        if not self.repository.list_latest_assessments():
            LOGGER.info("Bootstrapping synthetic monitoring history", extra={"runs": self.settings.bootstrap_history_runs})
            for tick in range(self.settings.bootstrap_history_runs):
                self.execute_monitoring_run(tick=tick)

    def execute_monitoring_run(self, tick: int | None = None) -> MonitoringRun:
        tick_value = self.settings.default_tick if tick is None else tick
        run = self.monitoring.execute_run(self.settings.zones, tick=tick_value, run_id=str(uuid4()))
        LOGGER.info("Monitoring run completed", extra={"run_id": run.run_id, "tick": tick_value})
        return run


def build_container() -> ApplicationContainer:
    """Create and initialize the application container."""

    configure_logging()
    settings = load_settings()
    repository = SQLiteMonitoringRepository(settings.database_path)
    metrics = InMemoryMetrics()
    simulator = SensorSimulationEngine(seed=settings.simulation_seed)
    scorer = AvalancheRiskScoringService()
    alerts = AlertDispatcher(
        score_threshold=settings.alert_score_threshold,
        level_threshold=RiskLevel(settings.alert_level_threshold),
    )
    summary = SummaryService()
    fabric = MicrosoftFabricPublisher(settings.fabric)
    monitoring = MonitoringService(
        simulator=simulator,
        scorer=scorer,
        repository=repository,
        alerts=alerts,
        summary=summary,
        fabric=fabric,
        metrics=metrics,
    )
    container = ApplicationContainer(
        settings=settings,
        simulator=simulator,
        scorer=scorer,
        repository=repository,
        alerts=alerts,
        summary=summary,
        fabric=fabric,
        metrics=metrics,
        monitoring=monitoring,
    )
    LOGGER.info("Application container created", extra={"environment": settings.environment})
    container.initialize()
    return container
