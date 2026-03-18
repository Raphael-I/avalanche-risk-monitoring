"""Alert generation policies for operational escalation."""

from __future__ import annotations

from avalanche_risk_monitoring.domain.entities import Alert, AvalancheRiskAssessment
from avalanche_risk_monitoring.domain.value_objects import RiskLevel


class AlertDispatcher:
    """Create actionable alerts from risk assessments."""

    def __init__(self, score_threshold: int = 65, level_threshold: RiskLevel = RiskLevel.HIGH) -> None:
        self._score_threshold = score_threshold
        self._level_threshold = level_threshold
        self._severity_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 1,
            RiskLevel.CONSIDERABLE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.EXTREME: 4,
        }

    def evaluate(self, assessments: list[AvalancheRiskAssessment]) -> list[Alert]:
        alerts: list[Alert] = []
        for assessment in assessments:
            if not self._should_alert(assessment):
                continue

            top_factors = sorted(
                assessment.contributing_factors,
                key=lambda factor: factor.score,
                reverse=True,
            )[:3]
            alerts.append(
                Alert(
                    zone_id=assessment.zone_id,
                    generated_at=assessment.generated_at,
                    severity=assessment.level.value,
                    title=f"{assessment.level.value.title()} avalanche danger in {assessment.zone_id}",
                    message=assessment.summary,
                    trigger_factors=[factor.factor for factor in top_factors],
                )
            )

        return alerts

    def _should_alert(self, assessment: AvalancheRiskAssessment) -> bool:
        return assessment.score >= self._score_threshold or (
            self._severity_order[assessment.level] >= self._severity_order[self._level_threshold]
        )
