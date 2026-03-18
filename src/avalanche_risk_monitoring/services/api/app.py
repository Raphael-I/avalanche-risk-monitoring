"""FastAPI application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from avalanche_risk_monitoring.bootstrap.container import ApplicationContainer, build_container


LOGGER = logging.getLogger(__name__)


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    """Create a FastAPI app for local execution."""

    runtime_container = container or build_container()
    app = FastAPI(title=runtime_container.settings.app_name, version="0.1.0")
    app.state.container = runtime_container
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "app_name": runtime_container.settings.app_name,
            "environment": runtime_container.settings.environment,
            "database_path": runtime_container.settings.database_path,
            "fabric_mode": runtime_container.settings.fabric.mode,
        }

    @app.get("/metrics")
    def metrics() -> dict[str, int | str | None]:
        return runtime_container.metrics.snapshot()

    @app.get("/zones")
    def list_zones() -> list[dict[str, str | int | float]]:
        return [zone.model_dump(mode="json") for zone in runtime_container.settings.zones]

    @app.post("/runs")
    def create_run(tick: int = Query(default=0, ge=0)) -> dict[str, object]:
        run = runtime_container.execute_monitoring_run(tick=tick)
        LOGGER.info("Run requested via API", extra={"run_id": run.run_id, "tick": tick})
        return run.model_dump(mode="json")

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        run = runtime_container.repository.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run.model_dump(mode="json")

    @app.get("/assessments/latest")
    def latest_assessments() -> list[dict[str, object]]:
        return [assessment.model_dump(mode="json") for assessment in runtime_container.monitoring.latest_assessments()]

    @app.get("/alerts/latest")
    def latest_alerts() -> list[dict[str, object]]:
        return [alert.model_dump(mode="json") for alert in runtime_container.monitoring.latest_alerts()]

    @app.get("/summary/latest")
    def latest_summary() -> dict[str, object]:
        return runtime_container.monitoring.latest_summary().model_dump(mode="json")

    @app.get("/analytics/zones")
    def zone_analytics(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, object]:
        payload = runtime_container.monitoring.zone_analytics(limit=limit)
        return {
            "overview": payload["overview"],
            "zones": [zone.model_dump(mode="json") for zone in payload["zones"]],
        }

    @app.get("/history/zones/{zone_id}")
    def zone_history(zone_id: str, limit: int = Query(default=24, ge=1, le=240)) -> dict[str, object]:
        history = runtime_container.repository.get_zone_history(zone_id, limit=limit)
        if not history:
            raise HTTPException(status_code=404, detail="Zone history not found")
        return {
            "zone_id": zone_id,
            "history": [point.model_dump(mode="json") for point in history],
        }

    @app.get("/integrations/fabric/status")
    def fabric_status() -> dict[str, object]:
        return runtime_container.fabric.status().model_dump(mode="json")

    @app.post("/integrations/fabric/export/latest")
    def fabric_export_latest() -> dict[str, object]:
        try:
            result = runtime_container.monitoring.export_latest_to_fabric()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return result.model_dump(mode="json")

    return app


app = create_app()
