"""Application service for monitoring workflows and queries."""

from __future__ import annotations

from avalanche_risk_monitoring.connectors.storage.sqlite import SQLiteMonitoringRepository
from avalanche_risk_monitoring.domain.entities import IntegrationResult, MonitoringRun
from avalanche_risk_monitoring.domain.scoring import AvalancheRiskScoringService
from avalanche_risk_monitoring.integrations.fabric.publisher import MicrosoftFabricPublisher
from avalanche_risk_monitoring.observability.metrics import InMemoryMetrics
from avalanche_risk_monitoring.services.alerts.dispatcher import AlertDispatcher
from avalanche_risk_monitoring.services.analytics.summary import SummaryService
from avalanche_risk_monitoring.services.simulation.engine import SensorSimulationEngine


class MonitoringService:
    """Orchestrate simulation runs, derived views, and optional exports."""

    def __init__(
        self,
        simulator: SensorSimulationEngine,
        scorer: AvalancheRiskScoringService,
        repository: SQLiteMonitoringRepository,
        alerts: AlertDispatcher,
        summary: SummaryService,
        fabric: MicrosoftFabricPublisher,
        metrics: InMemoryMetrics,
    ) -> None:
        self._simulator = simulator
        self._scorer = scorer
        self._repository = repository
        self._alerts = alerts
        self._summary = summary
        self._fabric = fabric
        self._metrics = metrics

    def execute_run(self, zones, tick: int, run_id: str) -> MonitoringRun:
        readings = self._simulator.simulate(zones, tick=tick)
        assessments = [
            self._scorer.score(zone=zone, reading=reading)
            for zone, reading in zip(zones, readings, strict=True)
        ]
        run = self._repository.save_run(run_id=run_id, readings=readings, assessments=assessments)
        self._metrics.record_run(run)
        return run

    def latest_assessments(self):
        return self._repository.list_latest_assessments()

    def latest_alerts(self):
        return self._alerts.evaluate(self.latest_assessments())

    def latest_summary(self):
        assessments = self.latest_assessments()
        alerts = self._alerts.evaluate(assessments)
        return self._summary.build_regional_summary(assessments, alerts)

    def zone_analytics(self, limit: int):
        analytics = self._repository.list_zone_analytics(limit=limit)
        return {
            "overview": self._summary.build_analytics_overview(analytics),
            "zones": analytics,
        }

    def export_latest_to_fabric(self) -> IntegrationResult:
        assessments = self.latest_assessments()
        latest_run_id = self._repository.get_latest_run_id()
        if latest_run_id is None:
            raise ValueError("No monitoring run available to export.")
        latest_run = self._repository.get_run(latest_run_id)
        if latest_run is None:
            raise ValueError("Latest monitoring run could not be loaded.")
        alerts = self._alerts.evaluate(assessments)
        summary = self._summary.build_regional_summary(assessments, alerts)
        result = self._fabric.publish_run(latest_run, alerts, summary)
        self._metrics.record_fabric_export(result)
        return result
