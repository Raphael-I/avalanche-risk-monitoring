"""In-memory operational metrics for local execution and demos."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from avalanche_risk_monitoring.domain.entities import IntegrationResult, MonitoringRun


@dataclass
class InMemoryMetrics:
    """Track lightweight operational counters without external dependencies."""

    counters: Counter = field(default_factory=Counter)
    last_run_id: str | None = None
    last_export_status: str | None = None

    def record_run(self, monitoring_run: MonitoringRun) -> None:
        self.counters["monitoring_runs_total"] += 1
        self.counters["assessments_generated_total"] += len(monitoring_run.assessments)
        self.last_run_id = monitoring_run.run_id

    def record_fabric_export(self, result: IntegrationResult) -> None:
        self.counters["fabric_exports_total"] += 1
        self.counters[f"fabric_exports_{result.status}_total"] += 1
        self.last_export_status = result.status

    def hydrate(self, snapshot: dict[str, int | str | None]) -> None:
        for key, value in snapshot.items():
            if key == "last_run_id":
                self.last_run_id = value if isinstance(value, str) else None
            elif key == "last_export_status":
                self.last_export_status = value if isinstance(value, str) else None
            elif isinstance(value, int):
                self.counters[key] = value

    def snapshot(self) -> dict[str, int | str | None]:
        return {
            **dict(self.counters),
            "last_run_id": self.last_run_id,
            "last_export_status": self.last_export_status,
        }
