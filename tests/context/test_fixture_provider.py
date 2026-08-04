"""Focused behavior tests for the provider-neutral fixture adapter."""

from __future__ import annotations

import pytest

from evidencegraph.context import FixtureContextProvider, WriteDisabledError


@pytest.mark.asyncio
async def test_read_operations_share_a_typed_interface() -> None:
    provider = FixtureContextProvider(
        {
            "search": ({"searchResults": [{"entity": "orders"}]},),
            "get_entities": ([{"urn": "urn:li:dataset:orders"}],),
            "list_schema_fields": ({"fields": [{"fieldPath": "customer_id"}]},),
        }
    )

    search = await provider.search("orders", num_results=5)
    entities = await provider.get_entities(["urn:li:dataset:orders"])
    fields = await provider.list_schema_fields("urn:li:dataset:orders", limit=20)

    assert search.data == {"searchResults": [{"entity": "orders"}]}
    assert entities.data == [{"urn": "urn:li:dataset:orders"}]
    assert fields.data == {"fields": [{"fieldPath": "customer_id"}]}
    assert [call.tool for call in provider.calls] == [
        "search",
        "get_entities",
        "list_schema_fields",
    ]
    assert provider.calls[0].arguments == {
        "query": "orders",
        "num_results": 5,
        "sort_order": "desc",
        "offset": 0,
    }


@pytest.mark.asyncio
async def test_lineage_paginates_by_returned_count_until_exhausted() -> None:
    provider = FixtureContextProvider(
        {
            "get_lineage": (
                {
                    "downstreams": {
                        "searchResults": [{"urn": "urn:li:dataset:b"}],
                        "returned": 1,
                        "hasMore": True,
                        "truncatedDueToTokenBudget": True,
                    }
                },
                {
                    "downstreams": {
                        "searchResults": [{"urn": "urn:li:dataset:c"}],
                        "returned": 1,
                        "hasMore": False,
                    }
                },
            )
        }
    )

    result = await provider.get_lineage("urn:li:dataset:a", page_size=30)

    assert result.complete is True
    assert result.stop_reason == "exhausted"
    assert result.next_offset == 2
    assert result.token_budgeted is True
    assert len(result.pages) == 2
    assert [call.arguments["offset"] for call in provider.calls] == [0, 1]
    assert all(call.arguments["upstream"] is False for call in provider.calls)


@pytest.mark.asyncio
async def test_lineage_refuses_to_claim_completeness_without_progress() -> None:
    provider = FixtureContextProvider(
        {"get_lineage": ({"downstreams": {"returned": 0, "hasMore": True}},)}
    )

    result = await provider.get_lineage("urn:li:dataset:a")

    assert result.complete is False
    assert result.stop_reason == "no_pagination_progress"
    assert result.next_offset == 0


@pytest.mark.asyncio
async def test_mutations_default_to_dry_run_and_require_both_gates() -> None:
    provider = FixtureContextProvider({})

    proposal = await provider.add_tags(["urn:li:tag:breaking-change"], ["urn:li:dataset:orders"])

    assert proposal.dry_run is True
    assert proposal.applied is False
    assert proposal.result is None
    assert provider.calls == []
    with pytest.raises(WriteDisabledError):
        await provider.update_description(
            "urn:li:dataset:orders", "Migration required.", dry_run=False
        )


@pytest.mark.asyncio
async def test_allowlisted_live_mutation_returns_normalized_receipt() -> None:
    provider = FixtureContextProvider(
        {"save_document": ({"success": True, "urn": "urn:li:document:evidence"},)},
        writes_enabled=True,
    )

    receipt = await provider.save_document(
        "Analysis", "Blast radius", "Validated impact report", dry_run=False
    )

    assert receipt.applied is True
    assert receipt.dry_run is False
    assert receipt.result is not None
    assert receipt.result.data == {"success": True, "urn": "urn:li:document:evidence"}
    assert [call.tool for call in provider.calls] == ["save_document"]


@pytest.mark.asyncio
async def test_application_level_mutation_failure_is_not_marked_applied() -> None:
    provider = FixtureContextProvider(
        {"save_document": ({"success": False, "message": "readback rejected"},)},
        writes_enabled=True,
    )

    receipt = await provider.save_document(
        "Analysis", "Blast radius", "Validated impact report", dry_run=False
    )

    assert receipt.applied is False
    assert receipt.result is not None
    assert receipt.result.is_error is False
