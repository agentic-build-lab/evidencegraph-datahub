"""Fresh-graph closure gate for an applied data-change revision."""

from __future__ import annotations

from datetime import datetime

from evidencegraph.engine import ImpactEngine
from evidencegraph.models import (
    ChangeRequest,
    ClosureReceipt,
    ClosureStatus,
    ContextSnapshot,
    ValidationResult,
    ValidationStatus,
)

REQUIRED_CLOSURE_VALIDATIONS = frozenset(
    {
        "VAL-INTEGRITY",
        "VAL-PATCH-APPLY",
        "VAL-DUCKDB-PARITY",
        "VAL-DBT-BUILD",
        "VAL-AIRFLOW-DAG",
        "VAL-ML-PARITY",
    }
)


def verify_fresh_graph_closure(
    change: ChangeRequest,
    before: ContextSnapshot,
    after: ContextSnapshot,
    validations: tuple[ValidationResult, ...],
    *,
    patch_sha256: str,
    applied_at: datetime,
) -> ClosureReceipt:
    """Close only when a complete post-apply graph proves the old field has no consumers."""

    reasons: list[str] = []
    if before.snapshot_id == after.snapshot_id:
        reasons.append("The before and after snapshots are identical; re-ingestion is unproven.")
    if not patch_sha256.strip():
        reasons.append("The applied migration revision has no patch digest.")
    if not after.completeness.is_complete:
        reasons.append("The post-migration DataHub graph is incomplete.")

    after_times = tuple(item.observed_at for item in after.observations)
    oldest = min(after_times, default=None)
    newest = max(after_times, default=None)
    if oldest is None or oldest <= applied_at:
        reasons.append("The post-migration graph contains stale or missing observations.")

    before_source = before.asset_map().get(change.asset_urn)
    after_source = after.asset_map().get(change.asset_urn)
    if before_source is None or after_source is None:
        reasons.append("The producer is absent from a closure snapshot.")
    elif change.field is not None:
        if change.field not in {field.name for field in before_source.schema_fields}:
            reasons.append("The before snapshot does not establish the changed source field.")
        if change.field in {field.name for field in after_source.schema_fields}:
            reasons.append("The removed source field is still present after re-ingestion.")
        after_required = (
            set(after_source.contract.required_fields)
            if after_source.contract is not None
            else set()
        )
        requested_required = set(change.after_contract.get("required_fields", []))
        if after_required != requested_required:
            reasons.append(
                "The re-ingested producer contract does not match the approved revision."
            )

    nonpassing = tuple(item for item in validations if item.status != ValidationStatus.PASSED)
    observed_validation_ids = {item.validation_id for item in validations}
    missing_validations = REQUIRED_CLOSURE_VALIDATIONS.difference(observed_validation_ids)
    if nonpassing or missing_validations:
        reasons.append("Every required migration validator must pass before graph closure.")

    remaining = ImpactEngine().analyze(change, after)
    if remaining:
        reasons.append(
            f"The fresh graph still exposes {len(remaining)} downstream consumer(s) "
            "of the old field."
        )

    return ClosureReceipt(
        change_id=change.change_id,
        proposal_revision=change.proposal_revision,
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        patch_sha256=patch_sha256,
        applied_at=applied_at,
        oldest_after_observation_at=oldest,
        newest_after_observation_at=newest,
        remaining_impact_urns=tuple(item.asset_urn for item in remaining),
        validation_ids=tuple(item.validation_id for item in validations),
        status=ClosureStatus.CLOSED if not reasons else ClosureStatus.REFUSED,
        reasons=tuple(
            reasons or ("Fresh DataHub context proves the approved revision is closed.",)
        ),
    )
