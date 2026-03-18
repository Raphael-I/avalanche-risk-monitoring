from datetime import datetime, timezone

from avalanche_risk_monitoring.domain.entities import SensorReading, ZoneDefinition
from avalanche_risk_monitoring.domain.scoring import AvalancheRiskScoringService
from avalanche_risk_monitoring.domain.value_objects import RiskLevel


def test_scoring_returns_high_risk_for_severe_conditions():
    service = AvalancheRiskScoringService()
    zone = ZoneDefinition(
        zone_id="test-zone",
        name="Test Zone",
        elevation_m=2400,
        slope_angle=40,
        aspect="N",
        tree_line_m=1800,
    )
    reading = SensorReading(
        zone_id="test-zone",
        recorded_at=datetime.now(timezone.utc),
        air_temp_c=2.0,
        snowfall_24h_cm=36.0,
        snowfall_72h_cm=70.0,
        wind_speed_kmh=72.0,
        wind_gust_kmh=95.0,
        snowpack_depth_cm=215.0,
        weak_layer_index=0.85,
        precipitation_mm=28.0,
        humidity_pct=94.0,
    )

    assessment = service.score(zone, reading)

    assert assessment.score >= 70
    assert assessment.level in {RiskLevel.HIGH, RiskLevel.EXTREME}
    assert assessment.contributing_factors[0].score >= assessment.contributing_factors[-1].score
    assert "primary drivers" in assessment.summary


def test_scoring_explains_dominant_risk_factors():
    service = AvalancheRiskScoringService()
    zone = ZoneDefinition(
        zone_id="wind-loaded-zone",
        name="Wind Loaded Start Zone",
        elevation_m=2300,
        slope_angle=39,
        aspect="NE",
        tree_line_m=1800,
    )
    reading = SensorReading(
        zone_id="wind-loaded-zone",
        recorded_at=datetime.now(timezone.utc),
        air_temp_c=-1.0,
        snowfall_24h_cm=24.0,
        snowfall_72h_cm=52.0,
        wind_speed_kmh=80.0,
        wind_gust_kmh=110.0,
        snowpack_depth_cm=205.0,
        weak_layer_index=0.76,
        precipitation_mm=20.0,
        humidity_pct=88.0,
    )

    assessment = service.score(zone, reading)

    top_names = [factor.factor for factor in assessment.contributing_factors[:3]]
    assert "wind_slab_formation" in top_names
    assert all(factor.explanation for factor in assessment.contributing_factors)
