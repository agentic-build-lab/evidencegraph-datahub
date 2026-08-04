"""Security boundary tests for live DataHub metadata write-back."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import pytest

from evidencegraph.context import FixtureContextProvider
from evidencegraph.engine import ImpactEngine
from evidencegraph.models import ChangeRequest, ContextSnapshot, WritebackProposal
from evidencegraph.planner import build_claims
from evidencegraph.writeback import (
    DEFAULT_WRITE_SCOPE_TAG,
    MAX_MUTATION_TARGETS,
    LiveWritebackError,
    build_writeback_proposals,
    execute_writeback_proposals,
)

REVIEW_TAG = "urn:li:tag:EvidenceGraphReviewRequired"
SOURCE_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)"
SECOND_URN = "urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.stg_orders,PROD)"
RUN_ID = "EG-SECURITYTEST"
DOCUMENT_TITLE = f"EvidenceGraph EG-042 evidence ledger ({RUN_ID})"
OWNERSHIP_MARKER = hashlib.sha256(
    f"evidencegraph:{RUN_ID}:{SOURCE_URN}".encode()
).hexdigest()


def _digest(targets: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(targets)).encode()).hexdigest()


def _idempotency(tool: str, arguments: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"run_id": RUN_ID, "tool": tool, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _entity(urn: str, *tags: str, description: str | None = None) -> dict[str, Any]:
    entity: dict[str, Any] = {
        "urn": urn,
        "tags": {"tags": [{"tag": {"urn": tag}} for tag in tags]},
    }
    if description is not None:
        entity["properties"] = {"description": description}
    return entity


def _document(urn: str, title: str, content: str) -> dict[str, Any]:
    return {
        "urn": urn,
        "info": {"title": title},
        "contents": {"text": content},
    }


def _tag_proposal(
    targets: list[str],
    *,
    digest: str | None = None,
    scope_tag: str = DEFAULT_WRITE_SCOPE_TAG,
    requires_human_approval: bool = True,
    tag_urns: list[str] | None = None,
    proposal_id: str = "WB-TAG",
    idempotency_key: str | None = None,
) -> WritebackProposal:
    arguments = {
        "entity_urns": targets,
        "tag_urns": tag_urns if tag_urns is not None else [REVIEW_TAG],
        "scope_tag_urn": scope_tag,
        "target_set_sha256": digest if digest is not None else _digest(targets),
    }
    return WritebackProposal(
        proposal_id=proposal_id,
        tool="add_tags",
        arguments=arguments,
        purpose="Security test",
        idempotency_key=idempotency_key or _idempotency("add_tags", arguments),
        requires_human_approval=requires_human_approval,
    )


def _document_proposal() -> WritebackProposal:
    arguments = {
        "document_type": "Analysis",
        "title": DOCUMENT_TITLE,
        "content": (
            "# EvidenceGraph evidence ledger -- EG-042\n\n"
            f"Run: `{RUN_ID}`\n"
            f"Producer: `{SOURCE_URN}`\n"
            f"EvidenceGraph ownership marker: `{OWNERSHIP_MARKER}`"
        ),
        "related_assets": [SOURCE_URN],
        "referenced_assets": [SOURCE_URN],
        "lookup_key": RUN_ID,
        "ownership_marker": OWNERSHIP_MARKER,
        "scope_tag_urn": DEFAULT_WRITE_SCOPE_TAG,
        "target_set_sha256": _digest([SOURCE_URN]),
    }
    return WritebackProposal(
        proposal_id="WB-DOCUMENT",
        tool="save_document",
        arguments=arguments,
        purpose="Security test",
        idempotency_key=_idempotency("save_document", arguments),
    )


def _description_proposal() -> WritebackProposal:
    arguments = {
        "entity_urn": SOURCE_URN,
        "operation": "append",
        "description": (
            "\n\n### EvidenceGraph change assurance -- EG-042\n"
            f"Run `{RUN_ID}` found 7 downstream assets. "
            "See the saved EvidenceGraph document for claims and validation receipts.\n\n"
            f"EvidenceGraph assurance marker: `{RUN_ID}`"
        ),
        "scope_tag_urn": DEFAULT_WRITE_SCOPE_TAG,
        "target_set_sha256": _digest([SOURCE_URN]),
    }
    return WritebackProposal(
        proposal_id="WB-DESCRIPTION",
        tool="update_description",
        arguments=arguments,
        purpose="Security test",
        idempotency_key=_idempotency("update_description", arguments),
    )


def test_builder_binds_every_proposal_to_an_approved_target_set(
    change: ChangeRequest,
    snapshot: ContextSnapshot,
) -> None:
    impacts = ImpactEngine().analyze(change, snapshot)
    claims = build_claims(change, snapshot, impacts)

    proposals = build_writeback_proposals(RUN_ID, change, impacts, claims, ())

    assert all(proposal.requires_human_approval for proposal in proposals)
    for proposal in proposals:
        arguments = proposal.arguments
        if proposal.tool == "add_tags":
            targets = arguments["entity_urns"]
        elif proposal.tool == "update_description":
            targets = [arguments["entity_urn"]]
        else:
            targets = arguments["related_assets"]
        assert isinstance(targets, list)
        assert arguments["scope_tag_urn"] == DEFAULT_WRITE_SCOPE_TAG
        assert arguments["target_set_sha256"] == _digest(targets)


@pytest.mark.asyncio
async def test_tampered_idempotency_key_is_rejected_before_provider_call() -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _tag_proposal([SOURCE_URN], idempotency_key="0" * 64)

    with pytest.raises(LiveWritebackError, match="idempotency key"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tag_urns",
    (["urn:li:tag:Other"], [REVIEW_TAG, "urn:li:tag:Other"]),
)
async def test_tag_writeback_rejects_non_review_or_multiple_tags_before_provider_call(
    tag_urns: list[str],
) -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _tag_proposal([SOURCE_URN], tag_urns=tag_urns)

    with pytest.raises(LiveWritebackError, match="only the review-required tag"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_description_writeback_rejects_replace_before_provider_call() -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _description_proposal()
    arguments = {**proposal.arguments, "operation": "replace"}
    proposal = proposal.model_copy(
        update={
            "arguments": arguments,
            "idempotency_key": _idempotency("update_description", arguments),
        }
    )

    with pytest.raises(LiveWritebackError, match="must use append"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_description_rejects_bad_marker_before_provider_call() -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _description_proposal()
    arguments = {
        **proposal.arguments,
        "description": "Unbounded replacement text without an EvidenceGraph marker.",
    }
    proposal = proposal.model_copy(
        update={
            "arguments": arguments,
            "idempotency_key": _idempotency("update_description", arguments),
        }
    )

    with pytest.raises(LiveWritebackError, match="bounded assurance marker"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_document_rejects_bad_ownership_marker_before_provider_call() -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _document_proposal()
    arguments = {
        **proposal.arguments,
        "content": (
            "# EvidenceGraph evidence ledger -- EG-042\n\n"
            f"Run: `{RUN_ID}`\nProducer: `{SOURCE_URN}`\nTampered content"
        ),
    }
    proposal = proposal.model_copy(
        update={
            "arguments": arguments,
            "idempotency_key": _idempotency("save_document", arguments),
        }
    )

    with pytest.raises(LiveWritebackError, match="canonical ownership marker"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_proposal_id_must_match_tool_schema_before_provider_call() -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _tag_proposal([SOURCE_URN], proposal_id="WB-DOCUMENT")

    with pytest.raises(LiveWritebackError, match="proposal id"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )

    assert provider.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("approval_granted", "requires_human_approval", "message"),
    (
        (False, True, "explicit approval is required"),
        (True, False, "must be marked as requiring explicit approval"),
    ),
)
async def test_live_writeback_cannot_bypass_required_approval(
    approval_granted: bool,
    requires_human_approval: bool,
    message: str,
) -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)
    proposal = _tag_proposal(
        [SOURCE_URN],
        requires_human_approval=requires_human_approval,
    )

    with pytest.raises(LiveWritebackError, match=message):
        await execute_writeback_proposals(
            provider,
            [proposal],
            run_id=RUN_ID,
            approval_granted=approval_granted,
        )

    assert provider.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("targets", "digest", "message"),
    (
        ([SOURCE_URN, SOURCE_URN], None, "duplicated or exceeds"),
        (
            [f"urn:li:dataset:security-{index}" for index in range(MAX_MUTATION_TARGETS + 1)],
            None,
            "duplicated or exceeds",
        ),
        ([SOURCE_URN], "0" * 64, "digest does not match"),
    ),
)
async def test_target_set_shape_and_digest_fail_before_any_provider_call(
    targets: list[str],
    digest: str | None,
    message: str,
) -> None:
    provider = FixtureContextProvider({}, writes_enabled=True)

    with pytest.raises(LiveWritebackError, match=message):
        await execute_writeback_proposals(
            provider,
            [_tag_proposal(targets, digest=digest)],
            run_id=RUN_ID,
            approval_granted=True,
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_scope_policy_and_observed_scope_both_gate_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVIDENCEGRAPH_WRITE_SCOPE_TAG", "urn:li:tag:ApprovedSandbox")
    provider = FixtureContextProvider({}, writes_enabled=True)

    with pytest.raises(LiveWritebackError, match="scope tag does not match"):
        await execute_writeback_proposals(
            provider,
            [_tag_proposal([SOURCE_URN])],
            run_id=RUN_ID,
            approval_granted=True,
        )
    assert provider.calls == []

    provider = FixtureContextProvider(
        {"get_entities": ({"result": [_entity(SOURCE_URN)]},)},
        writes_enabled=True,
    )
    proposal = _tag_proposal([SOURCE_URN], scope_tag="urn:li:tag:ApprovedSandbox")
    with pytest.raises(LiveWritebackError, match="outside the configured write scope"):
        await execute_writeback_proposals(
            provider, [proposal], run_id=RUN_ID, approval_granted=True
        )
    assert [call.tool for call in provider.calls] == ["get_entities"]


@pytest.mark.asyncio
async def test_tag_writeback_rejects_partial_per_target_readback() -> None:
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {
                    "result": [
                        _entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG),
                        _entity(SECOND_URN, DEFAULT_WRITE_SCOPE_TAG),
                    ]
                },
                {
                    "result": [
                        _entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG, REVIEW_TAG),
                        _entity(SECOND_URN, DEFAULT_WRITE_SCOPE_TAG),
                    ]
                },
            ),
            "add_tags": ({"success": True},),
        },
        writes_enabled=True,
    )

    with pytest.raises(LiveWritebackError, match="failed readback for 1 target"):
        await execute_writeback_proposals(
            provider,
            [_tag_proposal([SOURCE_URN, SECOND_URN])],
            run_id=RUN_ID,
            approval_granted=True,
        )

    assert [call.tool for call in provider.calls] == [
        "get_entities",
        "add_tags",
        "get_entities",
    ]


@pytest.mark.asyncio
async def test_existing_tags_make_retry_a_verified_no_op() -> None:
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {
                    "result": [
                        _entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG, REVIEW_TAG),
                        _entity(SECOND_URN, DEFAULT_WRITE_SCOPE_TAG, REVIEW_TAG),
                    ]
                },
            ),
        },
        writes_enabled=True,
    )

    receipts = await execute_writeback_proposals(
        provider,
        [_tag_proposal([SOURCE_URN, SECOND_URN])],
        run_id=RUN_ID,
        approval_granted=True,
    )

    assert receipts[0].status == "skipped_idempotent_verified"
    assert [call.tool for call in provider.calls] == ["get_entities"]


@pytest.mark.asyncio
async def test_application_level_false_success_stops_before_readback() -> None:
    provider = FixtureContextProvider(
        {
            "get_entities": ({"result": [_entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG)]},),
            "add_tags": ({"success": False, "message": "policy rejected"},),
        },
        writes_enabled=True,
    )

    with pytest.raises(LiveWritebackError, match="MCP mutation failed"):
        await execute_writeback_proposals(
            provider,
            [_tag_proposal([SOURCE_URN])],
            run_id=RUN_ID,
            approval_granted=True,
        )

    assert [call.tool for call in provider.calls] == ["get_entities", "add_tags"]


@pytest.mark.asyncio
async def test_document_title_collision_does_not_overwrite_a_different_title() -> None:
    new_urn = "urn:li:document:evidencegraph-security-test"
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {"result": [_entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG)]},
                {"result": [_document(new_urn, DOCUMENT_TITLE, OWNERSHIP_MARKER)]},
            ),
            "search_documents": (
                {
                    "searchResults": [
                        {
                            "entity": _document(
                                "urn:li:document:human-authored",
                                "Human-authored incident review",
                                RUN_ID,
                            )
                        }
                    ]
                },
            ),
            "save_document": ({"success": True, "urn": new_urn},),
        },
        writes_enabled=True,
    )

    receipts = await execute_writeback_proposals(
        provider,
        [_document_proposal()],
        run_id=RUN_ID,
        approval_granted=True,
    )

    save_call = next(call for call in provider.calls if call.tool == "save_document")
    assert "urn" not in save_call.arguments
    assert receipts[0].target_urn == new_urn


@pytest.mark.asyncio
async def test_exact_document_title_without_marker_is_never_overwritten() -> None:
    existing_urn = "urn:li:document:title-collision"
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {"result": [_entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG)]},
                {"result": [_document(existing_urn, DOCUMENT_TITLE, "Human-authored content")]},
            ),
            "search_documents": (
                {
                    "searchResults": [
                        {"entity": _document(existing_urn, DOCUMENT_TITLE, "search result")}
                    ]
                },
                {"searchResults": []},
            ),
        },
        writes_enabled=True,
    )

    with pytest.raises(LiveWritebackError, match="exact EvidenceGraph marker"):
        await execute_writeback_proposals(
            provider,
            [_document_proposal()],
            run_id=RUN_ID,
            approval_granted=True,
        )

    assert "save_document" not in [call.tool for call in provider.calls]


@pytest.mark.asyncio
async def test_document_readback_requires_exact_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("evidencegraph.writeback.asyncio.sleep", no_sleep)
    new_urn = "urn:li:document:wrong-title"
    wrong_document = _document(new_urn, "Wrong title", f"marker {RUN_ID}")
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {"result": [_entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG)]},
                *({"result": [wrong_document]} for _ in range(4)),
            ),
            "search_documents": tuple({"searchResults": []} for _ in range(9)),
            "save_document": ({"success": True, "urn": new_urn},),
        },
        writes_enabled=True,
    )

    with pytest.raises(LiveWritebackError, match="did not pass post-write readback"):
        await execute_writeback_proposals(
            provider,
            [_document_proposal()],
            run_id=RUN_ID,
            approval_granted=True,
        )


@pytest.mark.asyncio
async def test_exact_owned_document_makes_retry_a_verified_no_op() -> None:
    existing_urn = "urn:li:document:owned-evidencegraph-document"
    exact_document = _document(existing_urn, DOCUMENT_TITLE, OWNERSHIP_MARKER)
    provider = FixtureContextProvider(
        {
            "get_entities": (
                {"result": [_entity(SOURCE_URN, DEFAULT_WRITE_SCOPE_TAG)]},
                {"result": [exact_document]},
            ),
            "search_documents": (
                {"searchResults": [{"entity": exact_document}]},
                {"searchResults": [{"entity": exact_document}]},
            ),
        },
        writes_enabled=True,
    )

    receipts = await execute_writeback_proposals(
        provider,
        [_document_proposal()],
        run_id=RUN_ID,
        approval_granted=True,
    )

    assert receipts[0].status == "skipped_idempotent_verified"
    assert "save_document" not in [call.tool for call in provider.calls]
