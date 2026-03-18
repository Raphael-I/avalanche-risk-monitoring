"""SQLite-backed monitoring repository."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from avalanche_risk_monitoring.domain.entities import (
    AvalancheRiskAssessment,
    MonitoringRun,
    SensorReading,
    ZoneAnalytics,
    ZoneHistoryPoint,
)


class SQLiteMonitoringRepository:
    """Persist monitoring runs into a local SQLite database."""

    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS monitoring_runs (
                    run_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    zone_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS risk_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    zone_id TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sensor_readings_run_zone
                ON sensor_readings (run_id, zone_id);

                CREATE INDEX IF NOT EXISTS idx_risk_assessments_zone_generated_at
                ON risk_assessments (zone_id, generated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_monitoring_runs_generated_at
                ON monitoring_runs (generated_at DESC);
                """
            )

    def save_run(
        self,
        run_id: str,
        readings: list[SensorReading],
        assessments: list[AvalancheRiskAssessment],
    ) -> MonitoringRun:
        generated_at = assessments[0].generated_at if assessments else None
        if generated_at is None:
            raise ValueError("At least one assessment is required to persist a monitoring run.")

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO monitoring_runs (run_id, generated_at) VALUES (?, ?)",
                (run_id, generated_at.isoformat()),
            )

            connection.executemany(
                "INSERT INTO sensor_readings (run_id, zone_id, payload) VALUES (?, ?, ?)",
                [
                    (run_id, reading.zone_id, json.dumps(reading.model_dump(mode="json")))
                    for reading in readings
                ],
            )

            connection.executemany(
                """
                INSERT INTO risk_assessments (run_id, zone_id, generated_at, score, level, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        assessment.zone_id,
                        assessment.generated_at.isoformat(),
                        assessment.score,
                        assessment.level.value,
                        json.dumps(assessment.model_dump(mode="json")),
                    )
                    for assessment in assessments
                ],
            )

        return MonitoringRun(
            run_id=run_id,
            generated_at=generated_at,
            readings=readings,
            assessments=assessments,
        )

    def list_latest_assessments(self) -> list[AvalancheRiskAssessment]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ra.payload
                FROM risk_assessments ra
                INNER JOIN (
                    SELECT zone_id, MAX(generated_at) AS generated_at
                    FROM risk_assessments
                    GROUP BY zone_id
                ) latest
                    ON latest.zone_id = ra.zone_id
                   AND latest.generated_at = ra.generated_at
                ORDER BY ra.zone_id
                """
            ).fetchall()

        return [AvalancheRiskAssessment.model_validate(json.loads(row["payload"])) for row in rows]

    def get_run(self, run_id: str) -> MonitoringRun | None:
        with self._connect() as connection:
            run_row = connection.execute(
                "SELECT run_id, generated_at FROM monitoring_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if run_row is None:
                return None

            readings_rows = connection.execute(
                "SELECT payload FROM sensor_readings WHERE run_id = ? ORDER BY zone_id",
                (run_id,),
            ).fetchall()
            assessment_rows = connection.execute(
                "SELECT payload FROM risk_assessments WHERE run_id = ? ORDER BY zone_id",
                (run_id,),
            ).fetchall()

        return MonitoringRun(
            run_id=run_row["run_id"],
            generated_at=run_row["generated_at"],
            readings=[SensorReading.model_validate(json.loads(row["payload"])) for row in readings_rows],
            assessments=[
                AvalancheRiskAssessment.model_validate(json.loads(row["payload"]))
                for row in assessment_rows
            ],
        )

    def get_latest_run_id(self) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id
                FROM monitoring_runs
                ORDER BY generated_at DESC
                LIMIT 1
                """
            ).fetchone()
        return None if row is None else str(row["run_id"])

    def get_repository_stats(self) -> dict[str, int | str | None]:
        with self._connect() as connection:
            run_count = connection.execute("SELECT COUNT(*) AS count FROM monitoring_runs").fetchone()
            assessment_count = connection.execute(
                "SELECT COUNT(*) AS count FROM risk_assessments"
            ).fetchone()
            latest_run = connection.execute(
                """
                SELECT run_id
                FROM monitoring_runs
                ORDER BY generated_at DESC
                LIMIT 1
                """
            ).fetchone()

        return {
            "monitoring_runs_total": int(run_count["count"]) if run_count else 0,
            "assessments_generated_total": int(assessment_count["count"]) if assessment_count else 0,
            "last_run_id": None if latest_run is None else str(latest_run["run_id"]),
        }

    def list_zone_analytics(self, limit: int = 10) -> list[ZoneAnalytics]:
        with self._connect() as connection:
            zone_rows = connection.execute(
                """
                SELECT zone_id
                FROM risk_assessments
                GROUP BY zone_id
                ORDER BY zone_id
                """
            ).fetchall()

            analytics: list[ZoneAnalytics] = []
            for zone_row in zone_rows:
                zone_id = zone_row["zone_id"]
                rows = connection.execute(
                    """
                    SELECT generated_at, score, payload
                    FROM risk_assessments
                    WHERE zone_id = ?
                    ORDER BY generated_at DESC
                    LIMIT ?
                    """,
                    (zone_id, limit),
                ).fetchall()
                if not rows:
                    continue

                scores = [int(row["score"]) for row in rows]
                latest_assessment = AvalancheRiskAssessment.model_validate(json.loads(rows[0]["payload"]))
                trend = "stable"
                if len(scores) >= 2:
                    delta = scores[0] - scores[-1]
                    if delta >= 10:
                        trend = "rising"
                    elif delta <= -10:
                        trend = "falling"

                analytics.append(
                    ZoneAnalytics(
                        zone_id=zone_id,
                        latest_score=latest_assessment.score,
                        latest_level=latest_assessment.level,
                        average_score=round(sum(scores) / len(scores), 2),
                        max_score=max(scores),
                        run_count=len(scores),
                        trend=trend,
                    )
                )

        return analytics

    def get_zone_history(self, zone_id: str, limit: int = 24) -> list[ZoneHistoryPoint]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ra.payload AS assessment_payload, sr.payload AS sensor_payload
                FROM risk_assessments ra
                INNER JOIN sensor_readings sr
                    ON sr.run_id = ra.run_id
                   AND sr.zone_id = ra.zone_id
                WHERE ra.zone_id = ?
                ORDER BY ra.generated_at DESC
                LIMIT ?
                """,
                (zone_id, limit),
            ).fetchall()

        history: list[ZoneHistoryPoint] = []
        for row in reversed(rows):
            assessment = AvalancheRiskAssessment.model_validate(json.loads(row["assessment_payload"]))
            reading = SensorReading.model_validate(json.loads(row["sensor_payload"]))
            history.append(
                ZoneHistoryPoint(
                    generated_at=assessment.generated_at,
                    score=assessment.score,
                    level=assessment.level,
                    snowfall_24h_cm=reading.snowfall_24h_cm,
                    wind_speed_kmh=reading.wind_speed_kmh,
                    weak_layer_index=reading.weak_layer_index,
                    air_temp_c=reading.air_temp_c,
                )
            )

        return history
