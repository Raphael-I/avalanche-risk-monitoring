"""Feature definitions and engineering contracts."""

from __future__ import annotations

from avalanche_risk_monitoring.domain.entities import (
    DerivedFeatures,
    SensorReading,
    ZoneDefinition,
)


def build_features(zone: ZoneDefinition, reading: SensorReading) -> DerivedFeatures:
    """Derive normalized hazard signals from a sensor reading."""

    storm_intensity = min(1.0, reading.snowfall_24h_cm / 30 + reading.snowfall_72h_cm / 80)
    wind_loading = min(1.0, (reading.wind_speed_kmh * 0.7 + reading.wind_gust_kmh * 0.3) / 90)
    rapid_warming = min(1.0, max(0.0, reading.air_temp_c + 8) / 14)
    slab_potential = min(1.0, reading.snowpack_depth_cm / 250)
    persistent_weak_layer = reading.weak_layer_index
    terrain_exposure = min(1.0, max(0.0, zone.slope_angle - 25) / 20)

    return DerivedFeatures(
        storm_intensity=round(storm_intensity, 3),
        wind_loading=round(wind_loading, 3),
        rapid_warming=round(rapid_warming, 3),
        slab_potential=round(slab_potential, 3),
        persistent_weak_layer=round(persistent_weak_layer, 3),
        terrain_exposure=round(terrain_exposure, 3),
    )

