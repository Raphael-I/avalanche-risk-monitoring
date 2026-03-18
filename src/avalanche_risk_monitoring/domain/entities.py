"""Core entities for forecasts, observations, and risk outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field

from avalanche_risk_monitoring.domain.value_objects import RiskLevel


class ZoneDefinition(BaseModel):
    """Static metadata for a monitored zone."""

    zone_id: str
    name: str
    elevation_m: int = Field(ge=0)
    slope_angle: float = Field(ge=0, le=65)
    aspect: str
    tree_line_m: int = Field(ge=0)


class SensorReading(BaseModel):
    """Synthetic environmental state for a zone."""

    zone_id: str
    recorded_at: datetime
    air_temp_c: float
    snowfall_24h_cm: float = Field(ge=0)
    snowfall_72h_cm: float = Field(ge=0)
    wind_speed_kmh: float = Field(ge=0)
    wind_gust_kmh: float = Field(ge=0)
    snowpack_depth_cm: float = Field(ge=0)
    weak_layer_index: float = Field(ge=0, le=1)
    precipitation_mm: float = Field(ge=0)
    humidity_pct: float = Field(ge=0, le=100)


class DerivedFeatures(BaseModel):
    """Risk-relevant derived signals."""

    storm_intensity: float = Field(ge=0)
    wind_loading: float = Field(ge=0)
    rapid_warming: float = Field(ge=0)
    slab_potential: float = Field(ge=0)
    persistent_weak_layer: float = Field(ge=0)
    terrain_exposure: float = Field(ge=0)


class RiskFactor(BaseModel):
    """Human-readable contributor to avalanche danger."""

    factor: str
    weight: float = Field(ge=0)
    score: float = Field(ge=0)
    impact: str
    explanation: str


class AvalancheRiskAssessment(BaseModel):
    """Final risk assessment for a single zone."""

    zone_id: str
    generated_at: datetime
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    summary: str
    features: DerivedFeatures
    component_scores: Dict[str, float]
    contributing_factors: list[RiskFactor] = Field(default_factory=list)


class Alert(BaseModel):
    """Operational alert generated from an assessment."""

    zone_id: str
    generated_at: datetime
    severity: str
    title: str
    message: str
    trigger_factors: list[str]


class ZoneAnalytics(BaseModel):
    """Time-series analytics for a single zone."""

    zone_id: str
    latest_score: int = Field(ge=0, le=100)
    latest_level: RiskLevel
    average_score: float = Field(ge=0, le=100)
    max_score: int = Field(ge=0, le=100)
    run_count: int = Field(ge=0)
    trend: str


class ZoneHistoryPoint(BaseModel):
    """Combined sensor and risk history point for one zone and run timestamp."""

    generated_at: datetime
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    snowfall_24h_cm: float = Field(ge=0)
    wind_speed_kmh: float = Field(ge=0)
    weak_layer_index: float = Field(ge=0, le=1)
    air_temp_c: float


class RegionalSummary(BaseModel):
    """Aggregated summary across latest zone assessments."""

    generated_at: datetime
    zone_count: int = Field(ge=0)
    average_score: float = Field(ge=0, le=100)
    highest_risk_level: RiskLevel
    highest_risk_zone_id: str
    elevated_zone_count: int = Field(ge=0)
    headline: str
    primary_concerns: list[str]
    alerts: list[Alert]


class IntegrationResult(BaseModel):
    """Outcome of an optional external integration action."""

    integration: str
    mode: str
    status: str
    message: str
    exported_at: datetime
    artifacts: list[str] = Field(default_factory=list)


class MonitoringRun(BaseModel):
    """Persisted run bundle."""

    run_id: str
    generated_at: datetime
    readings: list[SensorReading]
    assessments: list[AvalancheRiskAssessment]
