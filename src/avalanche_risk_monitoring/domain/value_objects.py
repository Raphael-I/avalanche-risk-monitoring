"""Small immutable domain value objects."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """Ordered avalanche risk categories."""

    LOW = "low"
    MODERATE = "moderate"
    CONSIDERABLE = "considerable"
    HIGH = "high"
    EXTREME = "extreme"

