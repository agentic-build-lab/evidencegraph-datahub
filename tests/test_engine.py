from evidencegraph.engine import ImpactEngine
from evidencegraph.models import ChangeRequest, ContextSnapshot, RiskLevel


def test_field_aware_blast_radius_reaches_bi_and_ml(
    change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    impacts = ImpactEngine().analyze(change, snapshot)

    assert len(impacts) == 7
    by_name = {impact.asset_name: impact for impact in impacts}
    assert by_name["Executive Revenue Watch"].affected_fields == ("revenue_by_customer_tier",)
    assert by_name["churn-api-prod"].paths[0][-1].startswith("urn:li:mlModelDeployment:")
    assert by_name["customer_tier_signal"].risk_level == RiskLevel.BLOCKER


def test_unrelated_field_does_not_follow_column_lineage(
    change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    unrelated_change = change.model_copy(update={"field": "ordered_at"})

    impacts = ImpactEngine().analyze(unrelated_change, snapshot)

    assert impacts == ()
