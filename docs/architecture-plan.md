# Architecture Plan

## Objective

Build a local-first avalanche risk monitoring service that turns environmental readings into interpretable zone-level danger assessments, persists them for analysis, and exposes them through APIs, a dashboard, alerts, and optional export integrations.

## Architectural Principles

- Separate domain logic from infrastructure concerns.
- Keep local execution fully functional without cloud dependencies.
- Drive runtime behavior through typed settings and explicit service composition.
- Treat analytics and summaries as read models derived from persisted runs, not ad hoc route logic.
- Make integration points optional and replaceable.
- Keep observability and testability first-class.

## Implemented System Topology

### `bootstrap`

Owns startup configuration, dependency wiring, and application assembly.

### `domain`

Owns entities, value objects, derived features, and avalanche danger scoring.

Responsibilities:
- Zone definitions
- Sensor readings
- Risk factors and assessments
- Danger level classification
- Summary and integration payload models

### `connectors/storage`

Owns SQLite persistence and historical query patterns.

Responsibilities:
- Monitoring run persistence
- Latest assessment reads
- Zone trend analytics
- Per-zone history queries
- Repository statistics for runtime metrics

### `services/monitoring`

Owns orchestration of runs, summaries, alerts, analytics, and exports.

Responsibilities:
- Trigger monitoring cycles
- Coordinate scoring and persistence
- Build read models for API consumers
- Invoke optional export workflows

### `services/api`

Owns the FastAPI surface and bundled dashboard.

Responsibilities:
- Serve JSON APIs
- Serve the dashboard frontend
- Validate request parameters
- Map application errors to HTTP responses

### `services/alerts` and `services/analytics`

Own separate alert generation and summary/analytics logic from route handlers and storage.

### `integrations/fabric`

Own the optional Microsoft Fabric export boundary with disabled, staging, and API modes.

### `observability`

Own logging configuration and lightweight runtime metrics suitable for local execution.

## Runtime Flow

1. A monitoring cycle starts through `POST /runs` or the local scheduler.
2. The simulation engine generates deterministic readings for each configured zone.
3. The scoring service derives features such as storm loading, wind transport, weak-layer persistence, and warming instability.
4. The repository persists both sensor readings and final assessments.
5. Analytics and alert services compute latest views from persisted data.
6. The API and dashboard consume those read models.
7. If enabled, the latest run can be exported to Microsoft Fabric.
8. Observability components record run counts and export outcomes.

## Current Design Strengths

- Local mode is the default and requires no credentials.
- Core orchestration is concentrated in a dedicated monitoring service rather than spread across route handlers.
- The dashboard, analytics, and exports are all backed by persisted data instead of in-memory-only state.
- Integration risk is contained behind a separate Fabric publisher.
- The system is small enough to understand quickly but structured enough to extend responsibly.

## Highest-Value Next Extensions

- Replace simulated feeds with one or two real upstream environmental connectors.
- Add connector contract tests and fixture-backed ingestion tests.
- Persist run-level metadata such as trigger source, duration, and export outcomes.
- Add authentication or role separation if the service becomes multi-user.
- Introduce a deployment target and external metrics only when the project needs it.

## Testing Strategy

- Unit tests for domain policies and feature calculations.
- Integration tests for API flows and local persistence behavior.
- Export tests for disabled and staging integration modes.
- Smoke tests for dashboard serving, health checks, and history endpoints.
