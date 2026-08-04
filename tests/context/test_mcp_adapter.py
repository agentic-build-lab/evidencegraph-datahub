"""Contract and normalization tests for the official MCP adapter."""

from __future__ import annotations

import json

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from evidencegraph.context.mcp import (
    DATAHUB_MCP_PACKAGE,
    DataHubMCPConfig,
    DataHubMCPContractError,
    normalize_mcp_result,
    validate_tool_contracts,
)


def _tool(name: str, *properties: str) -> Tool:
    return Tool(
        name=name,
        description=f"Fixture contract for {name}",
        inputSchema={
            "type": "object",
            "properties": {property_name: {} for property_name in properties},
        },
    )


def _read_tools() -> list[Tool]:
    return [
        _tool("search", "query", "num_results", "offset"),
        _tool("get_entities", "urns"),
        _tool("search_documents", "query", "num_results", "offset"),
        _tool("list_schema_fields", "urn", "limit", "offset"),
        _tool("get_lineage", "urn", "upstream", "max_results", "offset"),
    ]


def test_config_pins_official_package_and_hides_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "fixture-path")
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-leak")
    config = DataHubMCPConfig(
        gms_url="https://datahub.example:8080", token="top-secret", writes_enabled=False
    )

    parameters = config.server_parameters()

    assert parameters.command == "uvx"
    assert parameters.args == [DATAHUB_MCP_PACKAGE]
    assert parameters.env is not None
    assert parameters.env["PATH"] == "fixture-path"
    assert parameters.env["DATAHUB_GMS_TOKEN"] == "top-secret"
    assert parameters.env["TOOLS_IS_MUTATION_ENABLED"] == "false"
    assert "GITHUB_TOKEN" not in parameters.env
    assert "top-secret" not in repr(config)
    assert "top-secret" not in " ".join([parameters.command, *parameters.args])


@pytest.mark.parametrize(
    "url",
    ["http://datahub.example:8080", "ftp://localhost:8080", "http://user:pass@localhost:8080"],
)
def test_config_rejects_insecure_or_credentialed_urls(url: str) -> None:
    with pytest.raises(ValueError):
        DataHubMCPConfig(gms_url=url)


def test_contract_check_accepts_reads_but_requires_writes_when_enabled() -> None:
    tools = _read_tools()

    validate_tool_contracts(tools, writes_enabled=False)
    with pytest.raises(DataHubMCPContractError, match="missing tool add_tags"):
        validate_tool_contracts(tools, writes_enabled=True)

    tools.extend(
        [
            _tool("add_tags", "tag_urns", "entity_urns"),
            _tool("update_description", "entity_urn", "operation", "description"),
            _tool("save_document", "document_type", "title", "content"),
        ]
    )
    validate_tool_contracts(tools, writes_enabled=True)


def test_contract_check_rejects_schema_drift() -> None:
    tools = _read_tools()
    tools[4] = _tool("get_lineage", "urn", "upstream", "max_results")

    with pytest.raises(DataHubMCPContractError, match="missing properties: offset"):
        validate_tool_contracts(tools, writes_enabled=False)


def test_normalizer_prefers_structured_content_and_preserves_text() -> None:
    result = CallToolResult(
        content=[TextContent(type="text", text="human-readable fallback")],
        structuredContent={"success": True, "count": 2},
    )

    normalized = normalize_mcp_result("search", result)

    assert normalized.data == {"success": True, "count": 2}
    assert normalized.text == ("human-readable fallback",)
    assert normalized.is_error is False


def test_normalizer_decodes_json_text_and_keeps_tool_errors() -> None:
    payload = {"downstreams": {"returned": 0, "hasMore": False}}
    result = CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))], isError=True
    )

    normalized = normalize_mcp_result("get_lineage", result)

    assert normalized.data == payload
    assert normalized.is_error is True
