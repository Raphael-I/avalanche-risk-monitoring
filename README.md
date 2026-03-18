# Avalanche Risk Monitoring

A local-first avalanche risk monitoring service built to demonstrate practical backend engineering, domain modeling, analytics, and product presentation in one portfolio project.

## Status

Production-style portfolio project with a runnable FastAPI backend, SQLite persistence, a polished operator dashboard, alerting logic, historical analytics, and optional Microsoft Fabric export workflows.

## Why This Project Is Credible

- The system is locally runnable end to end with no cloud dependency or hidden services.
- Scoring output is not a black box: each assessment includes weighted contributing factors and plain-language explanations.
- Historical analytics, alerts, dashboard views, and optional export workflows all use the same persisted run data.
- External integration is treated as optional infrastructure, not a hidden requirement.

## What It Demonstrates

- FastAPI application design with clear service boundaries
- Typed configuration and dependency wiring
- SQLite-backed persistence with historical query support
- Domain-focused risk scoring with interpretable outputs
- Frontend presentation for a technical operations dashboard
- Optional enterprise integration patterns with safe local defaults

## Architecture

```text
avalanche-risk-monitoring/
|-- config/
|-- data/
|-- docs/
|-- scripts/
|-- src/
|   `-- avalanche_risk_monitoring/
`-- tests/
```

Core service boundaries:

- `domain/`: scoring logic, entities, and value objects
- `services/monitoring/`: orchestration for runs, summaries, analytics, and exports
- `connectors/storage/`: SQLite persistence and historical query support
- `services/api/`: FastAPI routes plus dashboard assets
- `integrations/fabric/`: optional Microsoft Fabric export layer
- `observability/`: logging and lightweight runtime metrics

End-to-end runtime flow:

1. A monitoring cycle is triggered through the API or scheduler.
2. The simulation engine produces deterministic environmental readings for each zone.
3. The scoring service derives avalanche-relevant features and weighted danger signals.
4. The repository persists raw readings and assessments into SQLite.
5. Analytics and alert services build zone trends, active alerts, and regional summaries from persisted data.
6. The dashboard and API consume those read models.
7. If enabled, the latest run can be exported to Microsoft Fabric in staging or API mode.

## Quick Start

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the API locally with `python -m avalanche_risk_monitoring`.
4. Open `http://127.0.0.1:8000/` for the live dashboard.
5. Open `http://127.0.0.1:8000/docs` for the interactive API.

## What To Demo

- Trigger a new run from the dashboard or `POST /runs`
- Show zone-level danger, trend direction, and contributing factors
- Open historical charts for a single zone
- Show active alerts and the regional summary headline
- Call the Fabric status/export endpoints to show optional enterprise integration without requiring credentials

## Configuration

- Base application settings: `config/base.yaml`
- Environment overlays: `config/environments/`
- Logging setup: `config/logging.yaml`
- Data source registry: `config/sources.yaml`

## API Surface

- `GET /health`: service health and runtime configuration summary
- `GET /metrics`: in-memory operational counters for local runs and exports
- `POST /runs`: generate a new monitoring run
- `GET /assessments/latest`: latest danger assessments by zone
- `GET /alerts/latest`: active alerts derived from current assessments
- `GET /summary/latest`: regional headline summary
- `GET /analytics/zones`: zone-level averages, peaks, and trends
- `GET /history/zones/{zone_id}`: chart-friendly risk and sensor history
- `GET /integrations/fabric/status`: Fabric configuration status
- `POST /integrations/fabric/export/latest`: export the latest run to the configured Fabric mode

## Microsoft Fabric Integration

Microsoft Fabric support is optional and disabled by default. Local SQLite mode remains the default runtime path.

- Status endpoint: `GET /integrations/fabric/status`
- Export endpoint: `POST /integrations/fabric/export/latest`
- Default mode: `disabled`
- Local handoff mode: `staging` writes export bundles under `data/interim/fabric_exports/`
- Remote mode: `api` requires explicit config plus a bearer token in the environment variable named by `integrations.fabric.token_env_var`

Example config shape in `config/base.yaml`:

```yaml
integrations:
  fabric:
    enabled: false
    mode: disabled
    workspace_id: null
    lakehouse_id: null
    api_base_url: null
    dataset_name: avalanche_risk_monitoring
    staging_dir: data/interim/fabric_exports
    token_env_var: MICROSOFT_FABRIC_TOKEN
```

## Documentation

- Architecture plan: `docs/architecture-plan.md`
- Operational runbooks: `docs/runbooks/`
- ADRs: `docs/adr/`

## Engineering Notes

- Keep business rules in `domain/`.
- Keep I/O and vendor-specific code in `connectors/`.
- Keep orchestration in `services/monitoring/` instead of route handlers.
- Prefer typed settings, explicit service boundaries, and deterministic test fixtures.
- Local mode remains the default and does not require cloud credentials.

## Tradeoffs

- Environmental inputs are currently simulated rather than sourced from live upstream feeds.
- Runtime metrics are intentionally lightweight and in-memory to keep local execution frictionless.
- Fabric API publishing is modeled as an optional integration boundary rather than a required deployment target.
