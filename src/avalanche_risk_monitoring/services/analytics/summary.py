"""Regional summary and analytics helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from avalanche_risk_monitoring.domain.entities import Alert, AvalancheRiskAssessment, RegionalSummary, ZoneAnalytics
from avalanche_risk_monitoring.domain.value_objects import RiskLevel


class SummaryService:
    """Generate interpretable regional summaries from assessments."""

    _risk_order = {
        RiskLevel.LOW: 0,
        RiskLevel.MODERATE: 1,
        RiskLevel.CONSIDERABLE: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.EXTREME: 4,
    }

    def build_regional_summary(
        self,
        assessments: list[AvalancheRiskAssessment],
        alerts: list[Alert],
    ) -> RegionalSummary:
        if not assessments:
            return RegionalSummary(
                generated_at=datetime.now(timezone.utc),
                zone_count=0,
                average_score=0,
                highest_risk_level=RiskLevel.LOW,
                highest_risk_zone_id="",
                elevated_zone_count=0,
                headline="No assessments available.",
                primary_concerns=[],
                alerts=[],
            )

        highest = max(assessments, key=lambda item: item.score)
        elevated = [item for item in assessments if item.level in {RiskLevel.CONSIDERABLE, RiskLevel.HIGH, RiskLevel.EXTREME}]
        factor_counter = Counter()
        for assessment in assessments:
            for factor in assessment.contributing_factors[:3]:
                factor_counter[factor.factor] += factor.score

        top_concerns = [name for name, _ in factor_counter.most_common(3)]
        return RegionalSummary(
            generated_at=max(item.generated_at for item in assessments),
            zone_count=len(assessments),
            average_score=round(sum(item.score for item in assessments) / len(assessments), 2),
            highest_risk_level=highest.level,
            highest_risk_zone_id=highest.zone_id,
            elevated_zone_count=len(elevated),
            headline=(
                f"{highest.level.value.title()} danger centered on {highest.zone_id}; "
                f"{len(elevated)} of {len(assessments)} zones are at considerable or above."
            ),
            primary_concerns=top_concerns,
            alerts=alerts,
        )

    def build_analytics_overview(self, zone_analytics: list[ZoneAnalytics]) -> dict[str, object]:
        if not zone_analytics:
            return {"zone_count": 0, "average_score": 0, "rising_zones": [], "highest_zone_id": None}

        highest = max(zone_analytics, key=lambda item: item.latest_score)
        average = round(sum(item.latest_score for item in zone_analytics) / len(zone_analytics), 2)
        rising = [item.zone_id for item in zone_analytics if item.trend == "rising"]
        return {
            "zone_count": len(zone_analytics),
            "average_score": average,
            "rising_zones": rising,
            "highest_zone_id": highest.zone_id,
        }
