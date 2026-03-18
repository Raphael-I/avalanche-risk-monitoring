"""Risk scoring policies and thresholds."""

from __future__ import annotations

from datetime import datetime, timezone

from avalanche_risk_monitoring.domain.entities import (
    AvalancheRiskAssessment,
    RiskFactor,
    SensorReading,
    ZoneDefinition,
)
from avalanche_risk_monitoring.domain.features import build_features
from avalanche_risk_monitoring.domain.value_objects import RiskLevel


class AvalancheRiskScoringService:
    """Compute avalanche risk from simulated zone conditions."""

    _factor_weights = {
        "new_snow_load": 22.0,
        "wind_slab_formation": 18.0,
        "persistent_weak_layer": 21.0,
        "warming_instability": 12.0,
        "terrain_amplification": 15.0,
        "snowpack_structure": 12.0,
    }

    def score(self, zone: ZoneDefinition, reading: SensorReading) -> AvalancheRiskAssessment:
        features = build_features(zone, reading)
        factor_strengths = {
            "new_snow_load": min(1.0, reading.snowfall_24h_cm / 25 + reading.snowfall_72h_cm / 90),
            "wind_slab_formation": min(
                1.0,
                features.wind_loading * 0.6 + features.storm_intensity * 0.25 + features.terrain_exposure * 0.15,
            ),
            "persistent_weak_layer": min(1.0, reading.weak_layer_index * 0.8 + features.slab_potential * 0.2),
            "warming_instability": min(
                1.0,
                max(0.0, (reading.air_temp_c + 2) / 8) * 0.7 + min(1.0, reading.precipitation_mm / 30) * 0.3,
            ),
            "terrain_amplification": min(
                1.0,
                features.terrain_exposure * 0.65 + min(1.0, zone.elevation_m / 2600) * 0.35,
            ),
            "snowpack_structure": min(
                1.0,
                features.slab_potential * 0.55 + features.persistent_weak_layer * 0.45,
            ),
        }
        component_scores = {
            factor: factor_strengths[factor] * self._factor_weights[factor]
            for factor in self._factor_weights
        }
        total_score = min(100, round(sum(component_scores.values())))
        level = self._to_level(total_score)
        confidence = self._confidence(features)
        contributing_factors = self._build_contributing_factors(zone, reading, factor_strengths, component_scores)

        return AvalancheRiskAssessment(
            zone_id=zone.zone_id,
            generated_at=datetime.now(timezone.utc),
            score=total_score,
            level=level,
            confidence=confidence,
            summary=self._summary(zone, level, contributing_factors),
            features=features,
            component_scores={key: round(value, 2) for key, value in component_scores.items()},
            contributing_factors=contributing_factors,
        )

    def _to_level(self, score: int) -> RiskLevel:
        if score >= 85:
            return RiskLevel.EXTREME
        if score >= 70:
            return RiskLevel.HIGH
        if score >= 50:
            return RiskLevel.CONSIDERABLE
        if score >= 25:
            return RiskLevel.MODERATE
        return RiskLevel.LOW

    def _confidence(self, features) -> float:
        spread = (
            features.storm_intensity
            + features.wind_loading
            + features.persistent_weak_layer
            + features.terrain_exposure
        ) / 4
        return round(0.55 + min(0.4, spread * 0.35), 3)

    def _build_contributing_factors(
        self,
        zone: ZoneDefinition,
        reading: SensorReading,
        factor_strengths: dict[str, float],
        component_scores: dict[str, float],
    ) -> list[RiskFactor]:
        factors = [
            RiskFactor(
                factor="new_snow_load",
                weight=self._factor_weights["new_snow_load"],
                score=round(component_scores["new_snow_load"], 2),
                impact=self._impact_label(factor_strengths["new_snow_load"]),
                explanation=(
                    f"{reading.snowfall_24h_cm:.1f} cm in 24h and {reading.snowfall_72h_cm:.1f} cm in 72h "
                    "increase slab formation and storm loading."
                ),
            ),
            RiskFactor(
                factor="wind_slab_formation",
                weight=self._factor_weights["wind_slab_formation"],
                score=round(component_scores["wind_slab_formation"], 2),
                impact=self._impact_label(factor_strengths["wind_slab_formation"]),
                explanation=(
                    f"Winds of {reading.wind_speed_kmh:.1f} km/h with gusts to {reading.wind_gust_kmh:.1f} km/h "
                    "can transport snow into lee start zones."
                ),
            ),
            RiskFactor(
                factor="persistent_weak_layer",
                weight=self._factor_weights["persistent_weak_layer"],
                score=round(component_scores["persistent_weak_layer"], 2),
                impact=self._impact_label(factor_strengths["persistent_weak_layer"]),
                explanation=(
                    f"Weak layer index {reading.weak_layer_index:.2f} suggests buried instability remains capable "
                    "of wider propagation."
                ),
            ),
            RiskFactor(
                factor="warming_instability",
                weight=self._factor_weights["warming_instability"],
                score=round(component_scores["warming_instability"], 2),
                impact=self._impact_label(factor_strengths["warming_instability"]),
                explanation=(
                    f"Air temperature of {reading.air_temp_c:.1f} C and {reading.precipitation_mm:.1f} mm water "
                    "equivalent can weaken recent storm snow bonds."
                ),
            ),
            RiskFactor(
                factor="terrain_amplification",
                weight=self._factor_weights["terrain_amplification"],
                score=round(component_scores["terrain_amplification"], 2),
                impact=self._impact_label(factor_strengths["terrain_amplification"]),
                explanation=(
                    f"{zone.name} sits on a {zone.slope_angle:.0f} degree {zone.aspect}-facing slope, "
                    "which amplifies consequences when loading is present."
                ),
            ),
            RiskFactor(
                factor="snowpack_structure",
                weight=self._factor_weights["snowpack_structure"],
                score=round(component_scores["snowpack_structure"], 2),
                impact=self._impact_label(factor_strengths["snowpack_structure"]),
                explanation=(
                    f"Snowpack depth of {reading.snowpack_depth_cm:.1f} cm combined with weak-layer sensitivity "
                    "supports cohesive slab behavior."
                ),
            ),
        ]
        return sorted(factors, key=lambda factor: factor.score, reverse=True)

    def _impact_label(self, value: float) -> str:
        if value >= 0.8:
            return "very high"
        if value >= 0.6:
            return "high"
        if value >= 0.35:
            return "moderate"
        return "low"

    def _summary(
        self,
        zone: ZoneDefinition,
        level: RiskLevel,
        contributing_factors: list[RiskFactor],
    ) -> str:
        top = contributing_factors[:2]
        top_text = " and ".join(factor.factor.replace("_", " ") for factor in top)
        return f"{zone.name} is rated {level.value}; primary drivers are {top_text}."
