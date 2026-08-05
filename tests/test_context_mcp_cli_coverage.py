"""Focused fail-closed coverage for the MCP adapter and CLI orchestration."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
import typer
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, Tool

from evidencegraph import cli
from evidencegraph.context import mcp as mcp_adapter
from evidencegraph.context.mcp import (
    DataHubMCPConfig,
    DataHubMCPContractError,
    DataHubMCPError,
    DataHubMCPProvider,
)
from evidencegraph.models import MutationReceipt

ROOT = Path(__file__).resolve().parents[1]
FLAGSHIP_LEDGER = ROOT / "examples/flagship/evidence-ledger.live.sanitized.json"


def _tool(name: str, *properties: str) -> Tool:
    return Tool(
        name=name,
        description=f"Deterministic {name} fixture",
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


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"gms_url": ""}, "non-empty URL"),
        ({"gms_url": "localhost:8080"}, "absolute HTTP"),
        ({"gms_url": "https://localhost", "uvx_command": " "}, "uvx_command"),
        ({"gms_url": "https://localhost", "timeout_seconds": 0}, "positive finite"),
        ({"gms_url": "https://localhost", "timeout_seconds": math.inf}, "positive finite"),
        ({"gms_url": "https://localhost", "timeout_seconds": math.nan}, "positive finite"),
    ),
)
def test_mcp_config_rejects_unbounded_or_invalid_runtime_values(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        DataHubMCPConfig(**overrides)


def test_mcp_config_from_env_fails_closed_and_omits_absent_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATAHUB_GMS_URL", raising=False)
    monkeypatch.delenv("DATAHUB_GMS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="DATAHUB_GMS_URL is required"):
        DataHubMCPConfig.from_env()

    monkeypatch.setenv("DATAHUB_GMS_URL", "http://[::1]:8080")
    config = DataHubMCPConfig.from_env(writes_enabled=True)
    parameters = config.server_parameters()

    assert config.writes_enabled is True
    assert parameters.env is not None
    assert parameters.env["TOOLS_IS_MUTATION_ENABLED"] == "true"
    assert parameters.env["SAVE_DOCUMENT_TOOL_ENABLED"] == "true"
    assert "DATAHUB_GMS_TOKEN" not in parameters.env


def test_mcp_subprocess_environment_is_an_explicit_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "safe-path")
    monkeypatch.setenv("DATAHUB_GMS_TOKEN", "must-not-be-inherited")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-be-inherited")

    environment = mcp_adapter._minimal_subprocess_environment()

    assert environment["PATH"] == "safe-path"
    assert "DATAHUB_GMS_TOKEN" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment


@pytest.mark.asyncio
async def test_tool_discovery_collects_pages_and_rejects_cursor_cycles() -> None:
    class Session:
        def __init__(self, responses: list[SimpleNamespace]) -> None:
            self.responses = responses
            self.cursors: list[str | None] = []

        async def list_tools(self, *, cursor: str | None) -> SimpleNamespace:
            self.cursors.append(cursor)
            return self.responses.pop(0)

    paged = Session(
        [
            SimpleNamespace(tools=[_tool("search")], nextCursor="next"),
            SimpleNamespace(tools=[_tool("get_entities")], nextCursor=None),
        ]
    )
    tools = await mcp_adapter._list_all_tools(cast(ClientSession, paged))
    assert [tool.name for tool in tools] == ["search", "get_entities"]
    assert paged.cursors == [None, "next"]

    cyclic = Session(
        [
            SimpleNamespace(tools=[], nextCursor="repeat"),
            SimpleNamespace(tools=[], nextCursor="repeat"),
        ]
    )
    with pytest.raises(DataHubMCPContractError, match="repeated cursor"):
        await mcp_adapter._list_all_tools(cast(ClientSession, cyclic))


def test_tool_contract_reports_missing_and_non_object_schemas_together() -> None:
    tools = _read_tools()
    tools[0] = Tool(
        name="search",
        description="Schema without properties",
        inputSchema={"type": "object"},
    )
    tools.pop(1)

    with pytest.raises(DataHubMCPContractError) as captured:
        mcp_adapter.validate_tool_contracts(tools, writes_enabled=False)

    message = str(captured.value)
    assert "tool search has no object properties" in message
    assert "missing tool get_entities" in message


@dataclass
class _Payload:
    count: int
    ratio: float


class _DumpBlock:
    def model_dump(self, *, mode: str, by_alias: bool) -> dict[str, object]:
        assert mode == "json"
        assert by_alias is True
        return {"kind": "dumped"}


def test_mcp_normalization_covers_empty_multiple_and_non_json_payloads() -> None:
    empty = mcp_adapter.normalize_mcp_result("search", CallToolResult(content=[]))
    assert empty.data is None

    multiple = mcp_adapter.normalize_mcp_result(
        "search",
        CallToolResult(
            content=[
                TextContent(type="text", text='{"count": 2}'),
                TextContent(type="text", text="not-json"),
            ]
        ),
    )
    assert multiple.data == [{"count": 2}, "not-json"]
    assert multiple.text == ('{"count": 2}', "not-json")

    constructed = CallToolResult.model_construct(
        content=[_DumpBlock(), object()], structuredContent=None, isError=False
    )
    normalized = mcp_adapter.normalize_mcp_result("search", constructed)
    assert isinstance(normalized.data, list)
    assert normalized.data[0] == {"kind": "dumped"}
    assert isinstance(normalized.data[1], str)

    converted = mcp_adapter._to_json_value(
        {1: _Payload(count=3, ratio=math.inf), "items": (True, None)}
    )
    assert converted == {
        "1": {"count": 3, "ratio": "inf"},
        "items": [True, None],
    }


@pytest.mark.asyncio
async def test_provider_invoke_succeeds_and_times_out_without_leaking_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DataHubMCPProvider(DataHubMCPConfig(gms_url="http://localhost:8080"))
    monkeypatch.setattr(provider, "start", AsyncMock())

    class Session:
        async def call_tool(
            self, tool: str, *, arguments: dict[str, object]
        ) -> CallToolResult:
            assert tool == "search"
            assert arguments == {"query": "orders"}
            return CallToolResult(
                content=[TextContent(type="text", text='{"ok": true}')]
            )

    provider._session = cast(ClientSession, Session())
    result = await provider._invoke("search", {"query": "orders"})
    assert result.data == {"ok": True}

    class SlowSession:
        async def call_tool(self, *_: object, **__: object) -> CallToolResult:
            raise TimeoutError

    provider._session = cast(ClientSession, SlowSession())
    with pytest.raises(DataHubMCPError, match="exceeded the configured timeout"):
        await provider._invoke("search", {"query": "orders"})

    provider._session = None
    with pytest.raises(DataHubMCPError, match="session is closed"):
        await provider._invoke("search", {"query": "orders"})


@pytest.mark.asyncio
async def test_provider_start_wraps_transport_failure_and_close_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DataHubMCPProvider(DataHubMCPConfig(gms_url="http://localhost:8080"))

    def fail_stdio(*_: object, **__: object) -> object:
        raise RuntimeError("synthetic transport failure")

    monkeypatch.setattr(mcp_adapter, "stdio_client", fail_stdio)
    with pytest.raises(DataHubMCPError, match="failed to initialize") as captured:
        await provider.start()
    assert isinstance(captured.value.__cause__, RuntimeError)

    stack = SimpleNamespace(aclose=AsyncMock())
    provider._stack = cast(Any, stack)
    provider._session = cast(ClientSession, object())
    await provider.close()
    stack.aclose.assert_awaited_once()
    assert provider._stack is None
    assert provider._session is None
    await provider.close()


def test_cli_analyze_and_demo_preserve_dry_run_boundaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = SimpleNamespace(root=tmp_path / "run", ledger_json=tmp_path / "ledger.json")
    fake_agent = SimpleNamespace()
    fake_agent.run = lambda *args, **kwargs: ("ledger", paths)
    monkeypatch.setattr(cli, "EvidenceGraphAgent", lambda _: fake_agent)
    monkeypatch.setattr(cli, "load_change", lambda _: "change")
    monkeypatch.setattr(cli, "load_snapshot", lambda _: "snapshot")
    printed: list[tuple[object, Path, Path]] = []
    monkeypatch.setattr(cli, "_print_result", lambda *args: printed.append(args))

    cli.analyze(
        Path("change.json"),
        Path("snapshot.json"),
        tmp_path,
        Path("warehouse.sql"),
        apply=True,
    )
    assert printed == [("ledger", paths.root, paths.ledger_json)]

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "analyze", lambda **kwargs: calls.append(kwargs))
    cli.demo(tmp_path / "demo")
    assert calls[0]["apply"] is False
    assert calls[0]["output"] == tmp_path / "demo"


@pytest.mark.parametrize("apply", [False, True])
def test_cli_analyze_live_keeps_writeback_behind_all_gates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, apply: bool
) -> None:
    monkeypatch.setenv("EVIDENCEGRAPH_ENABLE_WRITES", "true")
    run_root = tmp_path / ("apply" if apply else "dry-run")
    run_root.mkdir()
    paths = SimpleNamespace(root=run_root, ledger_json=run_root / "evidence-ledger.json")
    calls: dict[str, object] = {"execute": 0, "persist": 0}

    class Snapshot:
        def model_dump_json(self, *, indent: int) -> str:
            assert indent == 2
            return '{"snapshot_id":"test"}'

    class Ledger:
        run_id = "EG-AAAAAAAAAAAA"
        writeback_proposals: tuple[object, ...] = ()

        def __init__(self) -> None:
            self.safety_decision = SimpleNamespace(may_execute_writeback=apply)

        def model_copy(self, *, update: dict[str, object]) -> Ledger:
            assert "mutation_receipts" in update
            return self

    ledger = Ledger()

    class Provider:
        def __init__(self, config: DataHubMCPConfig) -> None:
            calls["writes_enabled"] = config.writes_enabled
            self.writes_enabled = config.writes_enabled

        async def __aenter__(self) -> Provider:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    class Collector:
        def __init__(self, provider: Provider, sdk: object) -> None:
            assert provider.writes_enabled is apply
            assert sdk == "sdk"

        async def collect(self, change: object) -> Snapshot:
            assert change == "change"
            return Snapshot()

    class Agent:
        def __init__(self, warehouse_setup: Path) -> None:
            assert warehouse_setup == Path("warehouse.sql")

        def run(self, *_: object, **kwargs: object) -> tuple[Ledger, SimpleNamespace]:
            assert kwargs["apply_requested"] is apply
            assert kwargs["mutation_tools_available"] is apply
            return ledger, paths

        def persist(self, output: Path, updated: Ledger) -> SimpleNamespace:
            assert output == tmp_path
            assert updated is ledger
            calls["persist"] = int(calls["persist"]) + 1
            return paths

    async def execute(*_: object, **kwargs: object) -> tuple[MutationReceipt, ...]:
        assert kwargs["approval_granted"] is apply
        calls["execute"] = int(calls["execute"]) + 1
        return ()

    monkeypatch.setattr(cli, "load_change", lambda _: "change")
    monkeypatch.setattr(cli, "DataHubMCPProvider", Provider)
    monkeypatch.setattr(cli, "DataHubSDKReader", lambda *_: "sdk")
    monkeypatch.setattr(cli, "LiveContextCollector", Collector)
    monkeypatch.setattr(cli, "EvidenceGraphAgent", Agent)
    monkeypatch.setattr(cli, "execute_writeback_proposals", execute)
    monkeypatch.setattr(cli, "_print_result", lambda *_: None)

    cli.analyze_live(
        Path("change.json"),
        "http://localhost:8080",
        tmp_path,
        Path("warehouse.sql"),
        apply=apply,
    )

    assert calls["writes_enabled"] is apply
    assert calls["execute"] == int(apply)
    assert calls["persist"] == int(apply)
    assert (run_root / "context-snapshot.json").read_text(encoding="utf-8") == (
        '{"snapshot_id":"test"}\n'
    )


def test_cli_print_and_ablation_render_measured_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output: list[object] = []
    monkeypatch.setattr(cli.console, "print", lambda value: output.append(value))
    impact = SimpleNamespace(
        risk_level=SimpleNamespace(value="critical"),
        risk_score=91,
        asset_name="Executive Revenue Watch",
        paths=("path",),
    )
    ledger = SimpleNamespace(
        run_id="EG-AAAAAAAAAAAA",
        impacts=(impact,),
        safety_decision=SimpleNamespace(may_execute_writeback=False),
    )
    cli._print_result(ledger, tmp_path, tmp_path / "ledger.json")
    assert len(output) == 2

    monkeypatch.setattr(cli, "load_change", lambda _: "change")
    monkeypatch.setattr(cli, "load_snapshot", lambda _: "snapshot")
    monkeypatch.setattr(cli, "load_truth_manifest", lambda _: "truth")
    result = SimpleNamespace(to_dict=lambda: {"recall": 100.0})
    monkeypatch.setattr(cli, "run_ablation", lambda *args: result)
    cli.ablation(Path("change"), Path("context"), Path("truth"))
    assert len(output) == 3


def test_cli_verify_closure_writes_a_hash_bound_receipt(tmp_path: Path) -> None:
    output = tmp_path / "closure" / "receipt.json"
    patch = ROOT / "examples/flagship/migration/patches/demo-platform.patch"
    cli.verify_closure(
        ROOT / "examples/closure/before-graph.json",
        ROOT / "examples/closure/after-graph.json",
        FLAGSHIP_LEDGER,
        patch,
        output,
        applied_at="2026-08-03T12:30:00",
    )

    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["patch_sha256"] == hashlib.sha256(patch.read_bytes()).hexdigest()
    assert receipt["status"] == "closed"


def test_cli_writeback_retry_rejects_missing_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("EVIDENCEGRAPH_ENABLE_WRITES", raising=False)
    with pytest.raises(typer.BadParameter, match="requires --apply"):
        cli.verify_writeback_retry(
            FLAGSHIP_LEDGER,
            "http://localhost:8080",
            tmp_path / "receipts.json",
            apply=True,
        )


@pytest.mark.parametrize(
    ("status", "raises"),
    (("skipped_idempotent_verified", False), ("applied_verified", True)),
)
def test_cli_writeback_retry_accepts_only_verified_noops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    raises: bool,
) -> None:
    monkeypatch.setenv("EVIDENCEGRAPH_ENABLE_WRITES", "true")
    output = tmp_path / f"{status}.json"

    class Provider:
        def __init__(self, config: DataHubMCPConfig) -> None:
            assert config.writes_enabled is True

        async def __aenter__(self) -> Provider:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    receipt = MutationReceipt(
        proposal_id="WB-TAG",
        tool="add_tags",
        status=status,
        response_sha256="a" * 64,
    )

    async def execute(*_: object, **__: object) -> tuple[MutationReceipt, ...]:
        return (receipt,)

    monkeypatch.setattr(cli, "DataHubMCPProvider", Provider)
    monkeypatch.setattr(cli, "execute_writeback_proposals", execute)
    monkeypatch.setattr(cli.console, "print", lambda *_: None)

    if raises:
        with pytest.raises(RuntimeError, match="non-idempotent mutation"):
            cli.verify_writeback_retry(
                FLAGSHIP_LEDGER,
                "http://localhost:8080",
                output,
                apply=True,
            )
        assert not output.exists()
    else:
        cli.verify_writeback_retry(
            FLAGSHIP_LEDGER,
            "http://localhost:8080",
            output,
            apply=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload[0]["status"] == "skipped_idempotent_verified"
