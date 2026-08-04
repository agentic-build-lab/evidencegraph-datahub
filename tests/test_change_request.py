"""Trust-boundary tests for breaking-change proposal intake."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evidencegraph.models import ChangeKind, ChangeRequest


def valid_payload() -> dict[str, object]:
    return {
        "change_id": "EG-TEST",
        "asset_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,orders,PROD)",
        "kind": ChangeKind.DROP_COLUMN,
        "field": "customer_tier",
        "requested_by": "urn:li:corpuser:test",
        "reason": "Exercise the proposal trust boundary.",
        "proposal_revision": "rev-test-1",
        "before_contract": {"required_fields": ["order_id", "customer_tier"]},
        "after_contract": {"required_fields": ["order_id", "segment_code"]},
    }


@pytest.mark.parametrize("key", ["change_id", "asset_urn", "requested_by", "reason"])
def test_required_identifiers_reject_empty_strings(key: str) -> None:
    payload = valid_payload()
    payload[key] = "  "

    with pytest.raises(ValidationError):
        ChangeRequest.model_validate(payload)


def test_column_change_requires_field_even_when_default_would_be_none() -> None:
    payload = valid_payload()
    payload.pop("field")

    with pytest.raises(ValidationError, match="field is required"):
        ChangeRequest.model_validate(payload)


def test_rename_and_type_change_require_their_targets() -> None:
    rename = valid_payload() | {"kind": ChangeKind.RENAME_COLUMN}
    type_change = valid_payload() | {"kind": ChangeKind.CHANGE_TYPE}

    with pytest.raises(ValidationError, match="proposed_field"):
        ChangeRequest.model_validate(rename)
    with pytest.raises(ValidationError, match="proposed_type"):
        ChangeRequest.model_validate(type_change)


def test_drop_column_requires_coherent_before_and_after_contracts() -> None:
    missing_before = valid_payload() | {"before_contract": {"required_fields": ["order_id"]}}
    stale_after = valid_payload() | {
        "after_contract": {"required_fields": ["order_id", "customer_tier"]}
    }

    with pytest.raises(ValidationError, match="before_contract"):
        ChangeRequest.model_validate(missing_before)
    with pytest.raises(ValidationError, match="after_contract"):
        ChangeRequest.model_validate(stale_after)
