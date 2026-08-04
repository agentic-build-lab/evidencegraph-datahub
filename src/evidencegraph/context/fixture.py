"""Deterministic in-memory context provider for tests and offline demos."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from evidencegraph.context.provider import (
    BaseContextProvider,
    ContextProviderError,
    ContextResult,
    JSONValue,
)


class FixtureExhaustedError(ContextProviderError):
    """Raised when an operation has no remaining scripted fixture response."""


@dataclass(frozen=True, slots=True)
class FixtureCall:
    """One call recorded by the fixture provider."""

    tool: str
    arguments: Mapping[str, JSONValue]


FixtureResponse = ContextResult | JSONValue


class FixtureContextProvider(BaseContextProvider):
    """Serve the same typed interface as MCP from ordered fixture responses."""

    def __init__(
        self,
        responses: Mapping[str, Sequence[FixtureResponse]],
        *,
        writes_enabled: bool = False,
    ) -> None:
        super().__init__(writes_enabled=writes_enabled)
        self._responses = {name: tuple(values) for name, values in responses.items()}
        self._positions: dict[str, int] = defaultdict(int)
        self.calls: list[FixtureCall] = []

    async def __aenter__(self) -> FixtureContextProvider:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def _invoke(self, tool: str, arguments: Mapping[str, JSONValue]) -> ContextResult:
        self.calls.append(FixtureCall(tool=tool, arguments=dict(arguments)))
        position = self._positions[tool]
        responses = self._responses.get(tool, ())
        if position >= len(responses):
            raise FixtureExhaustedError(f"no fixture response remains for {tool}")
        self._positions[tool] += 1
        response = responses[position]
        if isinstance(response, ContextResult):
            if response.tool != tool:
                raise FixtureExhaustedError(
                    f"fixture response for {tool} is labeled as {response.tool}"
                )
            return response
        return ContextResult(tool=tool, data=response)
