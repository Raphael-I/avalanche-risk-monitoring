"""Deterministic sensor simulation engine for local execution."""

from __future__ import annotations

from datetime import datetime, timezone
from random import Random

from avalanche_risk_monitoring.domain.entities import SensorReading, ZoneDefinition


class SensorSimulationEngine:
    """Generate reproducible synthetic sensor readings for configured zones."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    def simulate(self, zones: list[ZoneDefinition], tick: int = 0) -> list[SensorReading]:
        recorded_at = datetime.now(timezone.utc)
        readings: list[SensorReading] = []

        for index, zone in enumerate(zones):
            rng = Random(self._seed + tick * 101 + index * 17)
            elevation_factor = min(1.2, zone.elevation_m / 2500)
            slope_factor = zone.slope_angle / 45

            snowfall_24h = max(0.0, rng.gauss(18 * elevation_factor, 6))
            snowfall_72h = snowfall_24h + max(0.0, rng.gauss(22 * elevation_factor, 10))
            wind_speed = max(0.0, rng.gauss(35 + 18 * slope_factor, 10))
            wind_gust = wind_speed + max(0.0, rng.gauss(12, 6))
            weak_layer = min(1.0, max(0.05, rng.random() * 0.6 + slope_factor * 0.2))
            air_temp = rng.gauss(-8 + elevation_factor * -4, 4)
            humidity = min(100.0, max(40.0, rng.gauss(78, 12)))
            precipitation = max(0.0, snowfall_24h * 0.7 + rng.gauss(3, 2))
            snowpack_depth = max(40.0, rng.gauss(140 + elevation_factor * 80, 25))

            readings.append(
                SensorReading(
                    zone_id=zone.zone_id,
                    recorded_at=recorded_at,
                    air_temp_c=round(air_temp, 2),
                    snowfall_24h_cm=round(snowfall_24h, 2),
                    snowfall_72h_cm=round(snowfall_72h, 2),
                    wind_speed_kmh=round(wind_speed, 2),
                    wind_gust_kmh=round(wind_gust, 2),
                    snowpack_depth_cm=round(snowpack_depth, 2),
                    weak_layer_index=round(weak_layer, 3),
                    precipitation_mm=round(precipitation, 2),
                    humidity_pct=round(humidity, 2),
                )
            )

        return readings

