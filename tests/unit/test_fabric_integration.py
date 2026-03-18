from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from avalanche_risk_monitoring.domain.entities import (
    Alert,
    AvalancheRiskAssessment,
    DerivedFeatures,
    IntegrationResult,
    MonitoringRun,
    RegionalSummary,
    RiskFactor,
    SensorReading,
)
from avalanche_risk_monitoring.domain.value_objects import RiskLevel
from avalanche_risk_monitoring.integrations.fabric.models import FabricSettings
from avalanche_risk_monitoring.integrations.fabric.publisher import MicrosoftFabricPublisher


def build_run() -> MonitoringRun:
    generated_at = datetime.now(timezone.utc)
    assessment = AvalancheRiskAssessment(
        zone_id="alpine-north",
        generated_at=generated_at,
        score=72,
        level=RiskLevel.HIGH,
        confidence=0.84,
        summary="High danger with wind slab and persistent weak layer concerns.",
        features=DerivedFeatures(
            storm_intensity=0.8,
            wind_loading=0.88,
            rapid_warming=0.2,
            slab_potential=0.74,
            persistent_weak_layer=0.81,
            terrain_exposure=0.67,
        ),
        component_scores={"wind_slab_formation": 15.2},
        contributing_factors=[
            RiskFactor(
                factor="wind_slab_formation",
                weight=18,
                score=15.2,
                impact="high",
                explanation="Strong southwest winds are loading lee terrain.",
            )
        ],
    )
    reading = SensorReading(
        zone_id="alpine-north",
        recorded_at=generated_at,
        air_temp_c=-6,
        snowfall_24h_cm=28,
        snowfall_72h_cm=44,
        wind_speed_kmh=68,
        wind_gust_kmh=92,
        snowpack_depth_cm=180,
        weak_layer_index=0.79,
        precipitation_mm=18,
        humidity_pct=83,
    )
    return MonitoringRun(run_id="run-1", generated_at=generated_at, readings=[reading], assessments=[assessment])


def build_summary(generated_at: datetime) -> RegionalSummary:
    alert = Alert(
        zone_id="alpine-north",
        generated_at=generated_at,
        severity="high",
        title="High avalanche danger in alpine-north",
        message="Conditions warrant conservative terrain choices.",
        trigger_factors=["wind_slab_formation"],
    )
    return RegionalSummary(
        generated_at=generated_at,
        zone_count=1,
        average_score=72,
        highest_risk_level=RiskLevel.HIGH,
        highest_risk_zone_id="alpine-north",
        elevated_zone_count=1,
        headline="High danger centered on alpine-north.",
        primary_concerns=["wind_slab_formation"],
        alerts=[alert],
    )


def test_fabric_status_defaults_to_disabled():
    publisher = MicrosoftFabricPublisher(FabricSettings())
    status = publisher.status()

    assert status.enabled is False
    assert status.mode == "disabled"
    assert status.configured is False


def test_fabric_staging_writes_local_export_bundle():
    staging_root = Path("data/interim") / f"fabric-test-{uuid4()}"
    settings = FabricSettings(
        enabled=True,
        mode="staging",
        workspace_id="workspace-123",
        lakehouse_id="lakehouse-456",
        staging_dir=str(staging_root),
    )
    publisher = MicrosoftFabricPublisher(settings)
    run = build_run()
    summary = build_summary(run.generated_at)

    try:
        result = publisher.publish_run(run, summary.alerts, summary)

        assert isinstance(result, IntegrationResult)
        assert result.status == "staged"
        assert len(result.artifacts) == 4
        assert all(Path(path).exists() for path in result.artifacts)
    finally:
        if staging_root.exists():
            for path in sorted(staging_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
