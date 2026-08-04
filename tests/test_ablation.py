from pathlib import Path

from evidencegraph.ablation import EvaluationClass, load_truth_manifest, run_ablation
from evidencegraph.models import ChangeRequest, ContextSnapshot

ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = ROOT / "fixtures/truth_manifest.json"


def test_truth_manifest_is_frozen_and_covers_repository_bi_and_ml() -> None:
    truth = load_truth_manifest(TRUTH_PATH)

    assert len(truth.affected_assets) == 7
    assert len(truth.urns(EvaluationClass.REPOSITORY)) == 3
    assert len(truth.urns(EvaluationClass.BI)) == 1
    assert len(truth.urns(EvaluationClass.ML)) == 3


def test_datahub_reaches_independent_truth_and_repo_only_misses_bi_and_ml(
    change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    truth = load_truth_manifest(TRUTH_PATH)

    result = run_ablation(change, snapshot, truth)

    assert result.truth_assets == 7
    assert result.datahub.true_positives == 7
    assert result.datahub.false_positives == 0
    assert result.datahub.false_negatives == 0
    assert result.datahub.recall_percent == 100.0
    assert result.datahub.bi_recall_percent == 100.0
    assert result.datahub.ml_recall_percent == 100.0
    assert result.datahub.false_safe is False

    assert result.repository_only.true_positives == 3
    assert result.repository_only.false_positives == 0
    assert result.repository_only.false_negatives == 4
    assert result.repository_only.recall_percent == 42.9
    assert result.repository_only.bi_recall_percent == 0.0
    assert result.repository_only.ml_recall_percent == 0.0
    assert result.repository_only.false_safe is True
    assert result.recall_delta_percentage_points == 57.1
    assert len(result.additional_truth_assets_found_with_datahub) == 4

    missed = set(result.repository_only.missed_urns)
    assert truth.urns(EvaluationClass.BI) <= missed
    assert truth.urns(EvaluationClass.ML) <= missed


def test_truth_manifest_detects_a_datahub_false_safe_regression(
    change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    truth = load_truth_manifest(TRUTH_PATH)
    deployment_urn = next(
        iter(
            truth.urns(EvaluationClass.ML)
            - {
                "urn:li:mlFeature:(customer_profile,customer_tier_signal)",
                "urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)",
            }
        )
    )
    regressed = snapshot.model_copy(
        update={
            "lineage": tuple(
                edge for edge in snapshot.lineage if edge.downstream_urn != deployment_urn
            )
        }
    )

    result = run_ablation(change, regressed, truth)

    assert result.datahub.true_positives == 6
    assert result.datahub.false_positives == 0
    assert result.datahub.false_negatives == 1
    assert result.datahub.recall_percent == 85.7
    assert result.datahub.ml_recall_percent == 66.7
    assert result.datahub.false_safe is True
    assert result.datahub.missed_urns == (deployment_urn,)
