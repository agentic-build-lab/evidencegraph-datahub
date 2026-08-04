"""Evidence-linked migration planning and claim construction."""

from __future__ import annotations

import hashlib

from evidencegraph.models import (
    AssetKind,
    ChangeRequest,
    ClaimStatus,
    ContextSnapshot,
    EvidenceClaim,
    Impact,
    MigrationStep,
)


def build_claims(
    change: ChangeRequest,
    snapshot: ContextSnapshot,
    impacts: tuple[Impact, ...],
) -> tuple[EvidenceClaim, ...]:
    observations = {item.observation_id: item for item in snapshot.observations}
    claims: list[EvidenceClaim] = []
    for index, impact in enumerate(impacts, start=1):
        fields = ", ".join(impact.affected_fields) or "table-level dependency"
        claims.append(
            EvidenceClaim(
                claim_id=f"CLM-{index:03d}",
                statement=(
                    f"{impact.asset_name} is downstream of {change.asset_urn} and is affected "
                    f"through {fields}."
                ),
                subject_urn=impact.asset_urn,
                predicate="is_downstream_and_affected",
                value={
                    "producer_urn": change.asset_urn,
                    "affected_fields": list(impact.affected_fields),
                    "path_count": len(impact.paths),
                },
                status=ClaimStatus.DERIVED,
                confidence=1.0 if snapshot.completeness.is_complete else 0.65,
                source_observation_ids=impact.source_observation_ids,
                observed_at=max(
                    (
                        observations[item].observed_at
                        for item in impact.source_observation_ids
                        if item in observations
                    ),
                    default=None,
                ),
                derivation=(
                    "Deterministic field-aware breadth-first traversal over DataHub lineage."
                ),
            )
        )
    if snapshot.completeness.is_complete:
        claims.append(
            EvidenceClaim(
                claim_id="CLM-COMPLETE",
                statement="The requested downstream frontier and all pagination were exhausted.",
                predicate="lineage_frontier_complete",
                value=True,
                status=ClaimStatus.OBSERVED,
                confidence=1.0,
                source_observation_ids=tuple(
                    observation.observation_id
                    for observation in snapshot.observations
                    if observation.operation == "get_lineage"
                ),
                observed_at=max(
                    (
                        observation.observed_at
                        for observation in snapshot.observations
                        if observation.operation == "get_lineage"
                    ),
                    default=None,
                ),
            )
        )
    else:
        claims.append(
            EvidenceClaim(
                claim_id="CLM-INCOMPLETE",
                statement=(
                    "The available context cannot prove that the downstream blast radius is "
                    "complete."
                ),
                predicate="lineage_frontier_complete",
                value=False,
                status=ClaimStatus.INCOMPLETE,
                confidence=1.0,
                source_observation_ids=(),
                derivation="One or more completeness invariants failed.",
                unresolved_risks=("Downstream blast-radius completeness is unestablished.",),
            )
        )
    return tuple(claims)


def build_migration_plan(
    change: ChangeRequest,
    impacts: tuple[Impact, ...],
    claims: tuple[EvidenceClaim, ...],
) -> tuple[MigrationStep, ...]:
    claim_by_urn = {claim.subject_urn: claim.claim_id for claim in claims if claim.subject_urn}
    ordered_groups = (
        (
            "Preserve the producer contract",
            {AssetKind.DATASET, AssetKind.DATA_JOB, AssetKind.PIPELINE},
            (
                "Introduce a compatibility projection and update transformations before the "
                "source change."
            ),
        ),
        (
            "Protect analytics consumers",
            {AssetKind.DASHBOARD, AssetKind.CHART},
            "Migrate metrics and dashboard fields, then run semantic validation queries.",
        ),
        (
            "Protect ML consumers",
            {
                AssetKind.ML_FEATURE,
                AssetKind.ML_FEATURE_TABLE,
                AssetKind.ML_MODEL,
                AssetKind.ML_MODEL_DEPLOYMENT,
            },
            "Version the feature contract, verify parity, and gate model deployment on validation.",
        ),
    )
    steps: list[MigrationStep] = []
    order = 1
    for title, kinds, action in ordered_groups:
        affected = tuple(impact for impact in impacts if impact.kind in kinds)
        if not affected:
            continue
        urns = tuple(impact.asset_urn for impact in affected)
        owners = tuple(sorted({owner for impact in affected for owner in impact.owners}))
        evidence_ids = tuple(claim_by_urn[urn] for urn in urns if urn in claim_by_urn)
        steps.append(
            MigrationStep(
                step_id=f"STEP-{order:02d}",
                order=order,
                title=title,
                action=action,
                target_urns=urns,
                owner_urns=owners,
                blocking=any(impact.risk_score >= 75 for impact in affected),
                evidence_claim_ids=evidence_ids,
            )
        )
        order += 1
    steps.append(
        MigrationStep(
            step_id=f"STEP-{order:02d}",
            order=order,
            title="Re-query the fresh context graph",
            action=(
                "After applying the migration in an approved environment, re-run DataHub "
                "lineage and schema collection; close only when no unremediated consumer "
                "remains."
            ),
            target_urns=(change.asset_urn,),
            owner_urns=(),
            blocking=True,
            evidence_claim_ids=("CLM-COMPLETE",)
            if any(claim.claim_id == "CLM-COMPLETE" for claim in claims)
            else (),
        )
    )
    return tuple(steps)


def stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
