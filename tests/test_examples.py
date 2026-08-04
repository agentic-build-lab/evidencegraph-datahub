"""Frozen public evidence must remain complete and internally consistent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evidencegraph.models import ClosureReceipt, ClosureStatus, EvidenceLedger, ValidationStatus

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def test_example_manifest_hashes_every_public_file() -> None:
    manifest = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))
    indexed = {item["path"]: item["sha256"] for item in manifest["files"]}
    actual = {
        path.relative_to(EXAMPLES).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in EXAMPLES.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }

    assert indexed == actual


def test_flagship_public_claims_match_the_frozen_ledger() -> None:
    ledger = EvidenceLedger.model_validate_json(
        (EXAMPLES / "flagship/evidence-ledger.live.sanitized.json").read_text(
            encoding="utf-8"
        )
    )
    retry = json.loads(
        (EXAMPLES / "flagship/writeback-retry-receipts.json").read_text(encoding="utf-8")
    )

    assert len(ledger.impacts) == 7
    assert len(ledger.artifacts) == 9
    assert len(ledger.validations) == 14
    assert all(item.status == ValidationStatus.PASSED for item in ledger.validations)
    assert len(ledger.mutation_receipts) == 3
    assert all(item.status == "applied_verified" for item in ledger.mutation_receipts)
    assert len(retry) == 3
    assert {item["status"] for item in retry} == {"skipped_idempotent_verified"}


def test_refusal_and_closure_examples_prove_opposite_policy_outcomes() -> None:
    refusal = EvidenceLedger.model_validate_json(
        (EXAMPLES / "refusal/incomplete-lineage-ledger.json").read_text(encoding="utf-8")
    )
    closure = ClosureReceipt.model_validate_json(
        (EXAMPLES / "closure/closure-receipt.json").read_text(encoding="utf-8")
    )

    assert refusal.safety_decision.may_propose_writeback is False
    assert refusal.safety_decision.may_execute_writeback is False
    assert closure.status == ClosureStatus.CLOSED
    assert closure.remaining_impact_urns == ()
