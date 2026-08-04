"""Fresh-graph closure must reject stale or unresolved context."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from evidencegraph.closure import REQUIRED_CLOSURE_VALIDATIONS, verify_fresh_graph_closure
from evidencegraph.models import (
    ChangeRequest,
    ClosureStatus,
    ContextSnapshot,
    ValidationResult,
    ValidationStatus,
)
from evidencegraph.orchestrator import load_snapshot

ROOT = Path(__file__).resolve().parents[1]


def passing_validations() -> tuple[ValidationResult, ...]:
    return tuple(
        ValidationResult(
            validation_id=validation_id,
            name=validation_id,
            status=ValidationStatus.PASSED,
            details="Fixture validator passed.",
            output_sha256="a" * 64,
        )
        for validation_id in sorted(REQUIRED_CLOSURE_VALIDATIONS)
    )


def test_fresh_graph_closes_only_after_reingestion(change: ChangeRequest) -> None:
    receipt = verify_fresh_graph_closure(
        change,
        load_snapshot(ROOT / "fixtures/platform.json"),
        load_snapshot(ROOT / "fixtures/platform_after.json"),
        passing_validations(),
        patch_sha256="b" * 64,
        applied_at=datetime(2026, 8, 3, 12, 30, tzinfo=UTC),
    )

    assert receipt.status == ClosureStatus.CLOSED
    assert receipt.remaining_impact_urns == ()
    assert receipt.oldest_after_observation_at == datetime(2026, 8, 3, 13, 0, tzinfo=UTC)


def test_stale_graph_and_remaining_consumers_refuse_closure(
    change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    applied_at = max(item.observed_at for item in snapshot.observations) + timedelta(minutes=1)

    receipt = verify_fresh_graph_closure(
        change,
        snapshot,
        snapshot,
        passing_validations(),
        patch_sha256="b" * 64,
        applied_at=applied_at,
    )

    assert receipt.status == ClosureStatus.REFUSED
    assert len(receipt.remaining_impact_urns) == 7
    assert "stale" in " ".join(receipt.reasons).lower()


def test_missing_native_validator_refuses_closure(change: ChangeRequest) -> None:
    receipt = verify_fresh_graph_closure(
        change,
        load_snapshot(ROOT / "fixtures/platform.json"),
        load_snapshot(ROOT / "fixtures/platform_after.json"),
        passing_validations()[:-1],
        patch_sha256="b" * 64,
        applied_at=datetime(2026, 8, 3, 12, 30, tzinfo=UTC),
    )

    assert receipt.status == ClosureStatus.REFUSED
    assert "validator" in " ".join(receipt.reasons).lower()
