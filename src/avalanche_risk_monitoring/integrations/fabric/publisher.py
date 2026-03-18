"""Optional Microsoft Fabric publishing service."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from avalanche_risk_monitoring.domain.entities import (
    Alert,
    IntegrationResult,
    MonitoringRun,
    RegionalSummary,
)
from avalanche_risk_monitoring.integrations.fabric.models import FabricSettings, FabricStatus


class MicrosoftFabricPublisher:
    """Publish monitoring results to Microsoft Fabric when explicitly configured."""

    def __init__(self, settings: FabricSettings) -> None:
        self._settings = settings

    def status(self) -> FabricStatus:
        missing = self._missing_requirements()
        credential_present = bool(os.getenv(self._settings.token_env_var))
        configured = self._settings.enabled and not missing

        if not self._settings.enabled or self._settings.mode == "disabled":
            message = "Fabric integration is disabled. Local mode remains active."
        elif missing:
            message = "Fabric integration is enabled but incomplete. Remote publishing will be skipped."
        else:
            message = "Fabric integration is configured and ready."

        return FabricStatus(
            enabled=self._settings.enabled,
            mode=self._settings.mode,
            configured=configured,
            workspace_id=self._settings.workspace_id,
            lakehouse_id=self._settings.lakehouse_id,
            dataset_name=self._settings.dataset_name,
            staging_dir=self._settings.staging_dir,
            credential_present=credential_present,
            message=message,
            missing_requirements=missing,
        )

    def publish_run(
        self,
        monitoring_run: MonitoringRun,
        alerts: list[Alert],
        summary: RegionalSummary,
    ) -> IntegrationResult:
        status = self.status()
        exported_at = datetime.now(timezone.utc)

        if not self._settings.enabled or self._settings.mode == "disabled":
            return IntegrationResult(
                integration="microsoft-fabric",
                mode=self._settings.mode,
                status="skipped",
                message=status.message,
                exported_at=exported_at,
            )

        if self._settings.mode == "staging":
            artifacts = self._write_staging_bundle(monitoring_run, alerts, summary)
            return IntegrationResult(
                integration="microsoft-fabric",
                mode=self._settings.mode,
                status="staged",
                message="Fabric export bundle written locally for later ingestion.",
                exported_at=exported_at,
                artifacts=artifacts,
            )

        if self._settings.mode == "api":
            if status.missing_requirements:
                return IntegrationResult(
                    integration="microsoft-fabric",
                    mode=self._settings.mode,
                    status="skipped",
                    message=status.message,
                    exported_at=exported_at,
                )
            artifact = self._post_bundle(monitoring_run, alerts, summary)
            return IntegrationResult(
                integration="microsoft-fabric",
                mode=self._settings.mode,
                status="published",
                message="Fabric API export completed.",
                exported_at=exported_at,
                artifacts=[artifact],
            )

        return IntegrationResult(
            integration="microsoft-fabric",
            mode=self._settings.mode,
            status="skipped",
            message=f"Unsupported Fabric mode '{self._settings.mode}'.",
            exported_at=exported_at,
        )

    def _write_staging_bundle(
        self,
        monitoring_run: MonitoringRun,
        alerts: list[Alert],
        summary: RegionalSummary,
    ) -> list[str]:
        output_dir = Path(self._settings.staging_dir) / monitoring_run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        artifacts = []
        payloads = {
            "run.json": monitoring_run.model_dump(mode="json"),
            "alerts.json": [alert.model_dump(mode="json") for alert in alerts],
            "summary.json": summary.model_dump(mode="json"),
            "fabric_manifest.json": {
                "workspace_id": self._settings.workspace_id,
                "lakehouse_id": self._settings.lakehouse_id,
                "dataset_name": self._settings.dataset_name,
                "run_id": monitoring_run.run_id,
            },
        }

        for filename, payload in payloads.items():
            path = output_dir / filename
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            artifacts.append(str(path))

        return artifacts

    def _post_bundle(
        self,
        monitoring_run: MonitoringRun,
        alerts: list[Alert],
        summary: RegionalSummary,
    ) -> str:
        token = os.getenv(self._settings.token_env_var)
        if not token:
            raise ValueError("Fabric API mode requires a bearer token environment variable.")

        payload = {
            "workspace_id": self._settings.workspace_id,
            "lakehouse_id": self._settings.lakehouse_id,
            "dataset_name": self._settings.dataset_name,
            "run": monitoring_run.model_dump(mode="json"),
            "alerts": [alert.model_dump(mode="json") for alert in alerts],
            "summary": summary.model_dump(mode="json"),
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self._settings.api_base_url.rstrip("/") + "/runs",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            response.raise_for_status()

        return self._settings.api_base_url.rstrip("/") + "/runs"

    def _missing_requirements(self) -> list[str]:
        missing: list[str] = []
        if not self._settings.enabled or self._settings.mode == "disabled":
            return missing

        if not self._settings.workspace_id:
            missing.append("workspace_id")
        if not self._settings.lakehouse_id:
            missing.append("lakehouse_id")

        if self._settings.mode == "api":
            if not self._settings.api_base_url:
                missing.append("api_base_url")
            if not os.getenv(self._settings.token_env_var):
                missing.append(self._settings.token_env_var)

        return missing
