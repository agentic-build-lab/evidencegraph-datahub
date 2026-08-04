"""Typed, safety-oriented context provider contracts for EvidenceGraph."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias, runtime_checkable

JSONScalar: TypeAlias = bool | int | float | str | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
SortOrder: TypeAlias = Literal["asc", "desc"]
LineageDirection: TypeAlias = Literal["upstream", "downstream"]
DescriptionOperation: TypeAlias = Literal["replace", "append"]
DocumentType: TypeAlias = Literal[
    "Insight",
    "Decision",
    "FAQ",
    "Analysis",
    "Summary",
    "Recommendation",
    "Note",
    "Context",
]


class ContextProviderError(RuntimeError):
    """Base error raised by context providers."""


class WriteDisabledError(ContextProviderError):
    """Raised when a caller attempts a live mutation through a read-only provider."""


class InvalidContextRequest(ContextProviderError, ValueError):
    """Raised when a request cannot be sent safely to the backing provider."""


@dataclass(frozen=True, slots=True)
class ContextResult:
    """Provider-neutral representation of a tool result."""

    tool: str
    data: JSONValue
    text: tuple[str, ...] = ()
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class LineageResult:
    """All lineage pages collected for one bounded traversal request."""

    direction: LineageDirection
    pages: tuple[ContextResult, ...]
    complete: bool
    stop_reason: str
    next_offset: int
    token_budgeted: bool = False


@dataclass(frozen=True, slots=True)
class MutationResult:
    """A dry-run proposal or the normalized receipt from an allowlisted mutation."""

    tool: str
    arguments: Mapping[str, JSONValue]
    dry_run: bool
    applied: bool
    result: ContextResult | None = None


@runtime_checkable
class ContextProvider(Protocol):
    """The context operations used by the EvidenceGraph orchestration layer."""

    writes_enabled: bool

    async def search(
        self,
        query: str = "*",
        *,
        filter: str | None = None,
        num_results: int = 10,
        sort_by: str | None = None,
        sort_order: SortOrder = "desc",
        offset: int = 0,
    ) -> ContextResult: ...

    async def get_entities(self, urns: Sequence[str]) -> ContextResult: ...

    async def search_documents(
        self,
        query: str = "*",
        *,
        filter: str | None = None,
        num_results: int = 10,
        offset: int = 0,
    ) -> ContextResult: ...

    async def list_schema_fields(
        self,
        urn: str,
        *,
        keywords: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ContextResult: ...

    async def get_lineage(
        self,
        urn: str,
        *,
        column: str | None = None,
        query: str | None = None,
        filter: str | None = None,
        direction: LineageDirection = "downstream",
        max_hops: int = 3,
        page_size: int = 30,
        offset: int = 0,
        max_pages: int = 100,
    ) -> LineageResult: ...

    async def add_tags(
        self,
        tag_urns: Sequence[str],
        entity_urns: Sequence[str],
        *,
        column_paths: Sequence[str | None] | None = None,
        dry_run: bool = True,
    ) -> MutationResult: ...

    async def update_description(
        self,
        entity_urn: str,
        description: str,
        *,
        operation: DescriptionOperation = "replace",
        column_path: str | None = None,
        dry_run: bool = True,
    ) -> MutationResult: ...

    async def save_document(
        self,
        document_type: DocumentType,
        title: str,
        content: str,
        *,
        urn: str | None = None,
        topics: Sequence[str] | None = None,
        related_documents: Sequence[str] | None = None,
        related_assets: Sequence[str] | None = None,
        dry_run: bool = True,
    ) -> MutationResult: ...


class BaseContextProvider(ABC):
    """Shared request validation, pagination, and mutation safety behavior."""

    def __init__(self, *, writes_enabled: bool = False) -> None:
        self.writes_enabled = writes_enabled

    @abstractmethod
    async def _invoke(self, tool: str, arguments: Mapping[str, JSONValue]) -> ContextResult:
        """Invoke one pre-allowlisted operation in a concrete provider."""

    async def search(
        self,
        query: str = "*",
        *,
        filter: str | None = None,
        num_results: int = 10,
        sort_by: str | None = None,
        sort_order: SortOrder = "desc",
        offset: int = 0,
    ) -> ContextResult:
        _require_non_empty(query, "query")
        _require_positive(num_results, "num_results")
        _require_non_negative(offset, "offset")
        arguments: dict[str, JSONValue] = {
            "query": query,
            "num_results": num_results,
            "sort_order": sort_order,
            "offset": offset,
        }
        _add_optional(arguments, "filter", filter)
        _add_optional(arguments, "sort_by", sort_by)
        return await self._invoke("search", arguments)

    async def get_entities(self, urns: Sequence[str]) -> ContextResult:
        normalized = _require_strings(urns, "urns")
        return await self._invoke("get_entities", {"urns": _json_strings(normalized)})

    async def search_documents(
        self,
        query: str = "*",
        *,
        filter: str | None = None,
        num_results: int = 10,
        offset: int = 0,
    ) -> ContextResult:
        _require_non_empty(query, "query")
        _require_positive(num_results, "num_results")
        _require_non_negative(offset, "offset")
        arguments: dict[str, JSONValue] = {
            "query": query,
            "num_results": num_results,
            "offset": offset,
        }
        _add_optional(arguments, "filter", filter)
        return await self._invoke("search_documents", arguments)

    async def list_schema_fields(
        self,
        urn: str,
        *,
        keywords: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ContextResult:
        _require_non_empty(urn, "urn")
        _require_positive(limit, "limit")
        _require_non_negative(offset, "offset")
        arguments: dict[str, JSONValue] = {"urn": urn, "limit": limit, "offset": offset}
        _add_optional(arguments, "keywords", keywords)
        return await self._invoke("list_schema_fields", arguments)

    async def get_lineage(
        self,
        urn: str,
        *,
        column: str | None = None,
        query: str | None = None,
        filter: str | None = None,
        direction: LineageDirection = "downstream",
        max_hops: int = 3,
        page_size: int = 30,
        offset: int = 0,
        max_pages: int = 100,
    ) -> LineageResult:
        _require_non_empty(urn, "urn")
        if direction not in ("upstream", "downstream"):
            raise InvalidContextRequest("direction must be 'upstream' or 'downstream'")
        if max_hops not in (1, 2, 3):
            raise InvalidContextRequest("max_hops must be 1, 2, or 3 (3 means unlimited)")
        _require_positive(page_size, "page_size")
        _require_non_negative(offset, "offset")
        _require_positive(max_pages, "max_pages")

        pages: list[ContextResult] = []
        current_offset = offset
        token_budgeted = False
        direction_key = f"{direction}s"

        for _ in range(max_pages):
            arguments: dict[str, JSONValue] = {
                "urn": urn,
                "upstream": direction == "upstream",
                "max_hops": max_hops,
                "max_results": page_size,
                "offset": current_offset,
            }
            _add_optional(arguments, "column", column)
            _add_optional(arguments, "query", query)
            _add_optional(arguments, "filter", filter)
            page = await self._invoke("get_lineage", arguments)
            pages.append(page)

            if page.is_error:
                return LineageResult(
                    direction, tuple(pages), False, "tool_error", current_offset, token_budgeted
                )
            envelope = _mapping_at(page.data, direction_key)
            if envelope is None:
                return LineageResult(
                    direction,
                    tuple(pages),
                    False,
                    "unverifiable_pagination",
                    current_offset,
                    token_budgeted,
                )

            token_budgeted = token_budgeted or envelope.get("truncatedDueToTokenBudget") is True
            has_more = envelope.get("hasMore")
            if has_more is False:
                returned = envelope.get("returned", 0)
                if isinstance(returned, int) and not isinstance(returned, bool) and returned >= 0:
                    current_offset += returned
                return LineageResult(
                    direction, tuple(pages), True, "exhausted", current_offset, token_budgeted
                )
            if has_more is not True:
                return LineageResult(
                    direction,
                    tuple(pages),
                    False,
                    "unverifiable_pagination",
                    current_offset,
                    token_budgeted,
                )

            returned = envelope.get("returned")
            if not isinstance(returned, int) or isinstance(returned, bool) or returned <= 0:
                return LineageResult(
                    direction,
                    tuple(pages),
                    False,
                    "no_pagination_progress",
                    current_offset,
                    token_budgeted,
                )
            current_offset += returned

        return LineageResult(
            direction, tuple(pages), False, "page_limit", current_offset, token_budgeted
        )

    async def add_tags(
        self,
        tag_urns: Sequence[str],
        entity_urns: Sequence[str],
        *,
        column_paths: Sequence[str | None] | None = None,
        dry_run: bool = True,
    ) -> MutationResult:
        tags = _require_strings(tag_urns, "tag_urns")
        entities = _require_strings(entity_urns, "entity_urns")
        arguments: dict[str, JSONValue] = {
            "tag_urns": _json_strings(tags),
            "entity_urns": _json_strings(entities),
        }
        if column_paths is not None:
            paths = list(column_paths)
            if len(paths) != len(entities):
                raise InvalidContextRequest("column_paths must have one entry for each entity_urn")
            for path in paths:
                if path is not None:
                    _require_non_empty(path, "column_paths entry")
            arguments["column_paths"] = _json_nullable_strings(paths)
        return await self._mutate("add_tags", arguments, dry_run=dry_run)

    async def update_description(
        self,
        entity_urn: str,
        description: str,
        *,
        operation: DescriptionOperation = "replace",
        column_path: str | None = None,
        dry_run: bool = True,
    ) -> MutationResult:
        _require_non_empty(entity_urn, "entity_urn")
        _require_non_empty(description, "description")
        if operation not in ("replace", "append"):
            raise InvalidContextRequest("operation must be 'replace' or 'append'")
        arguments: dict[str, JSONValue] = {
            "entity_urn": entity_urn,
            "operation": operation,
            "description": description,
        }
        _add_optional(arguments, "column_path", column_path)
        return await self._mutate("update_description", arguments, dry_run=dry_run)

    async def save_document(
        self,
        document_type: DocumentType,
        title: str,
        content: str,
        *,
        urn: str | None = None,
        topics: Sequence[str] | None = None,
        related_documents: Sequence[str] | None = None,
        related_assets: Sequence[str] | None = None,
        dry_run: bool = True,
    ) -> MutationResult:
        valid_types = {
            "Insight",
            "Decision",
            "FAQ",
            "Analysis",
            "Summary",
            "Recommendation",
            "Note",
            "Context",
        }
        if document_type not in valid_types:
            raise InvalidContextRequest(f"unsupported document_type: {document_type}")
        _require_non_empty(title, "title")
        _require_non_empty(content, "content")
        arguments: dict[str, JSONValue] = {
            "document_type": document_type,
            "title": title,
            "content": content,
        }
        _add_optional(arguments, "urn", urn)
        if topics is not None:
            arguments["topics"] = _json_strings(_require_strings(topics, "topics"))
        if related_documents is not None:
            arguments["related_documents"] = _json_strings(
                _require_strings(related_documents, "related_documents")
            )
        if related_assets is not None:
            arguments["related_assets"] = _json_strings(
                _require_strings(related_assets, "related_assets")
            )
        return await self._mutate("save_document", arguments, dry_run=dry_run)

    async def _mutate(
        self, tool: str, arguments: Mapping[str, JSONValue], *, dry_run: bool
    ) -> MutationResult:
        copied_arguments = dict(arguments)
        if dry_run:
            return MutationResult(tool, copied_arguments, True, False)
        if not self.writes_enabled:
            raise WriteDisabledError(
                f"live {tool} is disabled; enable writes and explicitly set dry_run=False"
            )
        result = await self._invoke(tool, copied_arguments)
        applied = not result.is_error and _application_success(result.data)
        return MutationResult(tool, copied_arguments, False, applied, result)


def _require_non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidContextRequest(f"{name} must be a non-empty string")


def _require_strings(values: Sequence[str], name: str) -> list[str]:
    normalized = list(values)
    if not normalized:
        raise InvalidContextRequest(f"{name} must not be empty")
    for value in normalized:
        _require_non_empty(value, f"{name} entry")
    return normalized


def _json_strings(values: Sequence[str]) -> list[JSONValue]:
    result: list[JSONValue] = []
    result.extend(values)
    return result


def _json_nullable_strings(values: Sequence[str | None]) -> list[JSONValue]:
    result: list[JSONValue] = []
    result.extend(values)
    return result


def _require_positive(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidContextRequest(f"{name} must be a positive integer")


def _require_non_negative(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidContextRequest(f"{name} must be a non-negative integer")


def _add_optional(arguments: dict[str, JSONValue], key: str, value: str | None) -> None:
    if value is not None:
        _require_non_empty(value, key)
        arguments[key] = value


def _mapping_at(data: JSONValue, key: str) -> dict[str, JSONValue] | None:
    if not isinstance(data, dict):
        return None
    value = data.get(key)
    if not isinstance(value, dict):
        return None
    return value


def _application_success(data: JSONValue) -> bool:
    """Treat explicit application-level failure envelopes as failed mutations."""

    if not isinstance(data, dict):
        return True
    success = data.get("success")
    if success is False:
        return False
    nested = data.get("result")
    return not (isinstance(nested, dict) and nested.get("success") is False)
