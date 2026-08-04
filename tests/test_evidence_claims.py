"""Claim-level provenance contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evidencegraph.models import ClaimStatus, EvidenceClaim


def test_observed_claim_requires_observation() -> None:
    with pytest.raises(ValidationError, match="source observation"):
        EvidenceClaim(
            claim_id="CLM-TEST",
            statement="A fact was observed.",
            predicate="test_fact",
            value=True,
            status=ClaimStatus.OBSERVED,
            confidence=1.0,
        )


def test_derived_claim_requires_source_and_rule() -> None:
    with pytest.raises(ValidationError, match="observations and a derivation"):
        EvidenceClaim(
            claim_id="CLM-TEST",
            statement="A fact was derived.",
            predicate="test_fact",
            value=True,
            status=ClaimStatus.DERIVED,
            confidence=1.0,
            source_observation_ids=("OBS-1",),
        )


def test_uncertainty_states_serialize_distinctly() -> None:
    values = {
        EvidenceClaim(
            claim_id=f"CLM-{status.value}",
            statement=f"State is {status.value}.",
            predicate="evidence_state",
            value=status.value,
            status=status,
            confidence=1.0,
            derivation="Fixture state injection.",
        ).model_dump(mode="json")["status"]
        for status in (
            ClaimStatus.ABSENT,
            ClaimStatus.NOT_QUERIED,
            ClaimStatus.READ_FAILED,
            ClaimStatus.INCOMPLETE,
            ClaimStatus.UNSUPPORTED,
        )
    }

    assert values == {"absent", "not_queried", "read_failed", "incomplete", "unsupported"}
