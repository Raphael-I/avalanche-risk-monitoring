"""Microsoft Fabric integration settings and status models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FabricSettings(BaseModel):
    """Optional Microsoft Fabric integration configuration."""

    enabled: bool = False
    mode: str = "disabled"
    workspace_id: str | None = None
    lakehouse_id: str | None = None
    api_base_url: str | None = None
    dataset_name: str = "avalanche_risk_monitoring"
    staging_dir: str = "data/interim/fabric_exports"
    token_env_var: str = "MICROSOFT_FABRIC_TOKEN"


class FabricStatus(BaseModel):
    """Readable runtime integration status."""

    enabled: bool
    mode: str
    configured: bool
    workspace_id: str | None = None
    lakehouse_id: str | None = None
    dataset_name: str
    staging_dir: str
    credential_present: bool
    message: str
    missing_requirements: list[str] = Field(default_factory=list)
