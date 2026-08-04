"""Official DataHub MCP stdio adapter with startup contract verification."""

from __future__ import annotations

import asyncio
import json
import math
import os
from collections.abc import Mapping, Sequence
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlsplit

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent, Tool

from evidencegraph.context.provider import (
    BaseContextProvider,
    ContextProviderError,
    ContextResult,
    JSONValue,
)

DATAHUB_MCP_PACKAGE = "mcp-server-datahub@0.6.0"

READ_TOOL_CONTRACTS: dict[str, frozenset[str]] = {
    "search": frozenset({"query", "num_results", "offset"}),
    "get_entities": frozenset({"urns"}),
    "search_documents": frozenset({"query", "num_results", "offset"}),
    "list_schema_fields": frozenset({"urn", "limit", "offset"}),
    "get_lineage": frozenset({"urn", "upstream", "max_results", "offset"}),
}
WRITE_TOOL_CONTRACTS: dict[str, frozenset[str]] = {
    "add_tags": frozenset({"tag_urns", "entity_urns"}),
    "update_description": frozenset({"entity_urn", "operation", "description"}),
    "save_document": frozenset({"document_type", "title", "content"}),
}


class DataHubMCPError(ContextProviderError):
    """Base error for DataHub MCP transport and discovery failures."""


class DataHubMCPContractError(DataHubMCPError):
    """Raised when the server does not expose the expected pinned tool contract."""


@dataclass(frozen=True, slots=True)
class DataHubMCPConfig:
    """Connection configuration; credentials are never passed on the command line."""

    gms_url: str
    token: str | None = field(repr=False, default=None)
    writes_enabled: bool = False
    uvx_command: str = "uvx"
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.gms_url.strip():
            raise ValueError("gms_url must be a non-empty URL")
        if not self.uvx_command.strip():
            raise ValueError("uvx_command must be non-empty")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        parsed = urlsplit(self.gms_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("gms_url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("gms_url must not contain embedded credentials")
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme == "http" and parsed.hostname.lower() not in local_hosts:
            raise ValueError("remote DataHub connections must use HTTPS")

    @classmethod
    def from_env(cls, *, writes_enabled: bool = False) -> DataHubMCPConfig:
        """Build a configuration from DataHub's standard environment variables."""

        gms_url = os.environ.get("DATAHUB_GMS_URL", "").strip()
        if not gms_url:
            raise ValueError("DATAHUB_GMS_URL is required")
        return cls(
            gms_url=gms_url,
            token=os.environ.get("DATAHUB_GMS_TOKEN"),
            writes_enabled=writes_enabled,
        )

    def server_parameters(self) -> StdioServerParameters:
        """Return the pinned command and a child environment without printing secrets."""

        child_env = _minimal_subprocess_environment()
        child_env["DATAHUB_GMS_URL"] = self.gms_url
        child_env["TOOLS_IS_MUTATION_ENABLED"] = str(self.writes_enabled).lower()
        child_env["SAVE_DOCUMENT_TOOL_ENABLED"] = str(self.writes_enabled).lower()
        if self.token is None:
            child_env.pop("DATAHUB_GMS_TOKEN", None)
        else:
            child_env["DATAHUB_GMS_TOKEN"] = self.token
        return StdioServerParameters(
            command=self.uvx_command,
            args=[DATAHUB_MCP_PACKAGE],
            env=child_env,
        )


def _minimal_subprocess_environment() -> dict[str, str]:
    allowed = {
        "APPDATA",
        "COMSPEC",
        "HOME",
        "LANG",
        "LC_ALL",
        "LOCALAPPDATA",
        "NO_COLOR",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "UV_CACHE_DIR",
        "WINDIR",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


class DataHubMCPProvider(BaseContextProvider):
    """Lazy, reusable client for the official DataHub MCP server."""

    def __init__(self, config: DataHubMCPConfig, *, errlog: TextIO | None = None) -> None:
        super().__init__(writes_enabled=config.writes_enabled)
        self._config = config
        self._errlog = errlog
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._start_lock = asyncio.Lock()
        self._call_lock = asyncio.Lock()

    async def __aenter__(self) -> DataHubMCPProvider:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def start(self) -> None:
        """Start the subprocess and reject incompatible tool surfaces."""

        async with self._start_lock:
            if self._session is not None:
                return
            stack = AsyncExitStack()
            try:
                parameters = self._config.server_parameters()
                errlog = self._errlog
                if errlog is None:
                    errlog = stack.enter_context(
                        Path(os.devnull).open("w", encoding="utf-8")  # noqa: SIM115
                    )
                read_stream, write_stream = await stack.enter_async_context(
                    stdio_client(parameters, errlog=errlog)
                )
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await asyncio.wait_for(session.initialize(), timeout=self._config.timeout_seconds)
                tools = await asyncio.wait_for(
                    _list_all_tools(session), timeout=self._config.timeout_seconds
                )
                validate_tool_contracts(tools, writes_enabled=self.writes_enabled)
            except asyncio.CancelledError:
                await stack.aclose()
                raise
            except DataHubMCPError:
                await stack.aclose()
                raise
            except Exception as error:
                await stack.aclose()
                raise DataHubMCPError(
                    "the official DataHub MCP server failed to initialize"
                ) from error
            except BaseException:
                await stack.aclose()
                raise
            self._stack = stack
            self._session = session

    async def close(self) -> None:
        """Close the MCP session and its stdio subprocess."""

        async with self._start_lock, self._call_lock:
            stack = self._stack
            self._stack = None
            self._session = None
            if stack is not None:
                await stack.aclose()

    async def _invoke(self, tool: str, arguments: Mapping[str, JSONValue]) -> ContextResult:
        await self.start()
        async with self._call_lock:
            session = self._session
            if session is None:  # A concurrent close won the lifecycle race.
                raise DataHubMCPError("MCP session is closed")
            try:
                response = await asyncio.wait_for(
                    session.call_tool(tool, arguments=dict(arguments)),
                    timeout=self._config.timeout_seconds,
                )
            except TimeoutError as error:
                raise DataHubMCPError(
                    f"DataHub MCP operation {tool} exceeded the configured timeout"
                ) from error
        return normalize_mcp_result(tool, response)


async def _list_all_tools(session: ClientSession) -> list[Tool]:
    tools: list[Tool] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        result = await session.list_tools(cursor=cursor)
        tools.extend(result.tools)
        next_cursor = result.nextCursor
        if next_cursor is None:
            return tools
        if next_cursor in seen_cursors:
            raise DataHubMCPContractError("tool discovery returned a repeated cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


def validate_tool_contracts(tools: Sequence[Tool], *, writes_enabled: bool) -> None:
    """Verify expected names and minimum argument properties before serving requests."""

    discovered = {tool.name: tool for tool in tools}
    expected = dict(READ_TOOL_CONTRACTS)
    if writes_enabled:
        expected.update(WRITE_TOOL_CONTRACTS)

    defects: list[str] = []
    for name, expected_properties in expected.items():
        tool = discovered.get(name)
        if tool is None:
            defects.append(f"missing tool {name}")
            continue
        properties = tool.inputSchema.get("properties")
        if not isinstance(properties, dict):
            defects.append(f"tool {name} has no object properties")
            continue
        missing = expected_properties.difference(properties)
        if missing:
            defects.append(f"tool {name} missing properties: {', '.join(sorted(missing))}")
    if defects:
        raise DataHubMCPContractError("; ".join(defects))


def normalize_mcp_result(tool: str, result: CallToolResult) -> ContextResult:
    """Normalize structured or text MCP content into JSON-safe provider data."""

    texts = tuple(block.text for block in result.content if isinstance(block, TextContent))
    if result.structuredContent is not None:
        data = _to_json_value(result.structuredContent)
    else:
        content_values: list[JSONValue] = []
        for block in result.content:
            if isinstance(block, TextContent):
                text = block.text
                try:
                    content_values.append(_to_json_value(json.loads(text)))
                except (json.JSONDecodeError, TypeError):
                    content_values.append(text)
            elif hasattr(block, "model_dump"):
                content_values.append(_to_json_value(block.model_dump(mode="json", by_alias=True)))
            else:
                content_values.append(_to_json_value(block))
        if not content_values:
            data = None
        elif len(content_values) == 1:
            data = content_values[0]
        else:
            data = content_values
    return ContextResult(tool=tool, data=data, text=texts, is_error=result.isError)


def _to_json_value(value: Any) -> JSONValue:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_json_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_json_value(value.model_dump(mode="json", by_alias=True))
    if is_dataclass(value) and not isinstance(value, type):
        return _to_json_value(asdict(value))
    return str(value)
