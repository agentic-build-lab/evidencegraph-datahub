"""Measure DataHub's operational value against an independent truth manifest."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import model_validator

from evidencegraph.engine import ImpactEngine
from evidencegraph.models import (
    AssetKind,
    ChangeRequest,
    Completeness,
    ContextSnapshot,
    StrictModel,
)


class EvaluationClass(StrEnum):
    """Independent truth-set groups used for domain-specific recall."""

    REPOSITORY = "repository"
    BI = "bi"
    ML = "ml"


class TruthAsset(StrictModel):
    """One expected affected asset, classified independently of agent output."""

    urn: str
    asset_kind: AssetKind
    evaluation_class: EvaluationClass


class TruthManifest(StrictModel):
    """Frozen expected blast radius for one versioned change proposal."""

    schema_version: str
    change_id: str
    source_urn: str
    affected_assets: tuple[TruthAsset, ...]

    @model_validator(mode="after")
    def validate_truth_universe(self) -> Self:
        urns = [asset.urn for asset in self.affected_assets]
        if not urns:
            raise ValueError("truth manifest must contain affected assets")
        if len(urns) != len(set(urns)):
            raise ValueError("truth manifest contains duplicate asset URNs")
        classes = {asset.evaluation_class for asset in self.affected_assets}
        missing = set(EvaluationClass).difference(classes)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"truth manifest is missing evaluation classes: {names}")
        return self

    def urns(self, evaluation_class: EvaluationClass | None = None) -> set[str]:
        return {
            asset.urn
            for asset in self.affected_assets
            if evaluation_class is None or asset.evaluation_class == evaluation_class
        }


@dataclass(frozen=True)
class AblationModeMetrics:
    """Exact detection quality for one context mode."""

    assets_found: int
    true_positives: int
    false_positives: int
    false_negatives: int
    recall_percent: float
    bi_recall_percent: float
    ml_recall_percent: float
    false_safe: bool
    missed_urns: tuple[str, ...]
    unexpected_urns: tuple[str, ...]


@dataclass(frozen=True)
class AblationResult:
    """Side-by-side measurements grounded in a frozen, independent truth set."""

    truth_assets: int
    datahub: AblationModeMetrics
    repository_only: AblationModeMetrics
    additional_truth_assets_found_with_datahub: tuple[str, ...]
    recall_delta_percentage_points: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_truth_manifest(path: Path) -> TruthManifest:
    """Load and strictly validate an independent affected-asset manifest."""

    return TruthManifest.model_validate_json(path.read_text(encoding="utf-8"))


def run_ablation(
    change: ChangeRequest,
    snapshot: ContextSnapshot,
    truth_manifest: TruthManifest,
) -> AblationResult:
    """Compare DataHub and repository-only discoveries against independent truth."""

    _validate_truth_grounding(change, snapshot, truth_manifest)
    repository_snapshot = _repository_only_snapshot(change, snapshot)
    engine = ImpactEngine()
    datahub_urns = {impact.asset_urn for impact in engine.analyze(change, snapshot)}
    repository_urns = {impact.asset_urn for impact in engine.analyze(change, repository_snapshot)}
    truth_urns = truth_manifest.urns()
    datahub_metrics = _score(datahub_urns, truth_manifest)
    repository_metrics = _score(repository_urns, truth_manifest)
    return AblationResult(
        truth_assets=len(truth_urns),
        datahub=datahub_metrics,
        repository_only=repository_metrics,
        additional_truth_assets_found_with_datahub=tuple(
            sorted((datahub_urns & truth_urns) - (repository_urns & truth_urns))
        ),
        recall_delta_percentage_points=round(
            datahub_metrics.recall_percent - repository_metrics.recall_percent,
            1,
        ),
    )


def _validate_truth_grounding(
    change: ChangeRequest,
    snapshot: ContextSnapshot,
    truth_manifest: TruthManifest,
) -> None:
    if truth_manifest.change_id != change.change_id:
        raise ValueError("truth manifest change_id does not match the proposal")
    if truth_manifest.source_urn != change.asset_urn:
        raise ValueError("truth manifest source_urn does not match the proposal")
    assets = snapshot.asset_map()
    defects = [
        asset.urn
        for asset in truth_manifest.affected_assets
        if asset.urn not in assets or assets[asset.urn].kind != asset.asset_kind
    ]
    if defects:
        raise ValueError(
            "truth manifest is not grounded in the supplied platform snapshot: "
            + ", ".join(sorted(defects))
        )


def _repository_only_snapshot(change: ChangeRequest, snapshot: ContextSnapshot) -> ContextSnapshot:
    repository_platforms = {"postgres", "dbt", "airflow"}
    repository_assets = tuple(
        asset for asset in snapshot.assets if asset.platform in repository_platforms
    )
    repository_urns = {asset.urn for asset in repository_assets}
    repository_lineage = tuple(
        edge
        for edge in snapshot.lineage
        if edge.upstream_urn in repository_urns and edge.downstream_urn in repository_urns
    )
    repository_observation_ids = {edge.source_observation_id for edge in repository_lineage}
    return ContextSnapshot(
        snapshot_id=f"{snapshot.snapshot_id}-repository-only",
        assets=repository_assets,
        lineage=repository_lineage,
        documents=(),
        observations=tuple(
            observation
            for observation in snapshot.observations
            if observation.observation_id in repository_observation_ids
            or observation.object_urn == change.asset_urn
        ),
        completeness=Completeness(
            requested_direction="downstream",
            requested_depth=snapshot.completeness.requested_depth,
            pages_exhausted=True,
            frontier_exhausted=True,
            truncated=False,
            unsupported_entities=(
                "BI and ML consumers are not represented in the repository dependency graph.",
            ),
            notes=("Repository-only analysis cannot observe external consumers.",),
        ),
    )


def _score(discovered_urns: set[str], truth_manifest: TruthManifest) -> AblationModeMetrics:
    truth_urns = truth_manifest.urns()
    true_positive_urns = discovered_urns & truth_urns
    false_positive_urns = discovered_urns - truth_urns
    false_negative_urns = truth_urns - discovered_urns
    return AblationModeMetrics(
        assets_found=len(discovered_urns),
        true_positives=len(true_positive_urns),
        false_positives=len(false_positive_urns),
        false_negatives=len(false_negative_urns),
        recall_percent=_recall(true_positive_urns, truth_urns),
        bi_recall_percent=_class_recall(discovered_urns, truth_manifest.urns(EvaluationClass.BI)),
        ml_recall_percent=_class_recall(discovered_urns, truth_manifest.urns(EvaluationClass.ML)),
        false_safe=bool(false_negative_urns),
        missed_urns=tuple(sorted(false_negative_urns)),
        unexpected_urns=tuple(sorted(false_positive_urns)),
    )


def _recall(true_positive_urns: set[str], truth_urns: set[str]) -> float:
    return round(len(true_positive_urns) / len(truth_urns) * 100.0, 1)


def _class_recall(discovered_urns: set[str], class_truth_urns: set[str]) -> float:
    return _recall(discovered_urns & class_truth_urns, class_truth_urns)
