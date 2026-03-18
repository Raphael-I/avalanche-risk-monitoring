from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from avalanche_risk_monitoring.bootstrap.container import ApplicationContainer
from avalanche_risk_monitoring.bootstrap.settings import AppSettings
from avalanche_risk_monitoring.connectors.storage.sqlite import SQLiteMonitoringRepository
from avalanche_risk_monitoring.domain.scoring import AvalancheRiskScoringService
from avalanche_risk_monitoring.domain.value_objects import RiskLevel
from avalanche_risk_monitoring.integrations.fabric.publisher import MicrosoftFabricPublisher
from avalanche_risk_monitoring.observability.metrics import InMemoryMetrics
from avalanche_risk_monitoring.services.alerts.dispatcher import AlertDispatcher
from avalanche_risk_monitoring.services.analytics.summary import SummaryService
from avalanche_risk_monitoring.services.api.app import create_app
from avalanche_risk_monitoring.services.monitoring.service import MonitoringService
from avalanche_risk_monitoring.services.simulation.engine import SensorSimulationEngine


def test_api_can_create_and_fetch_runs():
    database_path = Path("data/processed") / f"test-monitoring-{uuid4()}.db"
    settings = AppSettings(database_path=str(database_path))
    repository = SQLiteMonitoringRepository(str(database_path))
    simulator = SensorSimulationEngine(seed=settings.simulation_seed)
    scorer = AvalancheRiskScoringService()
    alerts = AlertDispatcher(
        score_threshold=settings.alert_score_threshold,
        level_threshold=RiskLevel(settings.alert_level_threshold),
    )
    summary = SummaryService()
    fabric = MicrosoftFabricPublisher(settings.fabric)
    metrics = InMemoryMetrics()
    container = ApplicationContainer(
        settings=settings,
        simulator=simulator,
        scorer=scorer,
        repository=repository,
        alerts=alerts,
        summary=summary,
        fabric=fabric,
        metrics=metrics,
        monitoring=MonitoringService(
            simulator=simulator,
            scorer=scorer,
            repository=repository,
            alerts=alerts,
            summary=summary,
            fabric=fabric,
            metrics=metrics,
        ),
    )
    container.initialize()
    client = TestClient(create_app(container))

    try:
        create_response = client.post("/runs", params={"tick": 3})
        assert create_response.status_code == 200
        run_payload = create_response.json()

        latest_response = client.get("/assessments/latest")
        assert latest_response.status_code == 200
        latest_payload = latest_response.json()

        alerts_response = client.get("/alerts/latest")
        assert alerts_response.status_code == 200

        summary_response = client.get("/summary/latest")
        assert summary_response.status_code == 200

        analytics_response = client.get("/analytics/zones", params={"limit": 5})
        assert analytics_response.status_code == 200

        fabric_status_response = client.get("/integrations/fabric/status")
        assert fabric_status_response.status_code == 200

        fabric_export_response = client.post("/integrations/fabric/export/latest")
        assert fabric_export_response.status_code == 200

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200

        root_response = client.get("/")
        assert root_response.status_code == 200
        assert "Avalanche Risk Monitoring Dashboard" in root_response.text

        history_response = client.get(f"/history/zones/{settings.zones[0].zone_id}", params={"limit": 8})
        assert history_response.status_code == 200

        fetch_response = client.get(f"/runs/{run_payload['run_id']}")
        assert fetch_response.status_code == 200

        assert len(run_payload["readings"]) == len(settings.zones)
        assert len(latest_payload) == len(settings.zones)
        assert "headline" in summary_response.json()
        assert "overview" in analytics_response.json()
        assert fabric_status_response.json()["enabled"] is False
        assert fabric_export_response.json()["status"] == "skipped"
        assert metrics_response.json()["monitoring_runs_total"] >= 1
        assert history_response.json()["zone_id"] == settings.zones[0].zone_id
        assert len(history_response.json()["history"]) >= 1
        assert isinstance(alerts_response.json(), list)
        assert fetch_response.json()["run_id"] == run_payload["run_id"]
    finally:
        if database_path.exists():
            database_path.unlink()
