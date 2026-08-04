"""Reject executable content derived from untrusted DataHub document facts."""

from __future__ import annotations

from pathlib import Path

import pytest

from evidencegraph.models import ChangeRequest, ContextSnapshot
from evidencegraph.orchestrator import EvidenceGraphAgent

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("facts_update", "expected"),
    [
        ({"replacement_field": "segment_code; DROP TABLE customers"}, "safe SQL identifier"),
        ({"replacement_field": "{{ env_var('TOKEN') }}"}, "safe SQL identifier"),
        ({"mapping": {"B": "bronze' || secret", "S": "silver", "G": "gold"}}, "B/S/G"),
        ({"unknown_policy": "coerce"}, "fail closed"),
        ({"approved_by": "urn:li:corpGroup:attacker"}, "No approved DataHub migration"),
    ],
)
def test_untrusted_document_facts_block_artifact_generation(
    tmp_path: Path,
    change: ChangeRequest,
    snapshot: ContextSnapshot,
    facts_update: dict[str, object],
    expected: str,
) -> None:
    original = snapshot.documents[0]
    poisoned = original.model_copy(update={"facts": original.facts | facts_update})
    unsafe_snapshot = snapshot.model_copy(update={"documents": (poisoned,)})

    ledger, _ = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql").run(
        change,
        unsafe_snapshot,
        output_root=tmp_path,
    )

    assert ledger.artifacts == ()
    assert ledger.validations == ()
    assert ledger.safety_decision.may_generate is False
    assert ledger.safety_decision.may_propose_writeback is False
    assert expected in " ".join(ledger.safety_decision.reasons)
